#!/usr/bin/env python
"""
Smoke test for the OpenCV restoration pipeline.

Runs every predefined preprocessing config on a sample image, saves
the final and intermediate outputs to data/outputs/ for visual inspection.

Zero dependency on FastAPI, the database, or the model.

Usage:
    python scripts/smoke_test_opencv.py [--image PATH]
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.restoration.pipeline import (
    PRESET_CONFIGS,
    run_pipeline_on_file,
    save_intermediates,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_IMAGE = PROJECT_ROOT / "data" / "raw" / "sample_modi_page.png"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test: OpenCV restoration pipeline")
    parser.add_argument(
        "--image", type=Path, default=DEFAULT_IMAGE,
        help="Path to sample image (default: data/raw/sample_modi_page.png)",
    )
    args = parser.parse_args()

    if not args.image.exists():
        logger.error("Sample image not found: %s", args.image)
        logger.error("Add a Modi manuscript image to data/raw/ and try again.")
        sys.exit(1)

    print("=" * 70)
    print("LipiLens — OpenCV Restoration Pipeline Smoke Test")
    print("=" * 70)
    print(f"  Input image : {args.image}")
    print(f"  Output dir  : {OUTPUT_DIR}")
    print(f"  Configs     : {list(PRESET_CONFIGS.keys())}")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_passed = True

    for config_name, config in PRESET_CONFIGS.items():
        print(f"\n--- Running config: '{config_name}' ---")
        t0 = time.perf_counter()

        try:
            result = run_pipeline_on_file(
                input_path=args.image,
                config=config,
                output_path=OUTPUT_DIR / f"{config_name}_final.png",
                save_intermediates=True,
            )

            # Save intermediates in a per-config subdirectory
            inter_dir = OUTPUT_DIR / config_name / "intermediates"
            saved = save_intermediates(result, inter_dir, prefix=f"{config_name}_")

            elapsed = time.perf_counter() - t0

            print(f"  [OK] Stages run   : {result.stage_names}")
            print(f"  [OK] Final shape  : {result.final_image.shape}")
            print(f"  [OK] Intermediates: {len(saved)} images saved")
            print(f"  [OK] Time         : {elapsed:.3f}s")

        except Exception as exc:
            elapsed = time.perf_counter() - t0
            print(f"  [FAIL] FAILED after {elapsed:.3f}s: {exc}")

            logger.exception("Config '%s' failed", config_name)
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL CONFIGS PASSED — inspect outputs in data/outputs/")
    else:
        print("SOME CONFIGS FAILED — see errors above")
    print("=" * 70)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
