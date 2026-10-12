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

# Transcribe one text line at a time instead of a whole page. Costs no GPU
# (segmentation is OpenCV) and multiplies visual tokens per character.
#
# Default OFF, deliberately. Segmentation was introduced to raise the visual
# token budget, but measured against expert references it made accuracy far
# worse (mean CER 0.345 -> 0.794 on single-column pages) because the band
# detector cuts ascenders and matras off each line and then feeds the model
# anonymous slivers. Whole-page transcription is the configuration the accuracy
# numbers in the README were measured with. Set SEGMENT_LINES=1 to re-enable.
SEGMENT_LINES = os.getenv("SEGMENT_LINES", "0").strip().lower() not in (
    "0", "false", "no", "off"
)
# Pixel budget handed to the Qwen2.5-VL processor. 512*28*28 starves a full
# page (~0.5 visual tokens per character); 1280*28*28 is within the model's
# documented range for document OCR. Must match the value the Colab server
# uses, or it will silently re-downscale the upscaled line crops.
MAX_MODEL_PIXELS = int(os.getenv("MAX_MODEL_PIXELS", 1280 * 28 * 28))

# --- Inference decoding knobs (read at call time so the eval harness can vary
# --- them without reloading the model) -------------------------------
# Greedy decoding on a 3B model falls into loops ("X Y X Y") when a line is
# hard to read; 1.0 disables the guard. The published adapter lists
# hallucination loops as a known failure mode.
REPETITION_PENALTY = float(os.getenv("REPETITION_PENALTY", "1.05"))
# Devanagari runs ~1 token per character, and MoDeTrans lines reach 254 tokens,
# so the previous 256 cap had almost no headroom and would silently truncate.
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "512"))
# max_pixels is a ceiling, not a target: a page already under the budget is
# passed through untouched, so raising the budget alone buys nothing. Upscaling
# the image first is what actually adds visual tokens per character. 1.0 = off.
MODEL_UPSCALE = float(os.getenv("MODEL_UPSCALE", "1.0"))

# --- Inference levers, all read at call time (read before changing them) ---
# Greedy is one option; beam search costs wall-clock, not much VRAM.
NUM_BEAMS = int(os.getenv("NUM_BEAMS", "1"))
# bfloat16 is supported on sm_80+; fp16 is a cheap A/B on consumer cards.
COMPUTE_DTYPE = os.getenv("COMPUTE_DTYPE", "bfloat16").strip().lower()
# Merging the adapter into the base avoids a separate LoRA matmul per layer.
# DO NOT ENABLE THIS. Measured on 20 pages (LEVERS): CER 0.316 -> 1.064, worse
# than emitting nothing, and worse on 20/20 pages. PEFT's merge_adapter()
# dequantizes the base, adds the adapter and re-quantizes the sum, so a QLoRA
# adapter ends up merged into weights it was never fitted against. Kept as a
# knob only so the experiment is reproducible.
MERGE_LORA = os.getenv("MERGE_LORA", "0").strip().lower() in (
    "1", "true", "yes", "on")

# Pinned revisions (verified via HF API 2026-09-17). Part of the transcription
# cache key: a server-side model update must never serve stale cached text.
BASE_MODEL_REVISION = os.getenv(
    "BASE_MODEL_REVISION", "66285546d2b821cf421d4f5eb2576359d3770cd3")
LORA_REVISION = os.getenv(
    "LORA_REVISION", "5b9957d4755070ad25752517002c8773f2753e76")
