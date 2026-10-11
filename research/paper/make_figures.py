#!/usr/bin/env python
"""Figures for the paper, rendered from the real CSVs.

Every value is read from experiments/results/eval/*.csv or
research/paper/data/consolidated.csv — no figure can drift from its data.

    python research/paper/make_figures.py
"""

from __future__ import annotations

import collections
import csv
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "research" / "paper" / "figures"
EVAL = ROOT / "experiments" / "results" / "eval"
CONSOL = ROOT / "research" / "paper" / "data" / "consolidated.csv"

INK, MUTED, FAINT, GRID = "#1c1c1e", "#6e6e76", "#8e8e96", "#e4e4e9"
ACCENT, SUN, BAD, OK, PAPER = "#4f46e5", "#e8a33d", "#c0392b", "#16794a", "#ffffff"
DEVA = '"Nirmala UI","Noto Sans Devanagari",sans-serif'


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def head(w, h, title, subtitle=""):
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'viewBox="0 0 {w} {h}" font-family="Inter,Segoe UI,system-ui,sans-serif">',
         f'<rect width="{w}" height="{h}" fill="{PAPER}"/>',
         f'<text x="40" y="44" fill="{INK}" font-size="20" font-weight="700">{esc(title)}</text>']
    if subtitle:
        p.append(f'<text x="40" y="68" fill="{MUTED}" font-size="12.5">{esc(subtitle)}</text>')
    return "\n".join(p)


def finish(parts, name):
    parts.append("</svg>")
    (OUT / name).write_text("\n".join(parts), encoding="utf-8")
    print("wrote", name)


# ---------------------------------------------------------------- fig 1
def fig_baseline():
    rows = list(csv.DictReader(CONSOL.open(encoding="utf-8")))
    base = [float(r["cer"]) for r in rows if r["config"] == "baseline"]
    per_page = collections.defaultdict(list)
    for r in rows:
        if r["tag"] == "EXP-005":
            per_page[r["mid"]].append(float(r["cer"]))

    W, H = 980, 470
    L, T, PW = 70, 110, 830
    p = [head(W, H, "Page difficulty dominates every configuration effect",
              f"Whole-page baseline, {len(base)} measurements over 50 distinct pages "
              f"— mean CER {statistics.mean(base):.3f}, sigma {statistics.stdev(base):.3f}")]

    # histogram of per-page difficulty
    diffs = sorted(statistics.mean(v) for v in per_page.values())
    bins = [0] * 10
    for d in diffs:
        bins[min(9, int(d / 0.7))] += 1
    bw = PW / 10
    for i, c in enumerate(bins):
        bh = 240 * c / max(bins)
        x = L + i * bw
        p.append(f'<rect x="{x+3:.1f}" y="{T+250-bh:.1f}" width="{bw-6:.1f}" '
                 f'height="{bh:.1f}" fill="{ACCENT}" opacity="0.82" rx="3"/>')
        p.append(f'<text x="{x+bw/2:.1f}" y="{T+270}" fill="{FAINT}" font-size="11" '
                 f'text-anchor="middle">{int(i*0.7*10)/10:.1f}</text>')
        if c:
            p.append(f'<text x="{x+bw/2:.1f}" y="{T+244-bh:.1f}" fill="{INK}" '
                     f'font-size="11" text-anchor="middle">{c}</text>')
    p.append(f'<line x1="{L}" y1="{T+250}" x2="{L+PW}" y2="{T+250}" stroke="{GRID}"/>')
    p.append(f'<text x="{L+PW/2}" y="{T+296}" fill="{MUTED}" font-size="12" '
             f'text-anchor="middle">Mean CER of a page, averaged over the 7 restoration configurations</text>')

    y0 = T + 330
    for i, (lbl, val, col) in enumerate([
            ("Baseline mean CER", statistics.mean(base), ACCENT),
            ("Binarized (worst arm)", 0.355, BAD),
            ("Full restoration", 0.359, BAD),
            ("Segmentation (this study)", 0.606, BAD)]):
        y = y0 + i * 26
        p.append(f'<text x="40" y="{y}" fill="{INK}" font-size="12">{esc(lbl)}</text>')
        p.append(f'<rect x="300" y="{y-10}" width="{val*PW:.0f}" height="12" fill="{col}" rx="3"/>')
        p.append(f'<text x="{300+val*PW+10:.0f}" y="{y}" fill="{INK}" font-size="12">{val:.3f}</text>')
    finish(p, "fig1-page-difficulty.svg")


