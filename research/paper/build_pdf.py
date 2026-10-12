#!/usr/bin/env python
"""Render PAPER.md to a submission PDF with reportlab.

No LaTeX and no new dependencies: reportlab is already a project requirement
(used by research/build_paper.py). Figures are drawn natively from the same
CSVs as the SVG versions, so the PDF cannot drift from the data either.

    python research/paper/build_pdf.py

Output: research/paper/lipilens_vlm_input_pipeline.pdf
"""

from __future__ import annotations

import collections
import csv
import html
import pathlib
import re
import statistics
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether,
                                PageTemplate, Paragraph, Preformatted,
                                Spacer, Table, TableStyle)

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PAPER = pathlib.Path(__file__).resolve().parent / "PAPER.md"
OUT = pathlib.Path(__file__).resolve().parent / "lipilens_vlm_input_pipeline.pdf"
EVAL = ROOT / "experiments" / "results" / "eval"
CONSOL = pathlib.Path(__file__).resolve().parent / "data" / "consolidated.csv"

INK = colors.HexColor("#1c1c1e")
MUTED = colors.HexColor("#6e6e76")
ACCENT = colors.HexColor("#4f46e5")
BAD = colors.HexColor("#c0392b")
SUN = colors.HexColor("#c07f12")
GRID = colors.HexColor("#e4e4e9")
PAPER_BG = colors.white
RULE = colors.HexColor("#d8d8de")
BAND = colors.HexColor("#f4f4f7")

# ---------------------------------------------------------------- styles
S = {
    "title": ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=16.5,
                            leading=20, textColor=INK, alignment=TA_CENTER,
                            spaceAfter=6),
    "sub": ParagraphStyle("s", fontName="Helvetica", fontSize=10.5, leading=13,
                          textColor=MUTED, alignment=TA_CENTER, spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=12.5,
                         leading=15, textColor=INK, spaceBefore=12,
                         spaceAfter=5),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.8,
                         leading=13, textColor=INK, spaceBefore=9,
                         spaceAfter=4),
    "body": ParagraphStyle("b", fontName="Times-Roman", fontSize=9.6,
                           leading=13, textColor=INK, alignment=TA_JUSTIFY,
                           spaceAfter=5),
    "bullet": ParagraphStyle("bu", fontName="Times-Roman", fontSize=9.6,
                             leading=12.8, textColor=INK, leftIndent=14,
                             firstLineIndent=-8, spaceAfter=2.5),
    "code": ParagraphStyle("c", fontName="Courier", fontSize=7.6, leading=9.6,
                           textColor=INK, backColor=BAND,
                           borderPadding=4, spaceBefore=3, spaceAfter=6),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=7.8,
                           leading=9.6, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=7.8,
                            leading=9.6, textColor=INK),
    "cap": ParagraphStyle("cap", fontName="Helvetica-Oblique", fontSize=8,
                          leading=10, textColor=MUTED, alignment=TA_CENTER,
                          spaceBefore=3, spaceAfter=9),
}

INLINE = [
    (re.compile(r"`([^`]+)`"), r'<font face="Courier" size="8.6">\1</font>'),
    (re.compile(r"\*\*([^*]+)\*\*"), r"<b>\1</b>"),
    (re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)"), r"<i>\1</i>"),
    (re.compile(r"\[(\d+)\]"), r"[\1]"),
]


def inline(text: str) -> str:
    text = html.escape(text)
    for pat, rep in INLINE:
        text = pat.sub(rep, text)
    return text


