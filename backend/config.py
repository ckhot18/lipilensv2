import os
from pathlib import Path

# Base directories
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = DATA_DIR / "outputs"
EVALUATION_DIR = DATA_DIR / "evaluation"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/lipilens.db")

# CORS Origins
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# File Upload Limits
MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

# Inference configuration
INFERENCE_MODE = os.getenv("INFERENCE_MODE", "local")  # "local" | "colab"
BASE_MODEL_NAME = os.getenv("BASE_MODEL_NAME", "Qwen/Qwen2.5-VL-3B-Instruct")
LORA_ADAPTER_NAME = os.getenv("LORA_ADAPTER_NAME", "lgtk/qwen25vl-3b-modi-synth-lora")
COLAB_ENDPOINT_URL = os.getenv("COLAB_ENDPOINT_URL", "")
