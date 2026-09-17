#!/usr/bin/env python
"""Generate Phase 3 visual report: first-real-inference evidence + status.

Reads experiments/results/EXP-001_transcription.json (real model output) and
produces:
    docs/phase3_status_diagram.png   - system architecture with live/blocked paths
    docs/phase3_output_card.png       - rendered transcription (Devanagari font if available)
    docs/phase3_stats.png             - output stats + attempt timeline bars
"""

import json
import sys
import unicodedata
from pathlib import Path

import cv2

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DOCS = PROJECT_ROOT / "docs"
RESULTS = PROJECT_ROOT / "experiments" / "results"


def devanagari_font():
    for name in ("Nirmala UI", "Mangal", "Noto Sans Devanagari", "Kokila"):
        try:
            font_manager.findfont(name, fallback_to_default=False)
            return name
        except Exception:  # noqa: BLE001
            continue
    return None


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    exp = json.loads((RESULTS / "EXP-001_transcription.json").read_text(encoding="utf-8"))
    text = exp["text"]
    dev = sum(1 for c in text if "DEVANAGARI" in unicodedata.name(c, ""))
    digits = sum(1 for c in text if "DIGIT" in unicodedata.name(c, ""))

    # --- Fig 1: status diagram -------------------------------------------
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.axis("off")
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 5)
    boxes = [
        (0.3, 2.0, 2.0, 1.0, "Sample image\n552x424", "#fff3cd"),
        (3.0, 2.0, 2.2, 1.0, "FastAPI backend\nINFERENCE_MODE=colab", "#e8f0fe"),
        (6.0, 3.0, 2.4, 1.0, "LOCAL Qwen+LoRA\n(4-bit NF4)", "#f8d7da"),
        (6.0, 1.0, 2.4, 1.0, "COLAB Qwen+LoRA\nT4/A100 via ngrok", "#d4edda"),
        (9.4, 1.5, 3.0, 1.0, "EXP-001: 79 chars\n50 Devanagari (73.6s)", "#d4edda"),
    ]
    for x, y, w, h, label, color in boxes:
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=color, ec="black"))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=10)
    ax.annotate("", xy=(3.0, 2.5), xytext=(2.3, 2.5), arrowprops=dict(arrowstyle="->"))
    ax.annotate("", xy=(6.0, 3.4), xytext=(5.2, 2.7), arrowprops=dict(arrowstyle="->", color="red"))
    ax.annotate("", xy=(6.0, 1.6), xytext=(5.2, 2.3), arrowprops=dict(arrowstyle="->", color="green"))
    ax.annotate("", xy=(9.4, 2.0), xytext=(8.4, 1.6), arrowprops=dict(arrowstyle="->", color="green"))
    ax.text(5.6, 3.1, "BLOCKED\n(weights stall)", fontsize=8, color="red", ha="center")
    ax.text(5.6, 1.9, "LIVE", fontsize=9, color="green", ha="center", fontweight="bold")
    ax.set_title("Phase 3 — Inference path status (green = proven 2026-09-17)", fontsize=13)
    fig.tight_layout()
    fig.savefig(DOCS / "phase3_status_diagram.png", dpi=150)
    plt.close(fig)

    # --- Fig 2: output card -----------------------------------------------
    font = devanagari_font()
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.axis("off")
    ax.text(0.02, 0.85, "EXP-001 — first real transcription (Colab, 73.6s, original image)",
            fontsize=12, fontweight="bold", transform=ax.transAxes)
    kwargs = {"fontsize": 15} if font is None else {"fontsize": 15, "fontname": font}
    ax.text(0.02, 0.55, text, transform=ax.transAxes, va="top", ha="left", wrap=True, **kwargs)
    note = f"{len(text)} chars | {dev} Devanagari | {digits} Devanagari digits | font: {font or 'fallback (no Devanagari font)'}"
    ax.text(0.02, 0.08, note, fontsize=9, transform=ax.transAxes, color="#555555")
    ax.set_title("Model output rendered verbatim (unverified AI draft — not ground truth)",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(DOCS / "phase3_output_card.png", dpi=150)
    plt.close(fig)

    # --- Fig 3: stats -------------------------------------------------------
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    ax[0].bar(["total chars", "Devanagari", "digits", "spaces/other"],
              [len(text), dev, digits, len(text) - dev - digits])
    ax[0].set_title("EXP-001 output composition (real counts)")
    ax[1].barh(["local download\n(30 min)", "processor check", "stub client test", "EXP-001 colab\n(load+infer)"],
               [1800, 20, 4, 73.6], color=["red", "gray", "gray", "green"])
    ax[1].set_xlabel("seconds (log scale)")
    ax[1].set_xscale("log")
    ax[1].set_title("Phase 3 attempt timeline (real durations)")
    fig.suptitle("Phase 3 — Evidence summary", fontsize=13)
    fig.tight_layout()
    fig.savefig(DOCS / "phase3_stats.png", dpi=150)
    plt.close(fig)

    print(f"text={len(text)} dev={dev} digits={digits} font={font}")
    print("Saved 3 figures to docs/")


if __name__ == "__main__":
    main()
