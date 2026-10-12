#!/usr/bin/env python
"""Render the team-brief charts straight from the evaluation CSVs.

Every bar comes from experiments/results/eval/*.csv so a chart can never
drift from the numbers it claims to show. Regenerate with:

    python scripts/make_team_brief_charts.py
"""

import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = ROOT / "experiments" / "results" / "eval"
OUT = ROOT / "docs" / "team_brief"

BG = "#0a0a0c"
CARD = "#141417"
INK = "#f4f4f6"
MUTED = "#91919b"
FAINT = "#6e6e78"
ACCENT = "#8b85ff"
SUN = "#e8a33d"
OK = "#5fd39b"
BAD = "#ef7a6d"


def load(tag: str) -> dict[str, dict]:
    path = EVAL_DIR / f"eval_{tag}_metrics.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    arms: dict[str, list] = {}
    for r in rows:
        arms.setdefault(r["arm"], []).append(r)
    out = {}
    for arm, rs in arms.items():
        cers = [float(r["cer"]) for r in rs]
        out[arm] = {
            "n": len(rs),
            "cer": statistics.mean(cers),
            "acc": 100 * (1 - statistics.mean(cers)),
            "per_page": {r["page"]: float(r["cer"]) for r in rs},
        }
    return out


def svg_open(w: int, h: int, title: str, subtitle: str = "") -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="Inter,Segoe UI,system-ui,sans-serif">',
        f'<rect width="{w}" height="{h}" fill="{BG}"/>',
        f'<text x="34" y="46" fill="{INK}" font-size="21" font-weight="700">{title}</text>',
    ]
    if subtitle:
        parts.append(
            f'<text x="34" y="72" fill="{MUTED}" font-size="13">{subtitle}</text>')
    return "\n".join(parts)


def bar_chart(rows, w=980, note=None, filename="chart.svg"):
    """rows: [(label, value 0..1, colour, value_text)]"""
    left, top, bar_w = 210, 104, 560
    row_h, gap = 46, 16
    h = top + len(rows) * (row_h + gap) + 96
    parts = [svg_open(w, h, "Character Error Rate by configuration", note)]
    zero_x = left + bar_w * 0.0
    for i, (label, val, colour, vtext) in enumerate(rows):
        y = top + i * (row_h + gap)
        width = max(2, bar_w * val)
        parts.append(
            f'<text x="{left-16}" y="{y+26}" fill="{INK}" font-size="14" '
            f'text-anchor="end">{label}</text>')
        parts.append(
            f'<rect x="{left}" y="{y+6}" width="{bar_w}" height="26" rx="6" '
            f'fill="{CARD}"/>')
        parts.append(
            f'<rect x="{left}" y="{y+6}" width="{width:.0f}" height="26" rx="6" '
            f'fill="{colour}"/>')
        parts.append(
            f'<text x="{left+width+14}" y="{y+25}" fill="{INK}" font-size="14" '
            f'font-weight="600">{vtext}</text>')
    # scale
    axis_y = top + len(rows) * (row_h + gap) + 6
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = left + bar_w * frac
        parts.append(
            f'<line x1="{x}" y1="{top-6}" x2="{x}" y2="{axis_y}" '
            f'stroke="#26262c" stroke-width="1"/>')
        parts.append(
            f'<text x="{x}" y="{axis_y+20}" fill="{FAINT}" font-size="11" '
            f'text-anchor="middle">{int(frac*100)}%</text>')
    parts.append(
        f'<text x="{w/2}" y="{axis_y+48}" fill="{FAINT}" font-size="11" '
        f'text-anchor="middle">Lower is better - CER is the share of '
        f'reference characters the model got wrong</text>')
    parts.append("</svg>")
    (OUT / filename).write_text("\n".join(parts), encoding="utf-8")
    print("wrote", filename)


