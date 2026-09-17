#!/usr/bin/env python
"""
Smoke test for the Transcription service (Qwen2.5-VL-3B + Modi LoRA).

Runs local inference on a sample image.
"""

import logging
import sys
import time
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Service is selected via INFERENCE_MODE inside main() (local or Colab).

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_IMAGE = PROJECT_ROOT / "data" / "raw" / "sample_modi_page.png"
PROMPT = (
    "This image contains handwritten text in Modi script, a historical cursive "
    "script used to write the Marathi language. "
    "Transliterate the text in this image into Devanagari script. "
    "Output only the Devanagari text, with no explanation."
)

def main():
    image_path = DEFAULT_IMAGE
    
    if not image_path.exists():
        logger.error(f"Sample image not found: {image_path}")
        sys.exit(1)
        
    print("=" * 70)
    print("LipiLens — Model Smoke Test (Local Inference)")
    print("=" * 70)
    
    try:
        # Honor INFERENCE_MODE so this script works for both local and Colab.
        from backend.services.transcription.inference import get_transcription_service
        service = get_transcription_service()
        print(f"\nService: {type(service).__name__}")
        t0 = time.perf_counter()
        if hasattr(service, "_load_model"):
            service._load_model()
        t_load = time.perf_counter() - t0
        print(f"[OK] Model ready in {t_load:.2f}s (load time; ~0s for Colab lazy-load)")
        
        print(f"\nTranscribing: {image_path.name}")
        t1 = time.perf_counter()
        result = service.transcribe(image_path, PROMPT)
        t_infer = time.perf_counter() - t1
        
        print(f"\n[OK] Inference completed in {t_infer:.2f}s")
        print(f"Mode: {result.inference_mode} | Model: {result.model_name}")
        print("\n--- Output ---")
        # Windows consoles (cp1252) crash on Devanagari: use safe encoding.
        print(result.text.encode("ascii", "backslashreplace").decode("ascii"))
        print("--------------")
        
    except Exception as e:
        logger.exception("Inference failed")
        print(f"\n[FAIL] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
