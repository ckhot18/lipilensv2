#!/usr/bin/env python
"""Generate Phase 2 visual report: metrics + graphs + diagrams.

Computes real image-quality metrics for each preset config output and
saves PNG figures + CSV/JSON artifacts. No model, DB, or API dependency.

Outputs:
    docs/phase2_comparison_grid.png
    docs/phase2_metrics.png
    docs/phase2_histograms.png
    docs/phase2_pipeline_diagram.png
    experiments/results/phase2_metrics.csv
    experiments/results/phase2_metrics.json
"""

import csv
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.restoration.pipeline import PRESET_CONFIGS, run_pipeline_on_file

SAMPLE = PROJECT_ROOT / "data" / "raw" / "sample_modi_page.png"
OUT_FINALS = PROJECT_ROOT / "data" / "outputs"
DOCS = PROJECT_ROOT / "docs"
RESULTS = PROJECT_ROOT / "experiments" / "results"

CONFIG_ORDER = ["original", "grayscale", "denoised", "enhanced",
                "binarized", "deskewed", "full_restoration"]


def to_gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def sharpness(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    rows = []
    finals = {}
    for name in CONFIG_ORDER:
        cfg = PRESET_CONFIGS[name]
        t0 = time.perf_counter()
        res = run_pipeline_on_file(SAMPLE, cfg, output_path=None,
                                   save_intermediates=True)
        elapsed = time.perf_counter() - t0
        finals[name] = res.final_image
        gray = to_gray(res.final_image)
        uniq = np.unique(gray)
        rows.append({
            "config": name,
            "stages": "+".join(res.stage_names),
            "n_stages": len(res.stage_names),
            "shape_h": res.final_image.shape[0],
            "shape_w": res.final_image.shape[1],
            "channels": 1 if res.final_image.ndim == 2 else res.final_image.shape[2],
            "mean": round(float(np.mean(gray)), 2),
            "std": round(float(np.std(gray)), 2),
            "min": int(gray.min()),
            "max": int(gray.max()),
            "sharpness_lap_var": round(sharpness(gray), 2),
            "unique_values": int(len(uniq)),
            "is_binary": bool(set(uniq.tolist()).issubset({0, 255})),
            "ink_pct": round(float(np.mean(gray < 128)) * 100, 2),
            "runtime_s": round(elapsed, 4),
        })

    # --- CSV + JSON ------------------------------------------------------
    with open(RESULTS / "phase2_metrics.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(RESULTS / "phase2_metrics.json", "w") as f:
        json.dump(rows, f, indent=2)
    print("Saved metrics CSV + JSON")

    # --- Fig 1: comparison grid ------------------------------------------
    fig, axes = plt.subplots(2, 4, figsize=(16, 9))
    axes = axes.ravel()
    for i, name in enumerate(CONFIG_ORDER):
        img = finals[name]
        show = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if img.ndim == 3 else img
        axes[i].imshow(show, cmap=None if img.ndim == 3 else "gray")
        axes[i].set_title(name, fontsize=12, fontweight="bold")
        axes[i].axis("off")
    # 8th panel: full_restoration intermediates mini-strip
    axes[7].axis("off")
    axes[7].text(0.5, 0.5,
                 "7 configs x sample_modi_page.png\n(552x424, mean=201.8)\n"
                 "see data/outputs/*_final.png",
                 ha="center", va="center", fontsize=11,
                 bbox=dict(boxstyle="round", fc="#f0f0f0"))
    fig.suptitle("Phase 2 — Restoration outputs per preprocessing config", fontsize=15)
    fig.tight_layout()
    fig.savefig(DOCS / "phase2_comparison_grid.png", dpi=150)
    plt.close(fig)

    # --- Fig 2: metric bars ----------------------------------------------
    names = [r["config"] for r in rows]
    x = np.arange(len(names))
    fig, ax = plt.subplots(2, 2, figsize=(14, 9))
    ax[0, 0].bar(x, [r["mean"] for r in rows])
    ax[0, 0].set_title("Mean intensity (brightness)")
    ax[0, 0].set_xticks(x, names, rotation=20)
    ax[0, 1].bar(x, [r["std"] for r in rows])
    ax[0, 1].set_title("Std-dev (global contrast)")
    ax[0, 1].set_xticks(x, names, rotation=20)
    ax[1, 0].bar(x, [r["sharpness_lap_var"] for r in rows])
    ax[1, 0].set_title("Sharpness (Laplacian variance)")
    ax[1, 0].set_xticks(x, names, rotation=20)
    ax[1, 1].bar(x, [r["runtime_s"] for r in rows])
    ax[1, 1].set_title("Pipeline runtime (s)")
    ax[1, 1].set_xticks(x, names, rotation=20)
    fig.suptitle("Phase 2 — Quantitative image metrics per config (real measurements)",
                 fontsize=14)
    fig.tight_layout()
    fig.savefig(DOCS / "phase2_metrics.png", dpi=150)
    plt.close(fig)

    # --- Fig 3: histograms ------------------------------------------------
    fig, axes = plt.subplots(2, 4, figsize=(16, 8), sharex=True, sharey=True)
    axes = axes.ravel()
    for i, name in enumerate(CONFIG_ORDER):
        gray = to_gray(finals[name])
        axes[i].hist(gray.ravel(), bins=64, range=(0, 255))
        axes[i].set_title(name, fontsize=11)
    axes[7].axis("off")
    fig.suptitle("Phase 2 — Pixel-intensity histograms per config", fontsize=14)
    fig.tight_layout()
    fig.savefig(DOCS / "phase2_histograms.png", dpi=150)
    plt.close(fig)

    # --- Fig 4: pipeline diagram ------------------------------------------
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.axis("off")
    stages_all = ["input\n(BGR)", "validate", "grayscale", "denoise",
                  "enhance\n(CLAHE)", "binarize\n(Otsu)", "borders\ncleanup", "deskew"]
    for i, s in enumerate(stages_all):
        ax.add_patch(plt.Rectangle((i * 1.7 + 0.2, 2.0), 1.4, 0.9,
                                   fc="#e8f0fe" if i else "#fff3cd", ec="black"))
        ax.text(i * 1.7 + 0.9, 2.45, s, ha="center", va="center", fontsize=9)
        if i:
            ax.annotate("", xy=(i * 1.7 + 0.2, 2.45), xytext=(i * 1.7 - 0.1, 2.45),
                        arrowprops=dict(arrowstyle="->"))
    cfg_paths = {
        "original": [0, 1],
        "grayscale": [0, 1, 2],
        "denoised": [0, 1, 2, 3],
        "enhanced": [0, 1, 2, 3, 4],
        "binarized": [0, 1, 2, 3, 4, 5],
        "deskewed": [0, 1, 2, 7],
        "full_restoration": [0, 1, 2, 3, 4, 5, 6, 7],
    }
    for j, (cfg, path) in enumerate(cfg_paths.items()):
        y = 1.4 - j * 0.18
        for k in range(len(path) - 1):
            x0 = path[k] * 1.7 + 0.9
            x1 = path[k + 1] * 1.7 + 0.9
            ax.annotate("", xy=(x1, y), xytext=(x0, y),
                        arrowprops=dict(arrowstyle="-", color=f"C{j}", lw=1.2))
        ax.text(12.3, y, cfg, fontsize=9, color=f"C{j}", va="center")
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 3.6)
    ax.set_title("Phase 2 — Pipeline stage map per preset config", fontsize=14)
    fig.tight_layout()
    fig.savefig(DOCS / "phase2_pipeline_diagram.png", dpi=150)
    plt.close(fig)

    print("Saved 4 figures to docs/")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
