#!/usr/bin/env python
"""Qualitative figure: MT-002 under original/binarized/full_restoration.

Reproducible from tracked inputs (images are gitignored scratch, so the
script regenerates any missing restored variant CPU-only via run_pipeline).
Output: experiments/results/qualitative/fig_mt002_conditions.png
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

QUAL = PROJECT_ROOT / "experiments" / "results" / "qualitative"
QUAL.mkdir(parents=True, exist_ok=True)

# (condition, CER from sweep_metrics.csv)
PANELS = [("original", 0.099), ("binarized", 0.176), ("full_restoration", 0.242)]


def ensure_variant(condition: str) -> Path:
    p = (PROJECT_ROOT / "data" / "processed" / "_pipeline" /
         f"MT-002_{condition}.png")
    if p.exists() or condition == "original":
        return (PROJECT_ROOT / "data" / "raw" / "mode_trans" / "MT-002.png"
                if condition == "original" else p)
    from backend.services.pipeline import run_full_pipeline
    out = run_full_pipeline(f"data/raw/mode_trans/MT-002.png", condition,
                            output_dir="data/processed/_pipeline")
    return Path(out.restored_image_path)


def main() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (cond, cer) in zip(axes, PANELS):
        img = cv2.imread(str(ensure_variant(cond)), cv2.IMREAD_COLOR)
        ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        ax.set_title(f"{cond}\nCER {cer:.3f}", fontsize=12)
        ax.axis("off")
    fig.suptitle("MT-002 (best baseline, CER 0.099): heavier processing visibly\n"
                 "strips faint strokes — binarized/full_restoration damage is "
                 "visible, not just numeric", fontsize=12)
    fig.tight_layout()
    fig.savefig(QUAL / "fig_mt002_conditions.png", dpi=150)
    print("saved", QUAL / "fig_mt002_conditions.png")


if __name__ == "__main__":
    main()
