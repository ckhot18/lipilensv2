# LipiLens — Team Working Document

**This is the source document.** Build reports and slides from the sections
here; do not rewrite the facts. Every number has a source, and every claim has
a guardrail.

Status: working, measured, honestly documented
Date: 2026-10-08 · `main` @ `8944f49` · 93 tests passing · 90 model calls logged

Deck outline and speaker notes: **[PRESENTATION.md](PRESENTATION.md)**

---

# PART 1 — THE FACTS SHEET

> **Rule: quote from this table only.** If it is not here, measure it first
> with `scripts/evaluate_local.py`. Do not carry a number from memory.

## 1.1 Headline numbers

| Claim | Value | Source |
|---|---|---|
| Character accuracy, clean scans | **63.7%** (CER 0.363) | `eval_EVAL-01_metrics.csv`, 10 pages |
| Character accuracy, degraded captures | **65.2%** (CER 0.348) | `eval_DEG-MED_metrics.csv`, **23 pages** |
| Best degraded-input config (`denoised`) | 66.6% (CER 0.334) | n=23, sign test p=0.68 — **not significant** |
| Adapter's published mean, 204 held-out pages | 67.2% (CER 0.328) | adapter model card |
| Share of adapter examples below CER 0.20 | 21% | adapter model card |
| Share in the 0.20–0.40 "fair" band | 53% | adapter model card |
| Measurement noise, 10-page runs | **±0.05 CER** | `plain` vs historical baseline, 10 pages |
| Time per page | ~55–120 s | `eval_*_metrics.csv` |
| First-page extra cost (model load) | ~85 s | live runs |
| Hardware | RTX 2050, **4 GB VRAM** | `nvidia-smi` |
| VRAM in use during inference | ~3.9 GB of 4 GB | `nvidia-smi` |
| Adapter's recommended VRAM | ≥6 GB (developed on 8.5 GB) | adapter model card |
| Tests | 99 passing | `pytest tests/ -q` |

> **Retracted.** This brief previously reported *"`enhanced` on degraded input:
> 62.4% (CER 0.376), small gain"* from a 10-page run. Replicated at **n=23**,
> `enhanced` scores **49.6% (CER 0.504)** — the worst configuration tested. The
> 10-page number was page selection, not configuration. See §1.4.

## 1.2 Configuration results

| Configuration | CER | Accuracy | Verdict |
|---|---|---|---|
| **Whole page + `original`** | **0.363** | **63.7%** | **shipped** |
| + repetition guard + 512 tokens | 0.363 | 63.7% | no measurable effect |
| `enhanced` on clean input | 0.367 | 63.3% | negligible loss |
| `original` on degraded input (n=23) | 0.348 | 65.2% | baseline |
| `denoised` on degraded input (n=23) | 0.334 | 66.6% | +1.4 pts, **p=0.68, not significant** |
| **`enhanced` on degraded input (n=23)** | **0.504** | **49.6%** | **harms badly** |
| `binarized`, any input | 0.355–0.440 | 56.0–60.0% | **loses everywhere** |
| 1.5× pre-upscale | 0.417 | 58.3% | **worse** |
| Line segmentation | 0.606 | 39.4% | **much worse — now off** (n=20 paired; the n=10 `EVAL-01` run gave 0.623/37.7%, which is what `chart-clean-arms.svg` plots — both runs agree on direction and magnitude) |
| Beam search (4 beams) | 0.320 | 68.0% | noise, at **4.9× the latency** |
| fp16 compute | 0.326 | 67.4% | noise, no speed gain |
| LoRA merge | **1.064** | **−6.4%** | **destroys the model — never enable** |

## 1.3 Token budget, measured (`PIXELS`, n=20)

| Budget | Visual tokens/char | CER | Accuracy |
|---|---|---|---|
| 512 × 28² | 3.57 | 0.344 | 65.6% |
| 1280 × 28² (shipped) | 5.28 | **0.316** | **68.4%** |
| 2048 × 28² | 5.28 | 0.316 | 68.4% |

`max_pixels` is a **ceiling, not a target**. The 2048 arm is byte-identical to
1280 on 20/20 pages because the page is already under both. Line segmentation
supplies ~6.6× more tokens per character and scores **0.290 CER worse** — the
tokens it buys are more than cancelled by the page context it discards.
**Keep `SEGMENT_LINES=0`.**

## 1.4 Three facts to have ready cold

