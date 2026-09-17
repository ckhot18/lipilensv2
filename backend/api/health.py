from fastapi import APIRouter

from backend import config as app_config

router = APIRouter(prefix="/health", tags=["Health"])

# Global or state-dependent flag for model status
_model_loaded: bool = False

def set_model_loaded(loaded: bool) -> None:
    global _model_loaded
    _model_loaded = loaded

def is_model_loaded() -> bool:
    return _model_loaded

@router.get("")
def check_health():
    """Health check: server status + inference-path reachability.

    In Colab mode the local flag is meaningless, so the endpoint probes the
    Colab server (short timeout — health must stay fast) and reports it
    explicitly instead of pretending local state applies.
    """
    body: dict = {"status": "ok", "model_loaded": _model_loaded,
                  "inference_mode": app_config.INFERENCE_MODE}
    if app_config.INFERENCE_MODE == "colab":
        body["colab_reachable"] = False
        body["colab_model_loaded"] = False
        if app_config.COLAB_ENDPOINT_URL:
            try:
                import requests
                r = requests.get(
                    app_config.COLAB_ENDPOINT_URL.rstrip("/") + "/health",
                    timeout=10)
                if r.status_code == 200:
                    body["colab_reachable"] = True
                    body["colab_model_loaded"] = bool(
                        r.json().get("model_loaded"))
            except Exception:  # noqa: BLE001
                pass  # unreachable is itself the signal; stay fast
    return body
