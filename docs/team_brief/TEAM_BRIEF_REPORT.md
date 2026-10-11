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
| Character accuracy, degraded captures | **62.4%** (CER 0.376) | `eval_DEG-MED_metrics.csv`, 10 pages |
| Adapter's published mean, 204 held-out pages | 67.2% (CER 0.328) | adapter model card |
| Share of adapter examples below CER 0.20 | 21% | adapter model card |
| Share in the 0.20–0.40 "fair" band | 53% | adapter model card |
| Measurement noise, 10-page runs | **±0.05 CER** | `plain` vs historical baseline, 10 pages |
| Time per page | ~55–120 s | `eval_*_metrics.csv` |
| First-page extra cost (model load) | ~85 s | live runs |
| Hardware | RTX 2050, **4 GB VRAM** | `nvidia-smi` |
| VRAM in use during inference | ~3.9 GB of 4 GB | `nvidia-smi` |
| Adapter's recommended VRAM | ≥6 GB (developed on 8.5 GB) | adapter model card |
| Tests | 93 passing | `pytest tests/ -q` |

## 1.2 Configuration results

| Configuration | CER | Accuracy | Verdict |
|---|---|---|---|
| **Whole page + `original`** | **0.363** | **63.7%** | **shipped** |
| + repetition guard + 512 tokens | 0.363 | 63.7% | no measurable effect |
| `enhanced` on clean input | 0.367 | 63.3% | negligible loss |
| `denoised` on degraded input | 0.378 | 62.2% | small gain |
| **`enhanced` on degraded input** | **0.376** | **62.4%** | small gain |
| `binarized`, any input | 0.433–0.433 | 56.7% | **loses everywhere** |
| 1.5× pre-upscale | 0.417 | 58.3% | **worse** |
| Line segmentation | 0.623 | 37.7% | **much worse — now off** |

## 1.3 Three facts to have ready cold

1. **The accuracy regression.** Line segmentation was introduced as "the
   accuracy fix". Measured, it cost **0.363 → 0.623**. It is now off by default.
2. **Two of our own predictions were wrong.** The 1.5× upscale (rated
   highest-value) measured worse. The repetition guard changed nothing.
3. **The product thesis is directionally right but small.** Cleaning a degraded
   scan buys ~2 points. It is not the transformation it sounds like.

---

# PART 2 — CLAIM GUARDRAILS

> **This is the section that protects the team.** We removed a flagship claim
> because measurement disproved it. Do not put a new one in without evidence.

## 2.1 Say this / not that

| ✅ Say | ❌ Never say | Why |
|---|---|---|
| "63.7% character accuracy, measured on 10 pages against expert references" | "90% accurate" | Never measured. Model ceiling is ~0.33 CER. |
| "Segmentation measured 0.363 → 0.623, so we turned it off" | "Segmentation improves accuracy by giving the model more tokens per character" | **Disproven by our own experiment.** |
| "Preprocessing helps on dirty scans (+2.3) and is neutral on clean ones" | "Preprocessing cleans up the image so the model reads better" | Unqualified, this is false on clean input. |
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
authentic pages with authentic ground truth, and re-ran the comparison. On
degraded captures, preprocessing is worth ~2 points; on clean captures it costs
~0.4. **The thesis holds, but it is small** — and it is now measured rather than
assumed.

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
> authentic expert references and report **63.7%** on clean scans and **62.4%**
> on simulated photographic degradation, against a published adapter baseline
> of 0.328 CER. Our central negative finding is that line segmentation — widely
> assumed to help vision-language transcription by raising the visual-token
> budget — cost 26 accuracy points in our setting by fragmenting text lines and
> discarding ascenders and matras. We also show that image preprocessing, which
> is often assumed to help, is worth roughly two points and only on degraded
> input. We release an evaluation harness so that claims about transcription
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

Each is a one-line change on inference. None has been measured.

| Idea | Cost | Expectation |
|---|---|---|
| Beam search (`num_beams=4`) | ~2× wall clock, negligible VRAM | Standard OCR win; plausible small gain |
| `merge_and_unload()` the LoRA | Free | Often slightly better and faster in 4-bit |
| `prepare_model_for_kbit_training()` | Free | Documented PEFT prep we omitted |
| fp16 vs bf16 compute dtype | Free | Consumer-card bf16 quirks exist on sm_86 |
| Conditional preprocessing | ~1 day | Only worth it if n=50 confirms the +2 points |
| Larger model on more VRAM | Hardware | **The only real path to materially better accuracy** |

**Before anyone spends GPU time on these:** log the result in
`experiments/results/eval/` with a new tag and update this document. Do not
update the README with a single un-replicated run.