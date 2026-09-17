import logging
import requests
import base64
from pathlib import Path

from backend.config import COLAB_ENDPOINT_URL
from backend.services.transcription.inference import TranscriptionResult, TranscriptionService

logger = logging.getLogger(__name__)

class ColabTranscriptionService(TranscriptionService):
    def transcribe(self, image_path: str | Path, prompt: str) -> TranscriptionResult:
        if not COLAB_ENDPOINT_URL:
            raise ValueError("COLAB_ENDPOINT_URL is not configured.")

        logger.info(f"Transcribing image via Colab: {image_path}")
        
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
            
        payload = {
            "image": image_b64,
            "prompt": prompt
        }
        
        # Retry transient network/tunnel failures (dropped ngrok connections,
        # cold-start hiccups) with backoff — but never retry HTTP 4xx: a
        # rejected request will fail identically every time.
        last_exc: Exception | None = None
        for attempt in range(1, 4):
            try:
                # Generous timeout: Colab cold-start (model load) alone can
                # take minutes (EXP-001: 73.6s). No timeout = hang forever
                # on a dead tunnel.
                response = requests.post(
                    f"{COLAB_ENDPOINT_URL}/transcribe", json=payload,
                    timeout=900)
                if 400 <= response.status_code < 500:
                    response.raise_for_status()  # permanent: no retry
                response.raise_for_status()
                break
            except requests.exceptions.HTTPError:
                logger.error("Colab rejected request (HTTP %s): no retry",
                             response.status_code)
                raise
            except requests.exceptions.RequestException as e:
                last_exc = e
                logger.warning("Colab attempt %d/3 failed (%s); backing off",
                               attempt, type(e).__name__)
                if attempt < 3:
                    import time as _time
                    _time.sleep(5 * attempt)
        else:
            logger.error(f"Colab transcription failed after 3 attempts: "
                         f"{last_exc}")
            raise last_exc  # type: ignore[misc]

        data = response.json()
        result_text = data.get("transcription", "")

        return TranscriptionResult(
            text=result_text,
            model_name="Remote Colab (Qwen2.5-VL-3B + LoRA)",
            inference_mode="colab",
            raw_output=result_text
        )