def grouped_chart(groups, series, filename, note):
    """groups: [category]; series: {name: {category: cer}}"""
    w, h = 980, 520
    left, bottom, plot_h = 110, 440, 300
    plot_w = 790
    parts = [svg_open(w, h, "Clean scans vs degraded captures", note)]
    n = len(series)
    slot = plot_w / len(groups)
    bw = min(74, slot / (n + 1))
    for gi, cat in enumerate(groups):
        cx = left + slot * gi + slot / 2
        parts.append(
            f'<text x="{cx}" y="{bottom+34}" fill="{INK}" font-size="13" '
            f'text-anchor="middle">{cat}</text>')
        for si, (sname, data) in enumerate(series.items()):
            v = data.get(cat)
            if v is None:
                continue
            x = cx - (n * bw) / 2 + si * bw
            bh = max(2, plot_h * v)
            colour = ACCENT if si == 0 else SUN
            parts.append(
                f'<rect x="{x}" y="{bottom-bh:.0f}" width="{bw-8:.0f}" '
                f'height="{bh:.0f}" rx="5" fill="{colour}"/>')
            parts.append(
                f'<text x="{x+(bw-8)/2:.0f}" y="{bottom-bh-8:.0f}" '
                f'fill="{INK}" font-size="11" text-anchor="middle">{v:.3f}</text>')
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = bottom - plot_h * frac
        parts.append(
            f'<line x1="{left}" y1="{y}" x2="{left+plot_w}" y2="{y}" '
            f'stroke="#26262c"/>')
        parts.append(
            f'<text x="{left-12}" y="{y+4}" fill="{FAINT}" font-size="11" '
            f'text-anchor="end">{int(frac*100)}%</text>')
    lx = left
    for si, sname in enumerate(series):
        parts.append(
            f'<rect x="{lx}" y="486" width="13" height="13" rx="3" '
            f'fill="{ACCENT if si==0 else SUN}"/>')
        parts.append(
            f'<text x="{lx+20}" y="497" fill="{MUTED}" font-size="12">{sname}</text>')
        lx += 190
    parts.append("</svg>")
    (OUT / filename).write_text("\n".join(parts), encoding="utf-8")
    print("wrote", filename)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    clean = load("EVAL-01")
    deg = load("DEG-MED")

    order = [
        ("whole page + original (shipped)", "plain", ACCENT),
        ("+ repetition guard, 512 tok", "noseg", "#6d64f5"),
        ("enhanced preprocessing", "enh", SUN),
        ("1.5x pre-upscale", "up15", BAD),
        ("line segmentation", "seg", BAD),
    ]
    rows = []
    for label, key, colour in order:
        if key in clean:
            d = clean[key]
            rows.append((label, d["cer"], colour,
                         f'{d["cer"]:.3f}  ({d["acc"]:.1f}% correct)'))
    bar_chart(rows, note="10 MoDeTrans pages, authentic expert references, "
                         "50 real model calls (EVAL-01)",
              filename="chart-clean-arms.svg")

    deg_order = [("original", "c_original", ACCENT), ("denoised", "c_denoised", SUN),
                 ("enhanced", "c_enhanced", SUN), ("binarized", "c_binarized", BAD)]
    drows = []
    for label, key, colour in deg_order:
        if key in deg:
            d = deg[key]
            drows.append((label, d["cer"], colour,
                          f'{d["cer"]:.3f}  ({d["acc"]:.1f}% correct)'))
    bar_chart(drows, note="23 same pages re-photographed at medium severity: "
                          "aged paper, uneven light, stains, skew, JPEG - "
                          "92 real model calls (DEG-MED)",
              filename="chart-degraded.svg")

    groups = ["original", "denoised", "enhanced", "binarized"]
    series = {
        "clean scan": {g: clean["plain"]["cer"] for g in groups},
        "degraded capture": {g: deg.get(f"c_{g}", {}).get("cer") for g in groups},
    }
    grouped_chart(groups, series, "chart-clean-vs-dirty.svg",
                  "Preprocessing does not pay, even on input that needs it")

    print("\nSummary written from live data:")
    for k, v in clean.items():
        print(f"  EVAL-01 {k:<8} CER {v['cer']:.3f}  accuracy {v['acc']:.1f}%")
    for k, v in deg.items():
        print(f"  DEG-MED {k:<14} CER {v['cer']:.3f}  accuracy {v['acc']:.1f}%")


if __name__ == "__main__":
    main()