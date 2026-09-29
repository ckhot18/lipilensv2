#!/usr/bin/env python
"""Score the H2 robustness test: paired restoration effects, clean vs degraded.

For each (sample, input): effect = CER(full_restoration) - CER(original).
H2 predicts |effect_degraded| > |effect_clean| systematically.
Also reports degradation cost = CER(degraded+original) - CER(clean+original).

Reads experiments/results/h2/ hyps + data/evaluation refs. Writes
h2_metrics.csv/json + docs/h2_effects.png. Pure offline.
"""

import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.evaluation.compute_metrics import cer

SAMPLES = ["MT-048", "MT-002", "MT-014", "MT-020", "MT-011", "MT-003"]
INPUTS = ["clean", "blur", "noise", "fade"]
H2_DIR = PROJECT_ROOT / "experiments" / "results" / "h2"
RESULTS = PROJECT_ROOT / "experiments" / "results"
DOCS = PROJECT_ROOT / "docs"


def main() -> None:
    rows = []
    for mid in SAMPLES:
        ref = (PROJECT_ROOT / "data" / "evaluation" / f"{mid}_ref.txt"
               ).read_text(encoding="utf-8").strip()
        for inp in INPUTS:
            cell = {}
            for cond in ("original", "full_restoration"):
                p = H2_DIR / f"EXP-007_{mid}_{inp}_{cond}_hyp.txt"
                if not p.exists():
                    cell = {}
                    break
                cell[cond] = cer(p.read_text(encoding="utf-8").strip(), ref)
            if cell:
                rows.append({"sample": mid, "input": inp,
                             "cer_original": round(cell["original"], 4),
                             "cer_full": round(cell["full_restoration"], 4),
                             "effect": round(cell["full_restoration"] -
                                             cell["original"], 4)})
    if not rows:
        print("no complete H2 pairs yet")
        return

    with open(RESULTS / "h2_metrics.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)

    clean_fx = {r["sample"]: r["effect"] for r in rows
                if r["input"] == "clean"}
    pairs = [(r["sample"], r["input"], abs(r["effect"]),
              abs(clean_fx[r["sample"]]))
             for r in rows if r["input"] != "clean"]
    bigger = sum(1 for _, _, d, c in pairs if d > c + 0.005)
    smaller = sum(1 for _, _, d, c in pairs if d < c - 0.005)
    summary = {
        "n_pairs": len(pairs),
        "degraded_effect_bigger": bigger,
        "ties": len(pairs) - bigger - smaller,
        "clean_effect_bigger": smaller,
        "mean_abs_effect_degraded": round(
            sum(d for _, _, d, _ in pairs) / len(pairs), 4),
        "mean_abs_effect_clean": round(
            sum(c for _, _, _, c in pairs) / len(pairs), 4),
    }
    (RESULTS / "h2_summary.json").write_text(json.dumps(
        {"rows": rows, "summary": summary}, indent=2))
    print(json.dumps(summary, indent=2))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    labels = [f"{s}\n{i}" for s, i, _, _ in pairs]
    x = np.arange(len(pairs))
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.bar(x - 0.2, [d for _, _, d, _ in pairs], 0.4, label="|effect| degraded")
    ax.bar(x + 0.2, [c for _, _, _, c in pairs], 0.4,
           label="|effect| clean (same sample)")
    ax.set_xticks(x, labels, rotation=45, fontsize=8)
    ax.set_ylabel("|CER(full) - CER(original)|")
    ax.set_title("H2: restoration effect size — degraded vs clean inputs "
                 f"({bigger}/{len(pairs)} bigger when degraded)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(DOCS / "h2_effects.png", dpi=150)
    print("saved h2_metrics.csv/json, h2_effects.png")


if __name__ == "__main__":
    main()