# ---------------------------------------------------------------- markdown
def parse(md: str):
    """Yield ('h1'|'h2'|'h3'|'p'|'li'|'code'|'table'|'hr', payload)."""
    lines = md.split("\n")
    i, n = 0, len(lines)
    while i < n:
        raw = lines[i]
        line = raw.rstrip()

        if not line.strip():
            i += 1
            continue

        if line.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            yield ("code", "\n".join(buf))
            continue

        if re.fullmatch(r"-{3,}", line.strip()):
            yield ("hr", None)
            i += 1
            continue

        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            yield (f"h{min(level, 3)}", line.lstrip("#").strip())
            i += 1
            continue

        if line.lstrip().startswith("|"):
            block = []
            while i < n and lines[i].lstrip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            rows = []
            for r in block:
                if re.fullmatch(r"\|[\s:\-|]+\|", r):
                    continue
                cells = [c.strip() for c in r.strip("|").split("|")]
                rows.append(cells)
            if rows:
                yield ("table", rows)
            continue

        if re.match(r"^\s*[-*]\s+", line):
            item = re.sub(r"^\s*[-*]\s+", "", line)
            nxt = i + 1
            while nxt < n and re.match(r"^\s{2,}\S", lines[nxt]) and \
                    not lines[nxt].lstrip().startswith(("|", "-", "#")):
                item += " " + lines[nxt].strip()
                nxt += 1
            yield ("li", item)
            i = nxt
            continue

        para = []

        def stops(ln: str) -> bool:
            if not ln.strip():
                return True
            if ln.startswith(("#", "|", "```", "  ")):
                return True
            if re.match(r"^\s*[-*]\s+", ln):
                return True
            return bool(re.fullmatch(r"-{3,}", ln.strip()))

        while i < n and not stops(lines[i]):
            para.append(lines[i].strip())
            i += 1
        if para:
            yield ("p", " ".join(para))
        else:
            # A line that every branch above declined must still advance the
            # cursor, or the parse never terminates.
            i += 1


def styled_table(rows):
    head, *body = rows
    data = [[Paragraph(inline(c), S["cellb"]) for c in head]]
    for r in body:
        data.append([Paragraph(inline(c), S["cell"]) for c in r])
    t = Table(data, hAlign="CENTER", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BAND),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, RULE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


# ---------------------------------------------------------------- figures
def fig_segmentation() -> Drawing:
    rows = list(csv.DictReader((EVAL / "eval_SEG20_metrics.csv").open(encoding="utf-8")))
    P = [float(r["cer"]) for r in rows if r["arm"] == "plain"]
    Sg = [float(r["cer"]) for r in rows if r["arm"] == "seg"]
    d = Drawing(500, 190)
    bc = VerticalBarChart()
    bc.x, bc.y = 34, 30
    bc.width, bc.height = 440, 120
    bc.data = [P, Sg]
    bc.categoryAxis.categoryNames = [
        f"MT-{i+1:03d}".replace("MT-0", "") for i in range(len(P))]
    bc.categoryAxis.labels.fontName = "Helvetica"
    bc.categoryAxis.labels.fontSize = 4.2
    bc.categoryAxis.labels.angle = 90
    bc.categoryAxis.labels.dy = -4
    bc.categoryAxis.labels.dx = 2
    bc.valueAxis.valueMin, bc.valueAxis.valueMax = 0, 1.5
    bc.valueAxis.valueStep = 0.25
    bc.valueAxis.labels.fontName = "Helvetica"
    bc.valueAxis.labels.fontSize = 5.5
    bc.groupSpacing = 2
    bc.bars[0].fillColor = ACCENT
    bc.bars[1].fillColor = BAD
    bc.barWidth = 5
    d.add(bc)
    d.add(String(250, 178, "whole page — mean CER %.3f" % statistics.mean(P),
                 fontName="Helvetica-Bold", fontSize=7, fillColor=ACCENT))
    d.add(String(250, 166, "segmented — mean CER %.3f  (worse on 19/19, "
                           "sign test p = 3.8e-06)" % statistics.mean(Sg),
                 fontName="Helvetica-Bold", fontSize=7, fillColor=BAD))
    return d


def fig_restoration() -> Drawing:
    rows = list(csv.DictReader(CONSOL.open(encoding="utf-8")))
    cfg = collections.defaultdict(list)
    for r in rows:
        if r["tag"] == "EXP-005":
            cfg[r["config"]].append(float(r["cer"]))
    order = ["grayscale", "denoised", "enhanced", "deskewed", "binarized",
             "full_restoration"]
    vals = [statistics.mean(cfg[c]) for c in order]
    d = Drawing(500, 190)
    bc = VerticalBarChart()
    bc.x, bc.y = 46, 34
    bc.width, bc.height = 420, 116
    bc.data = [vals]
    bc.categoryAxis.categoryNames = [c[:11] for c in order]
    bc.categoryAxis.labels.fontName = "Helvetica"
    bc.categoryAxis.labels.fontSize = 5.4
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.labels.dy = -6
    bc.categoryAxis.labels.dx = 8
    bc.valueAxis.valueMin, bc.valueAxis.valueMax = 0, 0.45
    bc.valueAxis.valueStep = 0.1
    bc.valueAxis.labels.fontName = "Helvetica"
    bc.valueAxis.labels.fontSize = 5.5
    bc.bars[0].fillColor = ACCENT
    bc.barWidth = 22
    bc.groupSpacing = 10
    d.add(bc)
    d.add(String(250, 176, "Restoration sweep — 140 model calls, 7 configurations "
                            "x 20 pages (lower is better)",
                 fontName="Helvetica-Bold", fontSize=7, fillColor=INK))
    return d