1. **The accuracy regression.** Line segmentation was introduced as "the
   accuracy fix". Measured, it cost **0.363 → 0.623**. It is now off by default.
2. **Two of our own predictions were wrong.** The 1.5× upscale (rated
   highest-value) measured worse. The repetition guard changed nothing.
3. **The product thesis did not survive its own replication.** At n=10 a
   degraded capture looked ~2 points better after cleaning. At n=23 it is
   15.6 points *worse*, and nothing beat the untouched image. Cleaning is not a
   small win; on this adapter it is a loss.

---

# PART 2 — CLAIM GUARDRAILS

> **This is the section that protects the team.** We removed a flagship claim
> because measurement disproved it. Do not put a new one in without evidence.

## 2.1 Say this / not that

| ✅ Say | ❌ Never say | Why |
|---|---|---|
| "63.7% character accuracy, measured on 10 pages against expert references" | "90% accurate" | Never measured. Model ceiling is ~0.33 CER. |
| "Segmentation measured 0.363 → 0.623, so we turned it off" | "Segmentation improves accuracy by giving the model more tokens per character" | **Disproven by our own experiment.** It gives 6.6× the tokens and is far worse. |
| "No configuration beat the untouched capture on damaged input (n=23, all p>0.13)" | "Preprocessing helps on dirty scans (+2.3)" | **Our own n=10 claim. Reversed at n=23.** |
| "The adapter's published mean is 0.328; we reach 0.363 on our sample" | "We outperform the adapter" | Different sample, within noise. |
| "A reviewer corrects about one character in three" | "The system produces accurate transcriptions" | It produces a *draft*. |
| "Differences under ±0.05 CER are noise" | "Preprocessing improved accuracy by 0.004" | Below noise floor. |
| "Our degraded set simulates photographic damage on authentic text" | "We tested on real damaged manuscripts" | It is simulated, not photographed. |
| "Measured on a 4 GB consumer GPU, below the adapter's 6 GB recommendation" | *(omit the hardware context)* | Omitting it invites an unanswerable expectation. |

## 2.2 If asked "what's your accuracy?"

> "**63.7% character accuracy**, measured on 10 MoDeTrans pages scored against
> authentic expert references — that's CER 0.363. For calibration, the LoRA
> adapter we build on reports CER 0.328 on its own 204-page held-out set, so
> we're within noise of the published baseline on a much smaller GPU. At that
> accuracy a human reviewer corrects roughly one character in three, which is
> why the product is built around verification rather than automation."

Never lead with a percentage and stop there. Always give the comparison and the
design implication.

## 2.3 If asked "why can't you reach 90%?"

> "Three reasons, in order. First, capacity: the adapter's own published
> distribution has 53% of pages in the 0.20–0.40 CER band and only 21% below
> 0.20. Holding 0.10 as an average means beating its authors' held-out set.
> Second, hardware: it was developed on 8.5 GB and recommends ≥6 GB; we're on
> 4 GB and measure 3.9 GB in use. Third, and most importantly, we tested it —
> segmentation and upscaling, the two obvious levers, both made things worse."

## 2.4 If asked "isn't 63% useless?"

> "For automated indexing, yes. That's not the product. Modi documents hold
> property, tax and court records that are currently unreadable to search. At
> 63.7% a reviewer fixes roughly a third of characters — which converts an
> unreadable page into a searchable one, and preserves the reviewer's edit
> permanently. The verification panel exists for exactly this, and the AI draft
> is never overwritten."

---

# PART 3 — THE NARRATIVE

Use this for the "what did you actually do" section of any report.

## 3.1 The problem we were handed

The app appeared to do nothing. A page uploaded, the button changed state, then
minutes of silence before an error — no progress, no result. The team assumed
the model was broken.

## 3.2 What we found instead

The model was never broken. Proven before any code changed: a direct API call
returned HTTP 200 in 106 seconds with real Devanagari.

Two independent bugs:

1. **A 120-second client abort.** The frontend applied one timeout to every
   request. A page takes ~85 s to load the model plus ~25 s per line, so the
   browser gave up while the server was still working. Restoration — a ~184 ms
   CPU operation — always looked fine, which is why only the AI step failed.
2. **Silently discarded clicks.** The re-entrancy latch was seeded from the
   "auto file" prop, so every run started from the Home page returned before
   issuing any request. No upload, no error, no recovery.

