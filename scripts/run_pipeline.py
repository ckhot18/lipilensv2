#!/usr/bin/env python
"""Run the full Phase-4 pipeline once: image -> restored -> transcription.

Usage:
    python scripts/run_pipeline.py --image data/raw/mode_trans/MT-002.png --config enhanced
"""

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.pipeline import run_full_pipeline
from backend.services.restoration.pipeline import PRESET_CONFIGS

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4: full pipeline run")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--config", type=str, default="full_restoration",
                        choices=list(PRESET_CONFIGS))
    parser.add_argument("--cache-dir", type=Path, default=None,
                        help="Enable transcription disk cache (skips repeat model calls)")
    args = parser.parse_args()

    out = run_full_pipeline(args.image, args.config, cache_dir=args.cache_dir)
    hyp_path = Path(out.restored_image_path).with_name(
        f"{Path(out.restored_image_path).stem}_hyp.txt")
    hyp_path.write_text(out.transcription, encoding="utf-8")
    print(f"\n[OK] config={out.config_name} mode={out.inference_mode}")
    print(f"  restored: {out.restored_image_path}")
    print(f"  hyp text: {hyp_path}")
    print(f"  restore={out.restore_seconds}s transcribe={out.transcribe_seconds}s"
          f" cache_hit={out.cache_hit} sha256={out.image_sha256[:12]}...")
    if out.restoration_warning:
        print(f"  WARNING: {out.restoration_warning}")
    print("--- transcription (ascii-escaped) ---")
    print(out.transcription.encode("ascii", "backslashreplace").decode("ascii"))
    print("-------------------------------------")


if __name__ == "__main__":
    main()