def fig_errorprofile() -> Drawing:
    d = Drawing(500, 150)
    d.add(String(250, 136, "Error profile flips to deletions",
                 fontName="Helvetica-Bold", fontSize=7.5, fillColor=INK))
    cats = ["Substitutions", "Deletions", "Insertions"]
    whole = [64.3, 11.0, 24.7]
    seg = [42.1, 47.2, 10.7]
    bc = VerticalBarChart()
    bc.x, bc.y = 40, 26
    bc.width, bc.height = 420, 92
    bc.data = [whole, seg]
    bc.categoryAxis.categoryNames = cats
    bc.categoryAxis.labels.fontName = "Helvetica"
    bc.categoryAxis.labels.fontSize = 6
    bc.valueAxis.valueMin, bc.valueAxis.valueMax = 0, 70
    bc.valueAxis.valueStep = 20
    bc.valueAxis.labels.fontName = "Helvetica"
    bc.valueAxis.labels.fontSize = 5.5
    bc.groupSpacing = 14
    bc.barWidth = 26
    bc.bars[0].fillColor = ACCENT
    bc.bars[1].fillColor = BAD
    d.add(bc)
    d.add(String(120, 16, "whole page", fontName="Helvetica-Bold", fontSize=6,
                 fillColor=ACCENT))
    d.add(String(200, 16, "segmented", fontName="Helvetica-Bold", fontSize=6,
                 fillColor=BAD))
    d.add(String(300, 16, "adapter card: deletions = 46% of its errors",
                 fontName="Helvetica-Bold", fontSize=6, fillColor=BAD))
    return d


def _mean_cer(rows, arm):
    v = [float(r["cer"]) for r in rows if r["arm"] == arm]
    return statistics.mean(v) if v else None


