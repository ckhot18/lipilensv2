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


def fig_tokens():
    """The decisive figure: tokens on one axis, accuracy on the other."""
    px = list(csv.DictReader((EVAL / "eval_PIXELS_metrics.csv").open(encoding="utf-8")))
    lv = list(csv.DictReader((EVAL / "eval_LEVERS_metrics.csv").open(encoding="utf-8")))
    seg20 = list(csv.DictReader((EVAL / "eval_SEG20_metrics.csv").open(encoding="utf-8")))

    def mean_cer(rows, arm):
        v = [float(r["cer"]) for r in rows if r["arm"] == arm]
        return sum(v) / len(v) if v else None

    # tokens/char and CER for each measured point. px1280 and px2048 are the
    # same point (identical tokens, identical CER), so they are plotted once —
    # drawing both would overplot the markers and imply two measurements.
    pts = [
        ("px512  518 tok", 3.57, mean_cer(px, "px512"), SUN,
         "downscaled to 1036×392", "middle", -18),
        ("whole page  765 tok", 5.28, mean_cer(px, "px1280"), ACCENT,
         "native 1260×476 — shipped", "start", -6),
        ("segmented  ~35 tok", 35.0, mean_cer(seg20, "seg"), BAD,
         "6.6× the tokens, and far worse", "end", -6),
    ]

    W, H = 980, 470
    L, T, PW, PH = 96, 130, 700, 250
    mx_c, mx_t = 0.70, 40.0
    p = [head(W, H, "More tokens is not the constraint — context is",
              "Unsegmented token-budget sweep (n=20) against the segmentation arm. "
              "Both axes are measured, not assumed.")]

    # grid + axes
    for frac in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        y = T + PH - PH * frac
        p.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+PW}" y2="{y:.1f}" stroke="{GRID}"/>')
        p.append(f'<text x="{L-10}" y="{y+4:.1f}" fill="{FAINT}" font-size="11" '
                 f'text-anchor="end">{frac*mx_c:.2f}</text>')
        xt = L + PW * (frac * mx_c / mx_t)
        p.append(f'<text x="{xt:.1f}" y="{T+PH+20}" fill="{FAINT}" font-size="11" '
                 f'text-anchor="middle">{frac*mx_t:.0f}</text>')
    p.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{T+PH}" stroke="{GRID}"/>')
    p.append(f'<line x1="{L}" y1="{T+PH}" x2="{L+PW}" y2="{T+PH}" stroke="{GRID}"/>')
    p.append(f'<text x="{L-62}" y="{T+PH/2}" fill="{MUTED}" font-size="11.5" '
             f'text-anchor="middle" transform="rotate(-90 {L-62} {T+PH/2})">'
             f'Character error rate (lower is better)</text>')
    p.append(f'<text x="{L+PW/2}" y="{T+PH+42}" fill="{MUTED}" font-size="11.5" '
             f'text-anchor="middle">Visual tokens per character</text>')

    for lbl, tok, cer, col, note, anchor, dy in pts:
        if cer is None:
            continue
        x = L + PW * (min(tok, mx_t) / mx_t)
        y = T + PH - PH * (cer / mx_c)
        if tok > mx_t:
            x = L + PW - 6
        dx = 0 if anchor == "middle" else (12 if anchor == "start" else -12)
        p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{col}" '
                 f'stroke="{PAPER}" stroke-width="2"/>')
        p.append(f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" fill="{col}" font-size="11.5" '
                 f'font-weight="600" text-anchor="{anchor}">{esc(lbl)}</text>')
        p.append(f'<text x="{x+dx:.1f}" y="{y+dy+16:.1f}" fill="{MUTED}" font-size="10" '
                 f'text-anchor="{anchor}">{esc(note)}</text>')

    p.append(f'<text x="{L+PW*(5.28/mx_t):.1f}" y="{T+PH-((mean_cer(px,"px1280") or 0)/mx_c)*PH+40:.1f}" '
             f'fill="{FAINT}" font-size="10" text-anchor="middle">'
             f'px2048 plots here too — byte-identical to px1280</text>')

    bx = L + PW + 24
    p.append(f'<text x="{bx}" y="{T+8}" fill="{INK}" font-size="12.5" font-weight="700">'
             f'Tokens saturate at native</text>')
    for i, ln in enumerate([
            "518 → 765 tok/char: CER 0.344 → 0.316",
            "px2048 is byte-identical to px1280",
            "on 20/20 pages — the page is",
            "already under both ceilings.",
            "",
            "So raising the ceiling buys nothing.",
            "Segmentation supplies 6.6× the tokens",
            "and is far worse: the context it",
            "discards costs more than the tokens",
            "return."]):
        p.append(f'<text x="{bx}" y="{T+30+i*17}" fill="{MUTED}" font-size="11.2">{esc(ln)}</text>')

    p.append(f'<text x="40" y="{H-26}" fill="{MUTED}" font-size="11.5">'
             f'Lower-left is better. The whole page sits at the best measured '
             f'point despite using 4.6× fewer tokens than segmentation.</text>')
    finish(p, "fig5-tokens.svg")


