"""LipiLens Transcription Service Package"""

from .inference import TranscriptionResult, TranscriptionService
from .local_qwen import LocalQwenTranscriptionService
from .colab_client import ColabTranscriptionService

def get_transcription_service(mode: str) -> TranscriptionService:
    if mode == "local":
        return LocalQwenTranscriptionService()
    elif mode == "colab":
        return ColabTranscriptionService()
    else:
        raise ValueError(f"Unknown inference mode: {mode}")
