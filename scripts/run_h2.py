#!/usr/bin/env python
"""H2 robustness batch: 6 samples x 4 inputs x 2 conditions (48 calls).

Inputs: clean (= mode_trans PNG) + blur/noise/fade variants.
Conditions: original (control) vs full_restoration.
Design: effect_clean vs effect_degraded per pair; H2 predicts the latter
is systematically larger in magnitude.

Resumable (skips existing hyps), fail-fast on dead tunnel.
Usage: python scripts/run_h2.py [--dry-run]
Output: experiments/results/h2/EXP-007_{input}_{cond}_hyp.txt + h2_progress.csv
"""

import argparse
import csv
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.pipeline import run_full_pipeline

SAMPLES = ["MT-048", "MT-002", "MT-014", "MT-020", "MT-011", "MT-003"]
INPUTS = ["clean", "blur", "noise", "fade"]  # clean = original file
CONDS = ["original", "full_restoration"]
H2_DIR = PROJECT_ROOT / "experiments" / "results" / "h2"
PROGRESS = PROJECT_ROOT / "experiments" / "results" / "h2_progress.csv"


def src_for(mid: str, inp: str) -> Path:
    if inp == "clean":
        return PROJECT_ROOT / "data" / "raw" / "mode_trans" / f"{mid}.png"
    return PROJECT_ROOT / "data" / "raw" / "degraded" / f"{mid}_{inp}.png"


def hyp_name(mid: str, inp: str, cond: str) -> str:
    return f"EXP-007_{mid}_{inp}_{cond}_hyp.txt"


def tunnel_alive() -> bool:
    try:
        from backend import config as app_config
        import requests
        if app_config.INFERENCE_MODE != "colab":
            return True
        r = requests.get(
            app_config.COLAB_ENDPOINT_URL.rstrip("/") + "/health", timeout=15)
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="H2 robustness batch")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    H2_DIR.mkdir(parents=True, exist_ok=True)
    # Clean inputs already transcribed earlier — copy, don't re-burn GPU:
    # originals live under EXP-002/004/006 names, full_restoration under sweep
    # (MT-001..020 only; MT-048 full must run live).
    def _tag(mid: str) -> str:
        n = int(mid.split("-")[1])
        return "EXP-002" if n <= 3 else ("EXP-004" if n <= 20 else "EXP-006")

    SWEEP = PROJECT_ROOT / "experiments" / "results" / "sweep"
    linked = 0
    for m in SAMPLES:
        pairs = [(f"{_tag(m)}_{m}_hyp.txt", f"clean_original"),
                 (f"sweep/EXP-005_full_restoration_{m}_hyp.txt",
                  "clean_full_restoration")]
        for src_rel, kind in pairs:
            dst = H2_DIR / f"EXP-007_{m}_{kind}_hyp.txt"
            src = PROJECT_ROOT / "experiments" / "results" / src_rel
            if not dst.exists() and src.exists():
                dst.write_text(src.read_text(encoding="utf-8"),
                               encoding="utf-8")
                linked += 1
    print(f"linked {linked} clean-input hyps from prior runs (no GPU cost)")

    jobs = [(m, i, c) for m in SAMPLES for i in INPUTS for c in CONDS
            if not (H2_DIR / hyp_name(m, i, c)).exists()]
    # Clean-input originals already exist from earlier EXPs — link, don't rerun.
    print(f"pending={len(jobs)} (resume-skipped {6 * 4 * 2 - len(jobs)})",
          flush=True)
    if args.dry_run or not jobs:
        return

    if not PROGRESS.exists():
        with open(PROGRESS, "w", newline="") as f:
            csv.writer(f).writerow(
                ["timestamp", "sample", "input", "cond", "secs", "chars",
                 "status", "error"])

    done = 0
    for mid, inp, cond in jobs:
        t0 = time.perf_counter()
        status, err, nchars = "ok", "", 0
        try:
            out = run_full_pipeline(src_for(mid, inp), cond,
                                    output_dir="data/processed/_pipeline")
            nchars = len(out.transcription)
            (H2_DIR / hyp_name(mid, inp, cond)).write_text(
                out.transcription, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            status, err = "FAILED", f"{type(exc).__name__}: {exc}"[:160]
        dt = time.perf_counter() - t0
        with open(PROGRESS, "a", newline="") as f:
            csv.writer(f).writerow(
                [time.strftime("%Y-%m-%dT%H:%M:%S"), mid, inp, cond,
                 round(dt, 1), nchars, status, err])
        done += 1
        print(f"[{done}/{len(jobs)}] {mid} {inp} {cond} {dt:.1f}s "
              f"chars={nchars} {status} {err}"[:160], flush=True)
        if status != "ok" and not tunnel_alive():
            print("TUNNEL DEAD — stopping. Re-run later (resume-safe).",
                  flush=True)
            break
    print("H2 BATCH DONE")


if __name__ == "__main__":
    main()