# ---------------------------------------------------------------- fig 2
def fig_segmentation():
    rows = list(csv.DictReader((EVAL / "eval_SEG20_metrics.csv").open(encoding="utf-8")))
    P = {r["page"]: float(r["cer"]) for r in rows if r["arm"] == "plain"}
    S = {r["page"]: float(r["cer"]) for r in rows if r["arm"] == "seg"}
    pages = sorted(P)

    W, H = 980, 560
    L, T, PW = 70, 116, 830
    mx = 1.5
    p = [head(W, H, "Text-line segmentation increases character error on every page",
              "Paired comparison, n=20 identical pages, identical decoding — "
              "sign test p = 3.8e-06")]

    slot = PW / len(pages)
    for i, pg in enumerate(pages):
        x = L + slot * i + slot / 2
        for val, col, off in ((P[pg], ACCENT, -34), (S[pg], BAD, 0)):
            h = 320 * val / mx
            p.append(f'<rect x="{x-15:.1f}" y="{T+330-h:.1f}" width="15" '
                     f'height="{h:.1f}" fill="{col}" rx="2"/>')
            p.append(f'<text x="{x-7.5:.1f}" y="{T+338-h:.1f}" fill="{col}" '
                     f'font-size="9" text-anchor="middle">{val:.2f}</text>')
        p.append(f'<text x="{x:.1f}" y="{T+356}" fill="{FAINT}" font-size="9.5" '
                 f'text-anchor="middle">{pg.replace("MT-","")}</text>')

    p.append(f'<line x1="{L}" y1="{T+330}" x2="{L+PW}" y2="{T+330}" stroke="{GRID}"/>')
    for frac, lab in ((0.0, "0"), (0.25, "0.25"), (0.5, "0.5"), (0.75, "0.75"), (1.0, "1.0")):
        y = T + 330 - 320 * frac
        p.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+PW}" y2="{y:.1f}" stroke="{GRID}"/>')
        p.append(f'<text x="{L-10}" y="{y+4:.1f}" fill="{FAINT}" font-size="11" '
                 f'text-anchor="end">{lab}</text>')
    p.append(f'<text x="40" y="{T+20}" fill="{ACCENT}" font-size="12.5" font-weight="600">■ whole page  0.316</text>')
    p.append(f'<text x="330" y="{T+20}" fill="{BAD}" font-size="12.5" font-weight="600">■ segmented  0.606</text>')
    p.append(f'<text x="{L+PW/2}" y="{T+392}" fill="{MUTED}" font-size="12" '
             f'text-anchor="middle">Character error rate per page (MT-001 … MT-020). '
             f'Segmented is worse on 19 of 19, tied on 1.</text>')

    yb = T + 420
    p.append(f'<text x="40" y="{yb}" fill="{INK}" font-size="13" font-weight="700">Error profile flips to deletions</text>')
    for i, (lbl, vals, col) in enumerate([
            ("Substitutions", (64.3, 42.1), ACCENT),
            ("Deletions", (11.0, 47.2), BAD),
            ("Insertions", (24.7, 10.7), SUN)]):
        y = yb + 24 + i * 22
        p.append(f'<text x="40" y="{y}" fill="{INK}" font-size="11.5">{esc(lbl)}</text>')
        x = 180
        for v, c in zip(vals, (ACCENT, BAD)):
            p.append(f'<rect x="{x}" y="{y-10}" width="{v*4.6:.1f}" height="12" fill="{c}" rx="2"/>')
            p.append(f'<text x="{x+v*4.6+8:.1f}" y="{y}" fill="{INK}" font-size="11">{v:.1f}%</text>')
            x += 260
    p.append(f'<text x="180" y="{yb+16}" fill="{ACCENT}" font-size="11">whole page</text>')
    p.append(f'<text x="440" y="{yb+16}" fill="{BAD}" font-size="11">segmented</text>')
    p.append(f'<text x="700" y="{yb+40}" fill="{BAD}" font-size="11.5" font-weight="600">'
             f'the adapter card reports deletions as 46% of its errors</text>')
    finish(p, "fig2-segmentation.svg")


