import abc
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# A progress callback receives plain dicts so the service layer never imports
# anything job- or HTTP-shaped: {"stage": str, ...stage-specific fields}.
ProgressCallback = Callable[[dict[str, Any]], None]


def _emit(on_progress: ProgressCallback | None, **event: Any) -> None:
    if on_progress is not None:
        on_progress(event)


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
    def transcribe(self, image_path: str | Path, prompt: str,
                   on_progress: ProgressCallback | None = None,
                   ) -> TranscriptionResult:
        """
        Transcribe the text in the given image.
        
        Args:
            image_path: Path to the image file.
            prompt: Text prompt guiding the transcription.
            on_progress: Optional callback receiving progress events as this
                call advances. Callers that do not care may omit it.
            
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

    def transcribe(self, image_path: str | Path, prompt: str,
                   on_progress: ProgressCallback | None = None
                   ) -> TranscriptionResult:
        from backend.services.transcription.segment import segment_lines, write_lines

        lines = segment_lines(image_path)
        total = max(1, len(lines))

        if len(lines) <= 1:
            # Nothing to gain from segmentation (blank page, or one band):
            # report it as a single line so the UI still has a denominator.
            _emit(on_progress, stage="segmenting", lines_total=1,
                 message="Reading the page as a single line")
            _emit(on_progress, stage="line_start", index=0, lines_total=1)
            result = self.inner.transcribe(image_path, prompt, on_progress)
            result.line_count = len(lines)
            _emit(on_progress, stage="line_done", index=1, lines_total=1,
                 text=(result.text or "").strip(),
                 partial=(result.text or "").strip())
            return result

        logger.info("Line-segmented transcription: %d lines", len(lines))
        _emit(on_progress, stage="segmenting", lines_total=total,
             message=f"Found {len(lines)} text lines")
        pieces: list[str] = []
        model_name = ""
        inference_mode = ""
        raw: list[str] = []

        with tempfile.TemporaryDirectory(prefix="lipilens_lines_") as tmp:
            paths = write_lines(lines, Path(tmp))
            for i, path in enumerate(paths, start=1):
                _emit(on_progress, stage="line_start", index=i - 1,
                     lines_total=len(paths))
                try:
                    part = self.inner.transcribe(path, prompt, on_progress)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Line %d/%d failed (%s); skipping",
                                   i, len(paths), type(exc).__name__)
                    _emit(on_progress, stage="line_failed", index=i,
                         lines_total=len(paths))
                    continue
                text = (part.text or "").strip()
                if text:
                    pieces.append(text)
                    raw.append(text)
                model_name = model_name or part.model_name
                inference_mode = inference_mode or part.inference_mode
                _emit(on_progress, stage="line_done", index=i,
                     lines_total=len(paths), text=text,
                     partial="\n".join(pieces))

        if not pieces:
            # Every line failed; fall back to one whole-page call rather than
            # reporting an empty transcription as success.
            logger.warning("All %d lines failed; retrying as a single page",
                           len(lines))
            _emit(on_progress, stage="line_start", index=0, lines_total=1)
            result = self.inner.transcribe(image_path, prompt, on_progress)
            result.line_count = 1
            _emit(on_progress, stage="line_done", index=1, lines_total=1,
                 text=(result.text or "").strip(),
                 partial=(result.text or "").strip())
            return result

        return TranscriptionResult(
            text="\n".join(pieces),
            model_name=f"{model_name} + line segmentation",
            inference_mode=inference_mode,
            raw_output="\n".join(raw),
            line_count=len(paths),
        )