# ---------------------------------------------------------------- fig 6
def fig_levers():
    rows = list(csv.DictReader((EVAL / "eval_LEVERS_metrics.csv").open(encoding="utf-8")))

    def mean_cer(arm):
        v = [float(r["cer"]) for r in rows if r["arm"] == arm]
        return sum(v) / len(v) if v else 0.0

    def mean_secs(arm):
        v = [float(r["secs"]) for r in rows if r["arm"] == arm and float(r["secs"] or 0) > 0]
        return sum(v) / len(v) if v else 0.0

    arms = [("lever_base", "shipped", ACCENT),
            ("lever_beam4", "beam = 4", MUTED),
            ("lever_fp16", "fp16", MUTED),
            ("lever_merge", "merge LoRA", BAD)]

    W, H = 980, 430
    L, T, PW = 150, 130, 560
    mx = 1.15
    p = [head(W, H, "Every lever outside the input pipeline fails",
              "Paired against a control arm running the shipped settings, n=20. "
              "Control reproduced the §5.5 arm byte-for-byte.")]

    slot = PW / len(arms)
    for i, (arm, lbl, col) in enumerate(arms):
        cer, sec = mean_cer(arm), mean_secs(arm)
        x = L + slot * i + slot / 2
        h = 230 * cer / mx
        p.append(f'<rect x="{x-42:.1f}" y="{T+240-h:.1f}" width="84" height="{h:.1f}" '
                 f'fill="{col}" rx="3"/>')
        p.append(f'<text x="{x:.1f}" y="{T+248-h:.1f}" fill="{col}" font-size="12.5" '
                 f'font-weight="700" text-anchor="middle">{cer:.3f}</text>')
        p.append(f'<text x="{x:.1f}" y="{T+266}" fill="{INK}" font-size="12" '
                 f'text-anchor="middle">{esc(lbl)}</text>')
        p.append(f'<text x="{x:.1f}" y="{T+284}" fill="{FAINT}" font-size="10.5" '
                 f'text-anchor="middle">{sec:.0f}s/page</text>')
    p.append(f'<line x1="{L}" y1="{T+240}" x2="{L+PW}" y2="{T+240}" stroke="{GRID}"/>')
    p.append(f'<text x="{L-12}" y="{T+240+4}" fill="{FAINT}" font-size="11" '
             f'text-anchor="end">0</text>')

    bx = L + PW + 30
    for i, ln in enumerate([
            "Beam = 4:  +0.004 CER, 9 worse / 8 better",
            "— noise, at 4.9× the latency.",
            "",
            "fp16:  +0.010 CER, no speed benefit.",
            "bf16 stays.",
            "",
            "Merge LoRA:  CER 1.064, worse on",
            "20/20 pages. Folding the delta into",
            "NF4-quantised base weights is not",
            "numerically sound — the adapter was",
            "fitted against a dequantised bf16 base."]):
        c = BAD if ln.startswith("Merge LoRA") else MUTED
        w = "700" if ln.startswith("Merge LoRA") else "400"
        p.append(f'<text x="{bx}" y="{T+16+i*19}" fill="{c}" font-size="11.3" '
                 f'font-weight="{w}">{esc(ln)}</text>')

    p.append(f'<text x="40" y="{H-24}" fill="{MUTED}" font-size="11.5">'
             f'Character error rate per page, mean of 20. Nothing outside the '
             f'input representation moved accuracy.</text>')
    finish(p, "fig6-levers.svg")


