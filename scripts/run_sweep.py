#!/usr/bin/env python
"""Phase 8 restoration sweep: every config x every sample -> transcriptions.

Resumable: skips samples whose hyp file already exists. Progress is appended
incrementally so a dead tunnel loses at most one call.

Usage:
    python scripts/run_sweep.py --configs grayscale denoised --samples MT-001 MT-002
    python scripts/run_sweep.py --all          # 7 configs x 20 samples
    python scripts/run_sweep.py --all --dry-run  # show plan only

Outputs:
    experiments/results/sweep/EXP-005_{config}_{mid}_hyp.txt
    experiments/results/sweep_progress.csv (appended per call)
"""

import argparse
import csv
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.pipeline import run_full_pipeline
from backend.services.restoration.pipeline import PRESET_CONFIGS

ALL_IDS = [f"MT-{i:03d}" for i in range(1, 21)]
SWEEP_DIR = PROJECT_ROOT / "experiments" / "results" / "sweep"
PROGRESS = PROJECT_ROOT / "experiments" / "results" / "sweep_progress.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 8 sweep runner")
    parser.add_argument("--configs", nargs="*", default=None)
    parser.add_argument("--samples", nargs="*", default=None)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    configs = list(PRESET_CONFIGS) if args.all else (args.configs or [])
    samples = ALL_IDS if args.all else (args.samples or [])
    unknown = [c for c in configs if c not in PRESET_CONFIGS]
    if unknown:
        print(f"Unknown configs: {unknown}")
        sys.exit(1)

    jobs = [(c, m) for c in configs for m in samples
            if not (SWEEP_DIR / f"EXP-005_{c}_{m}_hyp.txt").exists()]
    print(f"configs={configs} samples={len(samples)} "
          f"pending={len(jobs)} (resume-skipped "
          f"{len(configs) * len(samples) - len(jobs)})", flush=True)
    if args.dry_run or not jobs:
        return

    SWEEP_DIR.mkdir(parents=True, exist_ok=True)
    if not PROGRESS.exists():
        with open(PROGRESS, "w", newline="") as f:
            csv.writer(f).writerow(
                ["timestamp", "config", "sample", "secs", "chars",
                 "status", "error"])

    done = 0
    for config, mid in jobs:
        t0 = time.perf_counter()
        status, err, nchars = "ok", "", 0
        try:
            out = run_full_pipeline(
                f"data/raw/mode_trans/{mid}.png", config,
                output_dir="data/processed/_pipeline")
            nchars = len(out.transcription)
            (SWEEP_DIR / f"EXP-005_{config}_{mid}_hyp.txt").write_text(
                out.transcription, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            status, err = "FAILED", f"{type(exc).__name__}: {exc}"[:160]
        dt = time.perf_counter() - t0
        with open(PROGRESS, "a", newline="") as f:
            csv.writer(f).writerow(
                [time.strftime("%Y-%m-%dT%H:%M:%S"), config, mid,
                 round(dt, 1), nchars, status, err])
        done += 1
        print(f"[{done}/{len(jobs)}] {config} {mid} {dt:.1f}s "
              f"chars={nchars} {status} {err}"[:160], flush=True)
    print("SWEEP BATCH DONE")


if __name__ == "__main__":
    main()
