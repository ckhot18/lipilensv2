import os
from pathlib import Path

from dotenv import load_dotenv

# Base directories
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Load project .env (COLAB_ENDPOINT_URL, INFERENCE_MODE, ...) if present.
load_dotenv(PROJECT_ROOT / ".env")
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

# Pinned revisions (verified via HF API 2026-09-17). Part of the transcription
# cache key: a server-side model update must never serve stale cached text.
BASE_MODEL_REVISION = os.getenv(
    "BASE_MODEL_REVISION", "66285546d2b821cf421d4f5eb2576359d3770cd3")
LORA_REVISION = os.getenv(
    "LORA_REVISION", "5b9957d4755070ad25752517002c8773f2753e76")