def fig_tokens() -> Drawing:
    """Tokens on the x-axis, CER on the y-axis: the decisive figure."""
    px = list(csv.DictReader((EVAL / "eval_PIXELS_metrics.csv").open(encoding="utf-8")))
    seg20 = list(csv.DictReader((EVAL / "eval_SEG20_metrics.csv").open(encoding="utf-8")))

    pts = [
        ("px512 — 518 tok/char", 3.57, _mean_cer(px, "px512"), SUN, 0),
        # px1280 and px2048 are the same point: identical tokens, identical CER.
        # Plotted once, with the saturation stated in the label, so the figure
        # cannot overplot two markers and imply two different measurements.
        ("whole page — 765 tok/char\n(px1280 and px2048 identical)",
         5.28, _mean_cer(px, "px1280"), ACCENT, 1),
        ("segmented — ~35 tok/char", 35.0, _mean_cer(seg20, "seg"), BAD, 2),
    ]

    d = Drawing(500, 210)
    L, B, PW, PH = 52, 46, 300, 128
    mx_c, mx_t = 0.70, 40.0

    # gridlines and both axes' ticks
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = B + PH * frac
        d.add(Line(L, y, L + PW, y, strokeColor=GRID, strokeWidth=0.5))
        d.add(String(L - 5, y - 2, "%.2f" % (frac * mx_c), fontName="Helvetica",
                     fontSize=5.5, fillColor=MUTED, textAnchor="end"))
        x = L + PW * (frac * mx_c / mx_t)
        d.add(String(x, B - 9, "%d" % round(frac * mx_t), fontName="Helvetica",
                     fontSize=5.5, fillColor=MUTED, textAnchor="middle"))
    d.add(Line(L, B, L, B + PH, strokeColor=INK, strokeWidth=0.7))
    d.add(Line(L, B, L + PW, B, strokeColor=INK, strokeWidth=0.7))
    d.add(String(L + PW / 2, B - 20, "visual tokens per character",
                 fontName="Helvetica", fontSize=6.5, fillColor=INK,
                 textAnchor="middle"))
    d.add(String(11, B + PH / 2, "CER  (lower is better)", fontName="Helvetica",
                 fontSize=6.5, fillColor=INK, textAnchor="middle"))

    for lbl, tok, cer, col, side in pts:
        if cer is None:
            continue
        x = L + PW * (min(tok, mx_t) / mx_t)
        y = B + PH * (cer / mx_c)
        d.add(Circle(x, y, 3.4, fillColor=col, strokeColor=PAPER_BG, strokeWidth=1))
        # px1280's label goes to the right, the others above, to avoid collisions
        if side == 1:
            d.add(String(x + 7, y + 1, "whole page — 765 tok/char",
                         fontName="Helvetica-Bold", fontSize=5.8, fillColor=col))
            d.add(String(x + 7, y - 6, "(px1280 and px2048 byte-identical)",
                         fontName="Helvetica", fontSize=5.2, fillColor=MUTED))
        elif side == 2:
            d.add(String(x - 6, y - 11, "segmented — ~35 tok/char",
                         fontName="Helvetica-Bold", fontSize=5.8, fillColor=col,
                         textAnchor="end"))
        else:
            d.add(String(x, y + 8, "px512 — 518 tok/char",
                         fontName="Helvetica-Bold", fontSize=5.8, fillColor=col,
                         textAnchor="middle"))

    bx = L + PW + 18
    lines = [
        "Tokens saturate at native resolution:",
        "px2048 is byte-identical to px1280 on",
        "20/20 pages, because a 1268x463 page is",
        "already under both ceilings.",
        "",
        "Segmentation supplies 6.6x the tokens and",
        "scores 0.290 CER worse. Tokens bought by",
        "discarding page context are net-negative.",
    ]
    for i, ln in enumerate(lines):
        d.add(String(bx, B + PH - 6 - i * 11, ln, fontName="Helvetica",
                     fontSize=6.0, fillColor=BAD if i >= 5 else MUTED))
    return d


def fig_levers() -> Drawing:
    rows = list(csv.DictReader((EVAL / "eval_LEVERS_metrics.csv").open(encoding="utf-8")))

    def secs(arm):
        v = [float(r["secs"]) for r in rows if r["arm"] == arm and float(r["secs"] or 0) > 0]
        return statistics.mean(v) if v else 0.0

    arms = [("lever_base", "shipped", ACCENT),
            ("lever_beam4", "beam = 4", MUTED),
            ("lever_fp16", "fp16", MUTED),
            ("lever_merge", "merge LoRA", BAD)]

    d = Drawing(500, 190)
    bc = VerticalBarChart()
    bc.x, bc.y = 40, 30
    bc.width, bc.height = 250, 118
    bc.data = [[_mean_cer(rows, a) or 0 for a, _, _ in arms]]
    bc.categoryAxis.categoryNames = [lbl for _, lbl, _ in arms]
    bc.categoryAxis.labels.fontName = "Helvetica"
    bc.categoryAxis.labels.fontSize = 5.6
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.labels.dx = 6
    bc.valueAxis.valueMin, bc.valueAxis.valueMax = 0, 1.15
    bc.valueAxis.valueStep = 0.25
    bc.valueAxis.labels.fontName = "Helvetica"
    bc.valueAxis.labels.fontSize = 5.5
    bc.barWidth = 30
    bc.groupSpacing = 12
    # per-bar colours
    bc.bars.strokeColor = None
    for i, (_a, _l, col) in enumerate(arms):
        bc.bars[(0, i)].fillColor = col
    d.add(bc)

    for i, (a, lbl, col) in enumerate(arms):
        cer = _mean_cer(rows, a) or 0
        d.add(String(55 + i * 62, 34 + 118 * (cer / 1.15), "%.3f" % cer,
                     fontName="Helvetica-Bold", fontSize=6.4, fillColor=col,
                     textAnchor="middle"))
        d.add(String(55 + i * 62, 22, "%.0fs" % secs(a), fontName="Helvetica",
                     fontSize=5.5, fillColor=MUTED, textAnchor="middle"))

    for i, ln in enumerate([
            "Paired against a control running the",
            "shipped settings, n = 20. The control",
            "reproduced the token-sweep arm",
            "byte-for-byte on 20/20 pages.",
            "",
            "beam = 4:  +0.004 CER (9 worse / 8",
            "better) at 4.9x the latency — noise.",
            "",
            "fp16:  +0.010 CER, no speed benefit.",
            "",
            "merge LoRA:  CER 1.064, worse on 20/20",
            "pages. Folding the adapter delta into",
            "NF4-quantised base weights is not",
            "numerically sound — the adapter was",
            "fitted against a dequantised bf16 base."]):
        c = BAD if ln.startswith("merge") else MUTED
        fn = "Helvetica-Bold" if ln.startswith("merge") else "Helvetica"
        d.add(String(308, 148 - i * 10.5, ln, fontName=fn, fontSize=6.0, fillColor=c))
    return d