Fixing those exposed a third, deeper problem: when the results *did* appear,
they were wrong.

## 3.3 The accuracy investigation

We built `scripts/evaluate_local.py` because 8 of the 18 local transcriptions in
the archive had **no ground truth and could not be scored at all**. An unscored
run is not a result. The harness runs the real pipeline — restoration included —
against expert references, keeps every hypothesis, and re-scores without a GPU.

That immediately produced the finding that changed the project: **line
segmentation, the feature the README called "the accuracy fix", was costing 26
points of accuracy.** Its band detector cut ascenders and matras off every line
and fed the model fragments at 23:1–40:1 aspect ratios. We repaired the geometry
— full-line padding, aspect clamp, config-driven pixel budget — and re-measured
0.623. Segmentation is simply the wrong strategy here. It is now off by default.

## 3.4 Restoring the product premise

The intended product is *dirty scan in, clean text out*. But every corpus page
we had was already deskewed and contrast-normalised, so the restoration pipeline
had no job — only ink to destroy.

We generated a degradation ladder (`make_realistic.py`) that re-photographs
authentic pages with authentic ground truth, and re-ran the comparison. At n=10
preprocessing looked worth ~2 points on damaged input. **At n=23 that reversed**:
`enhanced` became the worst configuration tested (49.6% vs 65.2% for the
untouched capture) and no configuration differed significantly from doing
nothing. We retracted the claim. The interesting part is not that we were wrong
but *how* — the same ten pages still favour `enhanced` (−0.023), so the
reversal lives entirely in the thirteen pages the larger run added. That is the
same page-selection artefact we had already documented for our own first n=10
segmentation ablation, applied to a claim we had not yet re-tested.

## 3.5 What we shipped

- Transcription runs as a background job: `POST` returns 202 immediately, the UI
  polls progress once a second, and the archive row is written exactly once.
- Defaults set by measurement: whole page, `original`, segmentation off.
- 93 tests, including 23 covering the job and progress contract.

---

# PART 4 — EVIDENCE INDEX

| Claim type | Where to look |
|---|---|
| Per-page CER/WER + substitution/deletion split | `experiments/results/eval/eval_EVAL-01_metrics.csv`, `eval_DEG-MED_metrics.csv` |
| Raw model output, every run | `experiments/results/eval/*_hyp.txt` (90 files) |
| Reproduce any number, no GPU | `scripts/evaluate_local.py --report ...` |
| Generate the charts | `scripts/make_team_brief_charts.py` |
| Screenshots of the running app | `docs/team_brief/*.png` |
| Job/progress behaviour | `tests/test_transcription_jobs.py` (23 tests) |
| Segmentation geometry | `tests/test_segmentation.py` |
| Historic experiments EXP-002/004/005 | `experiments/results/baseline_n20_metrics.csv` — **historical record, superseded on defaults** |

**Regenerate everything before a presentation:**

```bash
python scripts/evaluate_local.py --report --configs original denoised enhanced \
    --images data/raw/realistic_medium --tag DEG-MED
python scripts/make_team_brief_charts.py
```

## 4.1 Asset gallery

Every image here was captured from the running application by driving it with a
real file through the DevTools Protocol. Charts regenerate from the CSVs.

| Asset | What it shows | Use it for |
|---|---|---|
| ![Home](01-home.png) `01-home.png` | Landing page, six real demo samples | Intro slide |
| ![Empty](02-transcribe-empty.png) `02-transcribe-empty.png` | Empty dropzone | The bug narrative |
| ![Loaded](03-transcribe-loaded.png) `03-transcribe-loaded.png` | Dirty scan loaded, restoration preview at **184 ms** | Explains the two-act split |
| ![Progress](04-progress-reading.png) `04-progress-reading.png` | **Live transcription mid-flight**, "Reading the page as one block" | Demo fallback; the progress fix |
| ![Result](05-result.png) `05-result.png` | Real **54.3 s** run with Devanagari draft | The product slide |
| ![Library](06-library.png) `06-library.png` | The real archive, searchable | Archive / retrieval |
| ![Clean arms](chart-clean-arms.svg) `chart-clean-arms.svg` | CER by configuration, clean pages | The negative-findings slide |
| ![Degraded](chart-degraded.svg) `chart-degraded.svg` | CER by configuration, degraded pages | The preprocessing slide |
| ![Clean vs dirty](chart-clean-vs-dirty.svg) `chart-clean-vs-dirty.svg` | Both conditions side by side | Preprocessing slide, if space |

