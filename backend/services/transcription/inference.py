import abc
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranscriptionResult:
    """Result of a transcription inference call."""
    text: str
    model_name: str
    inference_mode: str
    raw_output: str = ""


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
        return LocalQwenTranscriptionService()
    if mode == "colab":
        from backend.services.transcription.colab_client import (
            ColabTranscriptionService,
        )
        return ColabTranscriptionService()
    raise ValueError(
        f"Unknown INFERENCE_MODE={app_config.INFERENCE_MODE!r} "
        "(expected 'local' or 'colab')"
    )