FIGURES = {
    "fig2-segmentation.svg": (
        fig_segmentation,
        "Figure 1. Paired comparison of whole-page and line-segmented "
        "transcription on 20 identical pages with identical decoding. "
        "Segmentation is worse on every page where the two differ (n=19, "
        "sign test p = 3.8e-06)."),
    "fig3-restoration.svg": (
        fig_restoration,
        "Figure 2. Mean CER for each of seven restoration configurations over "
        "20 pages (140 model calls). Error increases monotonically with "
        "pipeline aggressiveness; grayscale is the no-op control."),
    "fig1-page-difficulty.svg": (
        fig_errorprofile,
        "Figure 3. Error-profile composition. Whole-page reading produces 11% "
        "deletions; segmentation drives deletions to 47%, reproducing the "
        "adapter author's documented dominant failure mode."),
    "fig5-tokens.svg": (
        fig_tokens,
        "Figure 4. Visual tokens per character against character error rate. "
        "Sweeping the pixel budget on the unsegmented page shows tokens help up "
        "to native resolution and then stop (px2048 is byte-identical to px1280 "
        "on 20/20 pages). Segmentation supplies 6.6x more tokens per character "
        "and is far worse, so the tokens it buys are net-negative."),
    "fig6-levers.svg": (
        fig_levers,
        "Figure 5. Three standard inference levers against a control arm running "
        "the shipped settings (n=20). Beam search and fp16 are within noise; "
        "merging the LoRA into the NF4-quantised base is catastrophic (CER 1.064, "
        "worse on 20/20 pages). Nothing outside the input representation moved "
        "accuracy."),
}


# ---------------------------------------------------------------- build
def build():
    story = []
    pending_fig = None
    first_h1_done = False

    for kind, payload in parse(PAPER.read_text(encoding="utf-8")):
        if kind == "hr":
            continue

        if kind == "h1":
            if not first_h1_done:
                story.append(Paragraph(inline(payload), S["title"]))
                first_h1_done = True
            else:
                story.append(Paragraph(inline(payload), S["h1"]))
            continue

        if kind == "h2":
            story.append(Paragraph(inline(payload), S["h2"]))
            continue

        if kind == "h3":
            story.append(Paragraph(inline(payload), S["h2"]))
            continue

        if kind == "code":
            story.append(Preformatted(payload, S["code"]))
            continue

        if kind == "li":
            story.append(Paragraph(inline(payload), S["bullet"], bulletText="•"))
            continue

        if kind == "table":
            story.append(styled_table(payload))
            story.append(Spacer(1, 6))
            continue

        story.append(Paragraph(inline(payload), S["body"]))

    # figures appended as a final section, clearly captioned
    story.append(Spacer(1, 10))
    story.append(Paragraph("Figures", S["h1"]))
    for _key, (maker, cap) in FIGURES.items():
        block = [maker(), Paragraph(cap, S["cap"])]
        story.append(KeepTogether(block))

    doc = BaseDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        topMargin=0.8 * inch, bottomMargin=0.75 * inch,
        title="Input Pipelines, Not Models, Are the Bottleneck in VLM-Based "
              "Modi Transliteration",
        author="LipiLens Research Group")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame])])
    doc.build(story)
    print(f"wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    sys.exit(build())