#!/usr/bin/env python
"""Build the LipiLens IEEE conference paper PDF (reportlab, no LaTeX needed).

Usage:  python research/build_paper.py
Output: research/lipilens_paper.pdf  (IEEE two-column, letter, Times)

CONTENT RULE: every number below comes from experiments/results/*.csv/json.
Every citation was verified (model/dataset pages fetched 2026-09-17).
Nothing is invented. If you re-run experiments, update the constants in
Section "MEASURED RESULTS" and rebuild.

TODO FOR THE AUTHORS: replace placeholder co-author/faculty names.
"""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (BaseDocTemplate, Frame, Image, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "research" / "lipilens_paper.pdf"

# ---------------------------------------------------------------- MEASURED
N_BASE = 50
BASE_CER, BASE_WER = 0.304, 0.645
BASE_MIN, BASE_MAX = 0.026, 0.912
SWEEP = [  # (condition, n, mean CER, WER, W/T/L vs original)
    ("original", 20, 0.317, 0.688, "—"),
    ("grayscale", 20, 0.317, 0.688, "0/20/0"),
    ("denoised", 20, 0.321, 0.692, "8/1/11"),
    ("enhanced", 20, 0.328, 0.686, "5/5/10"),
    ("binarized", 20, 0.355, 0.723, "3/0/17"),
    ("deskewed", 20, 0.332, 0.699, "3/9/8"),
    ("full restoration", 20, 0.359, 0.728, "5/1/14"),
]
CARD_CER, CARD_ZERO = 0.328, 0.930  # adapter author's self-reported numbers

PAGE_W, PAGE_H = letter
M_L = M_R = 0.60 * inch
M_T, M_B = 0.55 * inch, 0.70 * inch
GAP = 0.25 * inch
COL_W = (PAGE_W - M_L - M_R - GAP) / 2
TITLE_H = 3.05 * inch

S = {
    "title": ParagraphStyle("title", fontName="Times-Bold", fontSize=22,
                            leading=26, alignment=1, spaceAfter=10),
    "authors": ParagraphStyle("authors", fontName="Times-Roman", fontSize=10,
                              leading=13, alignment=1, spaceAfter=2),
    "affil": ParagraphStyle("affil", fontName="Times-Italic", fontSize=9,
                            leading=11, alignment=1, spaceAfter=10),
    "abs": ParagraphStyle("abs", fontName="Times-Italic", fontSize=9,
                          leading=11, alignment=4, spaceAfter=4,
                          borderPadding=(0, 0, 6)),
    "kw": ParagraphStyle("kw", fontName="Times-Italic", fontSize=9,
                         leading=11, alignment=4, spaceAfter=0),
    "h1": ParagraphStyle("h1", fontName="Times-Bold", fontSize=10,
                         leading=12, alignment=1, spaceBefore=8,
                         spaceAfter=4),
    "body": ParagraphStyle("body", fontName="Times-Roman", fontSize=10,
                           leading=12, alignment=4, firstLineIndent=14,
                           spaceAfter=2),
    "body0": ParagraphStyle("body0"),
    "cap": ParagraphStyle("cap", fontName="Times-Roman", fontSize=8,
                          leading=10, alignment=1, spaceBefore=2,
                          spaceAfter=8),
    "cell": ParagraphStyle("cell", fontName="Times-Roman", fontSize=7.5,
                           leading=9, alignment=1),
    "cellh": ParagraphStyle("cellh", fontName="Times-Bold", fontSize=7.5,
                            leading=9, alignment=1),
    "ref": ParagraphStyle("ref", fontName="Times-Roman", fontSize=8,
                          leading=10, alignment=0, leftIndent=12,
                          firstLineIndent=-12, spaceAfter=2),
}
S["body0"].fontName = "Times-Roman"
S["body0"].fontSize = 10
S["body0"].leading = 12
S["body0"].alignment = 4
S["body0"].firstLineIndent = 0
S["body0"].spaceAfter = 2

def H(num, title):
    return Paragraph(f"{num}.&nbsp;&nbsp;{title.upper()}", S["h1"])


def P(t, first=True):
    return Paragraph(t, S["body"] if first else S["body0"])


def fig(path, caption, width=COL_W):
    iw, ih = ImageReader(str(path)).getSize()
    h = width * ih / iw
    return [Image(str(path), width=width, height=h),
            Paragraph(caption, S["cap"])]


def table(headers, rows, widths):
    data = [[Paragraph(h, S["cellh"]) for h in headers]]
    data += [[Paragraph(c, S["cell"]) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, "black"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def build():
    story = []
    A = story.append

    A(Paragraph("Does Image Restoration Help Vision-Language Transcription "
                "of Historical Modi Manuscripts? A Small-Scale Empirical "
                "Study with LipiLens", S["title"]))
    A(Paragraph("Chirayu Khot, <i>Second Author</i>, <i>Third Author</i>, "
                "<i>Fourth Author</i>, <i>Faculty Advisor</i>", S["authors"]))
    A(Paragraph("Department of Computer Engineering, Kolhapur Institute of "
                "Technology, Kolhapur, Maharashtra, India", S["affil"]))
    A(Paragraph("<b><i>Abstract</i></b>—Modi script manuscripts are largely "
                "inaccessible to modern readers and lack mature OCR. We present "
                "LipiLens, an AI-assisted pipeline (OpenCV restoration + "
                "Qwen2.5-VL-3B with a Modi-specific LoRA adapter + mandatory "
                "human verification), and use it to test whether classical "
                "image restoration helps vision-language transcription. On 50 "
                "real manuscript pages with expert Devanagari ground truth, "
                "the baseline character error rate (CER) is 0.304 (range "
                "0.026–0.912). Across a 140-call sweep over seven preprocessing "
                "conditions, grayscale conversion is a perfect no-op, "
                "denoising, contrast enhancement and deskewing are neutral "
                "within noise, binarization clearly degrades accuracy (17 of "
                "20 pages worse, +0.038 mean CER), and the full restoration "
                "pipeline performs worst overall (0.359). On clean historical "
                "pages, the safest input to the model is the original image.",
                S["abs"]))
    A(Paragraph("<b><i>Index Terms</i></b>—<i>Modi script, document image "
                "restoration, vision-language models, LoRA, optical character "
                "recognition, digital preservation.</i>", S["kw"]))

    A(H("I", "Introduction"))
    A(P("Modi was the administrative script of Maharashtra from roughly the "
        "13th century until it was phased out in favor of Devanagari in the "
        "mid-20th century. An estimated tens of millions of documents—land "
        "records, correspondence, court papers—survive only in Modi, while the "
        "number of fluent readers shrinks. Physical manuscripts are degraded "
        "by faded ink, staining, skew and uneven photography, and no mature "
        "commodity OCR exists for the script."))
    A(P("General-purpose vision-language models (VLMs), specialized with "
        "low-rank adapters (LoRA), now offer draft transliteration of such "
        "low-resource scripts, but always require expert review: a fluent, "
        "confident model output can be entirely wrong. A second open question "
        "is whether classical restoration (denoising, contrast enhancement, "
        "binarization, deskewing) helps or hurts a VLM trained on "
        "natural-looking images. More preprocessing is not obviously better.",
        first=False))
    A(P("This paper contributes: (1) <b>LipiLens</b>, a working end-to-end "
        "pipeline—upload, restore, transcribe, verify, archive, search—with "
        "structural separation of AI draft and human-verified text; and "
        "(2) a small, fully reproducible empirical study (50 pages, 140 "
        "inference calls) of restoration effects on transcription accuracy, "
        "reported with failures and limitations intact.", first=False))

    A(H("II", "Background and Related Work"))
    A(P("The MoDeTrans dataset [1] provides 2,043 Modi document images with "
        "expert Devanagari transliterations across the Shivakalin, Peshwekalin "
        "and Anglakalin eras, plus a synthetic companion set (SynthMoDe); the "
        "authors also propose MoScNet, a knowledge-distillation VLM framework. "
        "Our transcription adapter [2] is a QLoRA fine-tune (rank 32, "
        "1.94% trainable parameters) of Qwen2.5-VL-3B-Instruct [4] on 5,721 "
        "real plus synthetic images. Its author reports test CER 0.328 "
        f"against a 0.930 zero-shot baseline on 204 held-out real pages. We "
        "use 50 training-split rows of [3] with their shipped transliterations "
        "as ground truth."))
    A(P("Classical OCR practice applies denoising, contrast enhancement and "
        "binarization before recognition; whether these steps transfer to "
        "VLM transliteration of historical scripts has, to our knowledge, not "
        "been measured for this model and script combination.", first=False))

    A(H("III", "The LipiLens System"))
    A(P("A React frontend (Transcribe/Library/About) talks to a FastAPI "
        "backend over HTTP. Restoration is a modular OpenCV pipeline driven "
        "by named configs (Table I); inference sits behind one "
        "<i>transcribe(image, prompt)</i> interface served locally or from a "
        "Colab GPU endpoint; persistence is SQLite (manuscripts, "
        "transcriptions, preprocessing configs). The schema makes "
        "AI-authoritative use structurally impossible: <i>ai_transcription</i> "
        "is immutable once written and verification writes only "
        "<i>verified_transcription</i>."))
    A(table(["Config", "Stages"],
            [["original", "none (control)"],
             ["grayscale", "grayscale"],
             ["denoised", "+ non-local-means (h=10)"],
             ["enhanced", "+ CLAHE (2.0, 8×8)"],
             ["binarized", "+ Otsu threshold"],
             ["deskewed", "grayscale + Hough deskew"],
             ["full restoration", "all + border cleanup"]],
            [1.55 * inch, 1.75 * inch]))
    A(Paragraph("TABLE I. Preprocessing conditions (cumulative).", S["cap"]))

    A(H("IV", "Experimental Setup"))
    A(P("Data: 50 MoDeTrans training-split rows (filenames 1.jpg–1042.jpg "
        "range), reference lengths 60–205 characters, MIT-licensed; one "
        "additional unprovenanced character chart used only for smoke-testing. "
        "Model: Qwen2.5-VL-3B-Instruct at pinned revision <i>6628554</i> plus "
        "adapter [2] at <i>5b9957d</i>, 4-bit NF4, served from Colab GPU "
        "(type unrecorded). Prompt (from the adapter's official recipe): "
        "\u201cTransliterate the text in this image into Devanagari script. "
        "Output only the Devanagari text, with no explanation.\u201d "
        "Generation: max 256 new tokens, greedy. Metrics: CER and WER via "
        "Levenshtein distance against the shipped references. Controls: "
        "identical model, prompt and decoding across conditions; only the "
        "input variant changes."))
    A(P("Threats: the 50 pages come from the adapter's own training split, so "
        "scores may be optimistic; n=50 supports description, not significance "
        "testing; pages are relatively clean, short, single-hand excerpts.",
        first=False))

    A(H("V", "Results"))
    A(P(f"Baseline (original images, n={N_BASE}): mean CER {BASE_CER} "
        f"(std 0.15, range {BASE_MIN}–{BASE_MAX}), mean WER {BASE_WER}. Best "
        "page MT-048 reaches 0.026; worst MT-038 reaches 0.912. "
        "Substitutions dominate every error profile. Table II and Fig. 1 give "
        "the sweep outcome (140 calls)."))
    A(table(["Condition", "n", "CER", "WER", "W/T/L"],
            [[c, str(n), f"{ce:.3f}", f"{w:.3f}", x]
             for c, n, ce, w, x in SWEEP],
            [1.15 * inch, 0.35 * inch, 0.55 * inch, 0.55 * inch, 0.70 * inch]))
    A(Paragraph("TABLE II. Sweep results (descriptive; W/T/L = pages better / "
                "tied / worse than original at ±0.005 CER).", S["cap"]))
    story += fig(ROOT / "docs" / "sweep_means.png",
                 "Fig. 1. Mean CER/WER per condition (±std). Binarization and "
                 "the full pipeline sit clearly above baseline.")
    A(P("Three findings stand out. First, grayscale conversion ties the "
        "original on all 20 pages to four decimals—a built-in control proving "
        "measurement stability. Second, Otsu binarization degrades 17 of 20 "
        "pages (+0.038 mean CER); Fig. 2 shows why: thresholding visibly "
        "erodes thin strokes, headline rules and joints that the model "
        "evidently uses. Third, stacking neutral stages compounds into harm: "
        "the full pipeline is worst overall (0.359, 14/20 losses), damaging "
        "the cleanest page most (MT-002: 0.099 → 0.242). Denoising, "
        "enhancement and deskewing sit within noise of baseline, with the "
        "largest gains clustering on the highest-baseline pages (e.g., "
        "denoised MT-011: 0.550 → 0.420). A fluent-but-wrong hallucination on "
        "MT-003 (CER 0.567) further justifies mandatory verification.",
        first=False))
    story += fig(ROOT / "experiments" / "results" / "qualitative" /
                 "fig_mt002_conditions.png",
                 "Fig. 2. MT-002 under original / binarized / full "
                 "restoration. Stroke erosion is visible, not just numeric.")

    A(H("VI", "Discussion"))
    A(P("H1 (restoration helps) is rejected on these pages; H3 (aggressive "
        "processing can hurt, especially binarization) is supported; H2 "
        "(effects grow with degradation) gets weak directional support only, "
        "since degraded pairs were not tested. The product consequence is "
        "immediate: LipiLens defaults to the original image and offers "
        "restoration as an option, never the default."))

    A(H("VII", "Limitations"))
    A(P("Training-split overlap (optimistic bias); n=50, descriptive only; "
        "clean short pages—nothing here covers heavily degraded manuscripts; "
        "single prompt and decoding setting; Colab GPU type and VRAM "
        "unrecorded; local 4-GB-VRAM inference undemonstrated; ground truth "
        "taken on trust from [3]."))

    A(H("VIII", "Conclusion"))
    A(P("LipiLens works end-to-end and its embedded study answers the "
        "research question for clean Modi pages: send the original to the "
        "model, keep the human in the loop, and distrust preprocessing that "
        "destroys gray-level stroke detail. All data, code and logs are "
        "available for reproduction."))

    A(P("<i>Acknowledgment—We thank the MoDeTrans authors and the adapter "
        "author for open data and weights.</i>", first=False))

    A(H("References", ""))
    refs = [
        "H. Kausadikar, T. Kale, O. Susladkar, and S. Mittal, “Historic "
        "scripts to modern vision: a novel dataset and a VLM framework for "
        "transliteration of Modi script to Devanagari,” arXiv:2503.13060, "
        "2025 (accepted at ICDAR 2025).",
        "S. Godse (lgtk), “qwen25vl-3b-modi-synth-lora,” Hugging Face model "
        "hub, 2025. [Online]. Available: https://huggingface.co/lgtk/"
        "qwen25vl-3b-modi-synth-lora",
        "historyHulk, “MoDeTrans,” Hugging Face datasets, MIT license, 2025. "
        "[Online]. Available: https://huggingface.co/datasets/historyHulk/"
        "MoDeTrans",
        "Qwen Team, “Qwen2.5-VL-3B-Instruct,” Hugging Face model hub, 2025. "
        "[Online]. Available: https://huggingface.co/Qwen/"
        "Qwen2.5-VL-3B-Instruct",
    ]
    for i, r in enumerate(refs, 1):
        A(Paragraph(f"[{i}]&nbsp;&nbsp;{r}", S["ref"]))

    doc = BaseDocTemplate(str(OUT), pagesize=letter, leftMargin=M_L,
                          rightMargin=M_R, topMargin=M_T, bottomMargin=M_B,
                          title="LipiLens Modi Transcription Study",
                          author="Chirayu Khot et al.")
    tw, th = PAGE_W - M_L - M_R, PAGE_H - M_T - M_B
    ty = M_B + th - TITLE_H
    ch = th - TITLE_H - 0.12 * inch
    first = PageTemplate("first", frames=[
        Frame(M_L, ty, tw, TITLE_H, id="title"),
        Frame(M_L, M_B, COL_W, ch, id="c1"),
        Frame(M_L + COL_W + GAP, M_B, COL_W, ch, id="c2")])
    later = PageTemplate("later", frames=[
        Frame(M_L, M_B, COL_W, th, id="c1"),
        Frame(M_L + COL_W + GAP, M_B, COL_W, th, id="c2")])
    doc.addPageTemplates([first, later])

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Times-Roman", 8)
        canvas.drawCentredString(PAGE_W / 2, 0.45 * inch, str(canvas.getPageNumber()))
        canvas.restoreState()

    first.onPage = footer
    later.onPage = footer
    doc.build(story)
    print("wrote", OUT, f"({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    build()
