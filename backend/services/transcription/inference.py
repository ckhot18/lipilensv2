import abc
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of a transcription inference call."""
    text: str
    model_name: str
    inference_mode: str
    raw_output: str = ""
    line_count: int = 0


class TranscriptionService(abc.ABC):
    """Abstract interface for transcription services (local or Colab)."""

    @abc.abstractmethod
    def transcribe(self, image_path: str | Path, prompt: str) -> TranscriptionResult:
        """
        Transcribe the text in the given image.
        
        Args:
            image_path: Path to the image file.
            prompt: Text prompt guiding the transcription.
            
        Returns:
            TranscriptionResult containing the transcribed text.
        """
        pass


def get_transcription_service() -> TranscriptionService:
    """Return the transcription service selected by config.INFERENCE_MODE.

    The rest of the system must only use this factory (never instantiate
    Local/Colab services directly in routes), so switching inference paths
    changes nothing outside services/transcription/.
    """
    from backend import config as app_config

    mode = app_config.INFERENCE_MODE.lower().strip()
    if mode == "local":
        from backend.services.transcription.local_qwen import (
            LocalQwenTranscriptionService,
        )
        service: TranscriptionService = LocalQwenTranscriptionService()
    elif mode == "colab":
        from backend.services.transcription.colab_client import (
            ColabTranscriptionService,
        )
        service = ColabTranscriptionService()
    else:
        raise ValueError(
            f"Unknown INFERENCE_MODE={app_config.INFERENCE_MODE!r} "
            "(expected 'local' or 'colab')"
        )
    if app_config.SEGMENT_LINES:
        return LineSegmentedTranscriptionService(service)
    return service


class LineSegmentedTranscriptionService(TranscriptionService):
    """Split a page into text lines and transcribe each one separately.

    A whole page reaches the model as ~128 merged visual tokens for a few
    hundred characters — under one token per character. Transcribing a single
    upscaled line instead spends the whole pixel budget on ~40 characters,
    multiplying the tokens available per character several-fold. Segmentation
    is pure OpenCV, so this costs no GPU.
    """

    def __init__(self, inner: TranscriptionService):
        self.inner = inner

    def transcribe(self, image_path: str | Path, prompt: str) -> TranscriptionResult:
        from backend.services.transcription.segment import segment_lines, write_lines

        lines = segment_lines(image_path)
        if len(lines) <= 1:
            result = self.inner.transcribe(image_path, prompt)
            result.line_count = len(lines)
            return result

        logger.info("Line-segmented transcription: %d lines", len(lines))
        pieces: list[str] = []
        model_name = ""
        inference_mode = ""
        raw: list[str] = []

        with tempfile.TemporaryDirectory(prefix="lipilens_lines_") as tmp:
            paths = write_lines(lines, Path(tmp))
            for i, path in enumerate(paths, start=1):
                try:
                    part = self.inner.transcribe(path, prompt)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Line %d/%d failed (%s); skipping",
                                   i, len(paths), type(exc).__name__)
                    continue
                text = (part.text or "").strip()
                if text:
                    pieces.append(text)
                    raw.append(text)
                model_name = model_name or part.model_name
                inference_mode = inference_mode or part.inference_mode

        if not pieces:
            # Every line failed; fall back to one whole-page call rather than
            # reporting an empty transcription as success.
            logger.warning("All %d lines failed; retrying as a single page",
                           len(lines))
            result = self.inner.transcribe(image_path, prompt)
            result.line_count = 1
            return result

        return TranscriptionResult(
            text="\n".join(pieces),
            model_name=f"{model_name} + line segmentation",
            inference_mode=inference_mode,
            raw_output="\n".join(raw),
            line_count=len(paths),
        )
