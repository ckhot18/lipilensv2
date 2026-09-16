from fastapi import APIRouter

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
    """Health check endpoint returning server status and model loading state."""
    return {
        "status": "ok",
        "model_loaded": _model_loaded,
    }