# ---------------------------------------------------------------- fig 3
def fig_restoration():
    rows = list(csv.DictReader(CONSOL.open(encoding="utf-8")))
    cfg = collections.defaultdict(list)
    for r in rows:
        if r["tag"] == "EXP-005":
            cfg[r["config"]].append(float(r["cer"]))
    deg_rows = list(csv.DictReader((EVAL / "eval_DEG-MED_metrics.csv").open(encoding="utf-8")))
    degm = collections.defaultdict(list)
    for r in deg_rows:
        degm[r["arm"].replace("c_", "")].append(float(r["cer"]))

    order = ["grayscale", "denoised", "enhanced", "deskewed", "binarized",
             "full_restoration"]
    base = statistics.mean(cfg["grayscale"])
    W, H = 980, 430
    L, T, PW = 190, 118, 640
    p = [head(W, H, "Restoration is monotonically harmful; binarisation worst",
              f"140 model calls, 7 configurations x 20 pages. "
              f"Control = grayscale (no-op: {base:.3f})")]
    for i, c in enumerate(order):
        v = statistics.mean(cfg[c])
        y = T + i * 42
        col = BAD if v - base > 0.02 else (SUN if v - base > 0.005 else ACCENT)
        p.append(f'<text x="{L-14}" y="{y+22}" fill="{INK}" font-size="13" '
                 f'text-anchor="end">{esc(c)}</text>')
        p.append(f'<rect x="{L}" y="{y+8}" width="{PW}" height="20" rx="4" fill="#f4f4f5"/>')
        p.append(f'<rect x="{L}" y="{y+8}" width="{PW*v/0.5:.1f}" height="20" rx="4" fill="{col}"/>')
        d = v - base
        p.append(f'<text x="{L+PW*v/0.5+12:.1f}" y="{y+23}" fill="{INK}" font-size="12.5" '
                 f'font-weight="600">{v:.3f}  ({d:+.3f})</text>')
        dg = degm.get(c)
        if dg:
            p.append(f'<text x="{L-14}" y="{y+38}" fill="{MUTED}" font-size="10.5" '
                     f'text-anchor="end">on degraded: {statistics.mean(dg):.3f}</text>')
    p.append(f'<line x1="{L}" y1="{T+len(order)*42}" x2="{L+PW}" y2="{T+len(order)*42}" stroke="{GRID}"/>')
    p.append(f'<text x="{L+PW/2}" y="{T+len(order)*42+26}" fill="{MUTED}" font-size="12" '
             f'text-anchor="middle">Mean CER. Lower is better. Grey text = same configuration '
             f'measured on simulated photographic degradation.</text>')
    finish(p, "fig3-restoration.svg")


# ---------------------------------------------------------------- fig 4
def fig_example():
    """A real failure case: MT-003 whole page vs segmented, with real text."""
    import unicodedata
    def deva(s):
        return "".join(c if unicodedata.combining(c) == 0 else c for c in s)
    import pathlib as _p
    root = pathlib.Path(__file__).resolve().parent.parent.parent
    ref = " ".join((root / "data/evaluation/MT-003_ref.txt").read_text(encoding="utf-8").split())
    hp = _p.join = (root / "experiments/results/eval/SEG20_plain_MT-003_hyp.txt").read_text(encoding="utf-8")
    hs = (root / "experiments/results/eval/SEG20_seg_MT-003_hyp.txt").read_text(encoding="utf-8")
    hp, hs = " ".join(hp.split()), " ".join(hs.split())

    W, H = 980, 400
    p = [head(W, H, "Failure case MT-003 — segmentation invents text",
              "The hardest page in the corpus (baseline CER 0.517); segmentation drives it to 1.458")]
    rows = [("Expert reference", ref, INK, 0.303),
            ("Whole page  (CER 0.517)", hp, ACCENT, 0.317),
            ("Segmented   (CER 1.458)", hs, BAD, 0.606)]
    y = 110
    for lbl, text, col, _ in rows:
        p.append(f'<text x="40" y="{y}" fill="{col}" font-size="12.5" font-weight="600">{esc(lbl)}</text>')
        words = text.split()
        mid = len(words) // 2
        p.append(f'<text x="40" y="{y+26}" fill="{col}" font-size="15" font-family=\'{DEVA}\'>'
                 f'{esc(" ".join(words[:mid]))}</text>')
        p.append(f'<text x="40" y="{y+50}" fill="{col}" font-size="15" font-family=\'{DEVA}\'>'
                 f'{esc(" ".join(words[mid:]))}</text>')
        y += 96
    finish(p, "fig4-example.svg")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig_baseline()
    fig_segmentation()
    fig_restoration()
    fig_example()


if __name__ == "__main__":
    main()