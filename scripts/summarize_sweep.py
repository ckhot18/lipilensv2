#!/usr/bin/env python
"""Summarize the Phase 8 sweep: CER/WER per (config, sample) + aggregates.

Reads sweep hyp files + data/evaluation refs. Writes:
    experiments/results/sweep_metrics.csv   (one row per config x sample)
    experiments/results/sweep_summary.json  (means, stds, win/tie/loss vs original)
    docs/sweep_heatmap.png, docs/sweep_means.png
"""

import csv
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.evaluation.compute_metrics import cer, wer

ALL_IDS = [f"MT-{i:03d}" for i in range(1, 21)]
CONFIGS = ["original", "grayscale", "denoised", "enhanced",
           "binarized", "deskewed", "full_restoration"]
SWEEP_DIR = PROJECT_ROOT / "experiments" / "results" / "sweep"
RESULTS = PROJECT_ROOT / "experiments" / "results"
DOCS = PROJECT_ROOT / "docs"


def hyp_for(config: str, mid: str) -> str | None:
    if config == "original":
        # Original-condition hyps live under their EXP tags.
        tag = "EXP-002" if mid in ("MT-001", "MT-002", "MT-003") else "EXP-004"
        p = RESULTS / f"{tag}_{mid}_hyp.txt"
    else:
        p = SWEEP_DIR / f"EXP-005_{config}_{mid}_hyp.txt"
    return p.read_text(encoding="utf-8").strip() if p.exists() else None


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def main() -> None:
    rows = []
    for config in CONFIGS:
        for mid in ALL_IDS:
            hyp = hyp_for(config, mid)
            if hyp is None:
                continue
            ref = (PROJECT_ROOT / "data" / "evaluation" / f"{mid}_ref.txt"
                   ).read_text(encoding="utf-8").strip()
            rows.append({"config": config, "sample": mid,
                         "cer": round(cer(hyp, ref), 4),
                         "wer": round(wer(hyp, ref), 4),
                         "hyp_chars": len(hyp), "ref_chars": len(ref)})

    with open(RESULTS / "sweep_metrics.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)

    by_config: dict[str, dict] = {}
    orig = {r["sample"]: r["cer"] for r in rows if r["config"] == "original"}
    for config in CONFIGS:
        cers = [r["cer"] for r in rows if r["config"] == config]
        wers = [r["wer"] for r in rows if r["config"] == config]
        wins = ties = losses = 0
        for r in rows:
            if r["config"] != config or r["sample"] not in orig:
                continue
            d = orig[r["sample"]] - r["cer"]
            if d > 0.005:
                wins += 1
            elif d < -0.005:
                losses += 1
            else:
                ties += 1
        by_config[config] = {
            "n": len(cers), "mean_cer": round(mean(cers), 4),
            "std_cer": round(stdev(cers), 4),
            "mean_wer": round(mean(wers), 4),
            "std_wer": round(stdev(wers), 4),
            "wins_vs_original": wins, "ties": ties, "losses": losses,
        }
    summary = {"n_rows": len(rows), "by_config": by_config}
    (RESULTS / "sweep_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    # --- figures ---------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    present = [c for c in CONFIGS if by_config[c]["n"] > 0]
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    x = range(len(present))
    ax[0].bar(x, [by_config[c]["mean_cer"] for c in present],
              yerr=[by_config[c]["std_cer"] for c in present],
              capsize=4, color="steelblue")
    ax[0].set_xticks(list(x), present, rotation=20)
    ax[0].set_title("Mean CER ± std per condition")
    ax[1].bar(x, [by_config[c]["mean_wer"] for c in present],
              yerr=[by_config[c]["std_wer"] for c in present],
              capsize=4, color="darkorange")
    ax[1].set_xticks(list(x), present, rotation=20)
    ax[1].set_title("Mean WER ± std per condition")
    n = by_config[present[0]]["n"]
    fig.suptitle(f"Phase 8 sweep — {n}/20 samples per condition "
                 f"(descriptive, no significance claims)", fontsize=12)
    fig.tight_layout()
    fig.savefig(DOCS / "sweep_means.png", dpi=150)
    plt.close(fig)

    # Heatmap of CER: rows=configs, cols=samples.
    import numpy as np
    mat = np.full((len(present), len(ALL_IDS)), np.nan)
    lookup = {(r["config"], r["sample"]): r["cer"] for r in rows}
    for i, c in enumerate(present):
        for j, m in enumerate(ALL_IDS):
            mat[i, j] = lookup.get((c, m), np.nan)
    fig, ax = plt.subplots(figsize=(14, 4 + len(present) * 0.3))
    im = ax.imshow(mat, aspect="auto", vmin=0, vmax=0.7, cmap="RdYlGn_r")
    ax.set_yticks(range(len(present)), present)
    ax.set_xticks(range(len(ALL_IDS)), ALL_IDS, rotation=45, fontsize=8)
    ax.set_title("CER heatmap (green=low). Blank = pending.")
    fig.colorbar(im, ax=ax, label="CER")
    fig.tight_layout()
    fig.savefig(DOCS / "sweep_heatmap.png", dpi=150)
    plt.close(fig)
    print("saved sweep_metrics.csv, sweep_summary.json, sweep_means.png, "
          "sweep_heatmap.png")


if __name__ == "__main__":
    main()
