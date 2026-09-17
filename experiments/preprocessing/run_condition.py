#!/usr/bin/env python
"""Run a single preprocessing condition (Phase 2 / experiment helper).

Parameterized alternative to one-script-per-condition: avoids duplicated
code (per PROJECT_GUIDE.md Section 19).

Usage:
    python experiments/preprocessing/run_condition.py --config enhanced
    python experiments/preprocessing/run_condition.py --config binarized --image data/raw/other.png
    python experiments/preprocessing/run_condition.py --list
"""

import argparse
import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
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
    parser = argparse.ArgumentParser(description="Run one restoration condition")
    parser.add_argument("--config", type=str, default=None,
                        help=f"Config name, one of {list(PRESET_CONFIGS)}")
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--list", action="store_true",
                        help="List available configs and exit")
    args = parser.parse_args()

    if args.list:
        print("Available configs:")
        for name, cfg in PRESET_CONFIGS.items():
            print(f"  - {name}: {cfg.to_dict()}")
        return

    if args.config not in PRESET_CONFIGS:
        print(f"Unknown config '{args.config}'. Available: {list(PRESET_CONFIGS)}")
        sys.exit(1)
    if not args.image.exists():
        print(f"Image not found: {args.image}")
        sys.exit(1)

    config = PRESET_CONFIGS[args.config]
    t0 = time.perf_counter()
    result = run_pipeline_on_file(
        input_path=args.image,
        config=config,
        output_path=OUTPUT_DIR / f"{args.config}_final.png",
        save_intermediates=True,
    )
    saved = save_intermediates(
        result, OUTPUT_DIR / args.config / "intermediates", prefix=f"{args.config}_"
    )
    elapsed = time.perf_counter() - t0
    print(f"[OK] config='{args.config}' stages={result.stage_names} "
          f"shape={result.final_image.shape} intermediates={len(saved)} "
          f"time={elapsed:.3f}s")


if __name__ == "__main__":
    main()