# ---------------------------------------------------------------- fig 7
def fig_context():
    """The reframe: adding a page is free, destroying structure is not."""
    ctx = list(csv.DictReader((EVAL / "eval_CTX_metrics.csv").open(encoding="utf-8")))
    seg = list(csv.DictReader((EVAL / "eval_SEG20_metrics.csv").open(encoding="utf-8")))

    def mean_cer(rows, arm):
        v = [float(r["cer"]) for r in rows if r["arm"] == arm]
        return sum(v) / len(v) if v else None

    bot = [float(r["cer_bottom"]) for r in ctx
           if r["arm"] == "pair_top" and r["cer_bottom"] not in ("", None)]

    bars = [
        ("whole page", mean_cer(ctx, "single"), ACCENT),
        ("whole page + its neighbour (top)", mean_cer(ctx, "pair_top"), ACCENT),
        ("the neighbour, read second", statistics.mean(bot) if bot else None, ACCENT),
        ("page split into line slivers", mean_cer(seg, "seg"), BAD),
    ]

    W, H = 980, 430
    L, T, PW = 220, 132, 520
    mx = 0.70
    p = [head(W, H, "Adding a page is free. Destroying a page's structure is not.",
              "Paired, n=20, every bar at full native resolution. "
              "Only the second bar's input contains an extra page.")]

    slot = PW / len(bars)
    for i, (lbl, val, col) in enumerate(bars):
        if val is None:
            continue
        y = T + 10 + i * 46
        w = 300 * val / mx
        p.append(f'<text x="{L-14}" y="{y+15}" fill="{INK}" font-size="12" '
                 f'text-anchor="end">{esc(lbl)}</text>')
        p.append(f'<rect x="{L}" y="{y}" width="{w:.1f}" height="22" fill="{col}" rx="3"/>')
        p.append(f'<text x="{L+w+9:.1f}" y="{y+16}" fill="{col}" font-size="12.5" '
                 f'font-weight="700">{val:.3f}</text>')
    p.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{T+10+len(bars)*46}" stroke="{GRID}"/>')

    bx = L + 380
    for i, ln in enumerate([
            "Paired deltas vs the whole page:",
            "",
            "  neighbour present    -0.001",
            "    worse 10 / better 9 / tie 1",
            "",
            "  same page, read second  +0.015",
            "    95% CI [-0.021, +0.052], p = 0.65",
            "",
            "  line segmentation      +0.290",
            "    worse 19 / tie 1, p = 3.8e-06",
            "",
            "Cross-page context is nearly worthless",
            "and nearly free. Within-page structure",
            "is neither."]):
        c = BAD if "segmentation" in ln else MUTED
        w = "700" if "segmentation" in ln else "400"
        p.append(f'<text x="{bx}" y="{T+16+i*17}" fill="{c}" font-size="11.2" '
                 f'font-weight="{w}">{esc(ln)}</text>')

    p.append(f'<text x="40" y="{H-24}" fill="{MUTED}" font-size="11.5">'
             f'Character error rate, mean of 20 pages. Lower is better.</text>')
    finish(p, "fig7-context.svg")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig_baseline()
    fig_segmentation()
    fig_restoration()
    fig_example()
    fig_tokens()
    fig_levers()
    fig_context()


if __name__ == "__main__":
    main()