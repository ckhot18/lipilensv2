#!/usr/bin/env python
"""Generate Phase 4 visual report: integration proof + first restoration effect.

Outputs:
    docs/phase4_sequence.png            - pipeline stages with real timings
    docs/phase4_restoration_effect.png  - CER/WER original vs enhanced vs binarized (MT-002)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Real measurements (EXP-002b, EXP-003a/b, MT-002, Colab warm).
CER = {"original": 0.099, "enhanced": 0.121, "binarized": 0.176}
WER = {"original": 0.286, "enhanced": 0.286, "binarized": 0.286}
RESTORE_S = {"enhanced": 0.18, "binarized": 0.21}
TRANSCRIBE_S = {"enhanced": 18.5, "binarized": 18.6}


def main() -> None:
    # --- Fig 1: sequence with timings ------------------------------------
    fig, ax = plt.subplots(figsize=(13, 4))
    ax.axis("off")
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 4)
    steps = [
        (0.2, "load image\nMT-002.png", "~0.01s"),
        (3.0, "restore\n(CLAHE / Otsu)", "0.18 / 0.21s"),
        (5.8, "save restored\nPNG to disk", "~0.01s"),
        (8.4, "transcribe\n(Colab Qwen+LoRA)", "18.5 / 18.6s"),
        (11.0, "PipelineOutput\ntext + timings", "—"),
    ]
    for i, (x, label, t) in enumerate(steps):
        ax.add_patch(plt.Rectangle((x, 1.4), 1.9, 1.2, fc="#e8f0fe", ec="black"))
        ax.text(x + 0.95, 2.1, label, ha="center", va="center", fontsize=10)
        ax.text(x + 0.95, 1.15, t, ha="center", va="center", fontsize=9, color="#555555")
        if i:
            ax.annotate("", xy=(x, 2.0), xytext=(x - 0.25, 2.0),
                        arrowprops=dict(arrowstyle="->"))
    ax.text(6.5, 3.2, "Phase 4 — one function: run_full_pipeline() (no DB, no API)",
            ha="center", fontsize=12, fontweight="bold")
    ax.text(6.5, 0.6, "Model always receives the restored FILE (never the original object). "
                       "Restoration failure -> fall back to original + warning.",
            ha="center", fontsize=9, color="#555555")
    fig.tight_layout()
    fig.savefig("docs/phase4_sequence.png", dpi=150)
    plt.close(fig)

    # --- Fig 2: first restoration effect -----------------------------------
    names = ["original", "enhanced", "binarized"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    colors = ["green", "orange", "red"]
    ax[0].bar(names, [CER[n] for n in names], color=colors)
    ax[0].set_title("CER on MT-002 (lower is better)")
    ax[0].set_ylim(0, 0.22)
    for i, n in enumerate(names):
        ax[0].text(i, CER[n] + 0.005, f"{CER[n]:.3f}", ha="center")
    ax[1].bar(names, [WER[n] for n in names], color=colors)
    ax[1].set_title("WER on MT-002 (identical — char-level damage only)")
    ax[1].set_ylim(0, 0.4)
    fig.suptitle("EXP-002b/003 — first restoration comparison (n=1 page, descriptive only)",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig("docs/phase4_restoration_effect.png", dpi=150)
    plt.close(fig)
    print("Saved 2 figures to docs/")


if __name__ == "__main__":
    main()