---

# PART 5 — REPORT TEMPLATES

## 5.1 Technical report

```
1. Problem        one paragraph, the reader's problem not the system's
2. Approach       what we built, one diagram
3. Findings       the three findings, each with n and the noise floor
4. Negative results   the ones that contradicted us - lead with these
5. Limitations    hardware ceiling, noise, simulated degradation
6. Conclusion     what a reviewer would do next
```

Rules: every number carries its `n`; every difference smaller than ±0.05 CER is
described as noise; the negative results appear before the positive ones.

## 5.2 Progress update (weekly)

```
Done             measurable, one line each
Measured         the numbers that moved, with n
Negative         what we tried that did not work
Next             the specific next experiment
Blocked          what we need from whom
```

## 5.3 Paper section

```
4.1 Dataset        MoDeTrans (IIT Roorkee / MIT), authentic expert references
4.2 Method         restoration configs, whole-page vs segmented, decoding
4.3 Protocol       same scorer, same pages, +/-0.05 noise floor stated up front
4.4 Results        per-config table + the segmentation regression
4.5 Threats        <6 GB VRAM, n=10, simulated degradation, possible train overlap
4.6 Discussion     human-in-the-loop design and why the ceiling is the model
```

## 5.4 Abstract

> LipiLens is a human-in-the-loop transliteration aid for historical
> Modi-script manuscripts, using a 4-bit quantised Qwen2.5-VL-3B with a
> domain LoRA on consumer hardware. We measure character error rate against
> authentic expert references and report **63.7%** on clean scans and **65.2%**
> on simulated photographic degradation, against a published adapter baseline
> of 0.328 CER. Our central negative finding is that line segmentation — widely
> assumed to help vision-language transcription by raising the visual-token
> budget — cost 26 accuracy points in our setting by fragmenting text lines and
> discarding ascenders and matras. We also show that image preprocessing, which
> is often assumed to help, is not measurably helpful on either, and we report
> the n=10 result we had to retract when n=23 reversed it. We release an
> evaluation harness so that claims about transcription
> quality are reproducible rather than anecdotal.

---

# PART 6 — KNOWN LIMITS

State these proactively. Each one has a reason, not just a fact.

| Limit | Why it exists |
|---|---|
| 4 GB VRAM, below the adapter's 6 GB recommendation | Hardware. Measured 3.9 GB in use. |
| ±0.05 CER noise on 10-page runs | Sample size. Differences below this are not results. |
| n=10 per experiment | Time: ~35 s per page on this GPU. 50 pages ≈ 30 min per arm. |
| Degradation is simulated | Authentic text, authentic references, simulated capture. Never present as a photograph. |
| Whole-page reads have no line denominator | The progress bar sweeps without a percentage rather than invent one. |
| Progress is per-process, in-memory | A restart loses the live view, not the result. Multiple workers would need the database. |
| Single-user, no auth | Do not expose publicly. |
| Possible train/eval overlap on MoDeTrans | Disclosed caveat; stated in the paper. |

---

# PART 7 — WHAT WE HAVE NOT TRIED

Each is a one-line change on inference.

| Idea | Cost | Status |
|---|---|---|
| Beam search (`num_beams=4`) | **4.9× wall clock** | **Measured: no gain.** +0.004 CER, 9 pages worse / 8 better. Noise. |
| `merge_and_unload()` the LoRA | Free | **Measured: destroys the model.** CER 1.064, worse on 20/20 pages. PEFT re-quantizes the base on merge, so a QLoRA adapter is merged into weights it was never fitted against. **Never enable.** |
| fp16 vs bf16 compute dtype | Free | **Measured: no gain.** +0.010 CER, no speed benefit. bf16 stands. |
| Conditional preprocessing | ~1 day | **Measured against.** n=23 found no config beats `original` on damaged input. |
| `prepare_model_for_kbit_training()` | Free | Not measured. It is a *training* prep; we only run inference. |
| Larger model on more VRAM | Hardware | **The only real path to materially better accuracy** |

All four inference levers are now measured (`LEVERS`, n=20, paired against a
control that reproduced the token-sweep arm byte-for-byte). None helped. Only
the input representation moved accuracy at all.

**Before anyone spends GPU time on these:** log the result in
`experiments/results/eval/` with a new tag and update this document. Do not
update the README with a single un-replicated run.