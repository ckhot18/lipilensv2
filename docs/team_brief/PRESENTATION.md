# LipiLens — College Project Presentation

**Working file for building the PPT.** Every slide has its on-slide content, the
exact asset to place, and speaker notes. Build from this; do not invent numbers.

**Target: 22 slides, 15–18 minutes**, then demo and Q&A.
All facts trace to **[TEAM_BRIEF_REPORT.md](TEAM_BRIEF_REPORT.md)**.

**Deck order:** Problem → Objectives → Prior Work → Proposed Solution →
Technicalities → Results → Demo → Conclusion

---
---

# SECTION A — SETTING UP

## Slide 1 — Title

**On slide**
```
LipiLens
AI-Assisted Transliteration of Historical Modi-Script Manuscripts

A Human-in-the-Loop System on Consumer Hardware

Team members · Roll numbers
Project guide · Department · Institution
Date
```

**Say:** *"Our project converts photographs of handwritten Modi-script
manuscripts into searchable Devanagari text, using a 3-billion-parameter vision
model on a 4 GB consumer GPU, with a human verification step."*

---

## Slide 2 — Contents

**On slide**
```
1. Background & Problem
2. Objectives
3. Existing work & our gap
4. Proposed solution
5. System architecture
6. Technical implementation
7. Evaluation & results
8. Challenges we faced
9. Limitations
10. Future scope
11. Demo
```

**Say:** Keep this to 10 seconds. *"I'll start with the problem, then the
solution, then how we built and measured it."*

---
---

# SECTION B — THE PROBLEM

> **Define the problem before anything else.** If the audience doesn't feel the
> problem, nothing after this matters.

## Slide 3 — Background: what is Modi script?

**On slide**
```
• Administrative script of Maharashtra, ~13th century to mid-20th
• Cursive, ligature-heavy, written on a continuous headline (shirorekha)
• NO word spaces — characters run together
• Periods: Shivakalin (17th c.) · Peshwekalin (18th–19th c.) · Anglakalin (1818–1952)

Output is ordinary Devanagari — the script Marathi is written in today.
```

**Say:** *"Modi shares an ancestor with Devanagari. A Marathi speaker reads
Devanagari easily. So converting Modi into Devanagari turns a page unreadable
to almost everyone into one any Marathi reader can use. We are changing script,
not translating."*

> **Note for whoever builds this slide:** use a page from
> `showcase/GROUND_TRUTH.md` or `data/evaluation/` as the visual example rather
> than typing Modi Unicode by hand — our transcription is the subject of the
> project, so a hand-typed Modi string is exactly the kind of thing that could
> be wrong.

---

## Slide 4 — Why it matters

**On slide**
```
What survives:
  • Land and revenue records        • Court / legal proceedings
  • Royal correspondence            • Religious and administrative orders

Problem: these hold property and fiscal history,
         and almost none of it is searchable.
```

**Say:** *"This isn't an aesthetic concern. When a land record can't be found,
it can't be enforced. The value here is access."*

---

## Slide 5 — Problem statement

**On slide**
```
PROBLEM
Historical Modi-script manuscripts cannot be searched, quoted or
retrieved by anyone who does not read the original script.

CAUSES
 1. No reliable Modi OCR exists — cursive, no word boundaries, rare script
 2. Manual transcription by an expert is accurate but extremely slow
 3. Past digitization attempts treated pages as images, not as text

CONSEQUENCE
Legally and culturally significant documents remain effectively lost,
even when the physical page survives.
```

**Say:** *"Three causes, one consequence. Note cause 3 — a lot of previous
work stopped at producing a nicer-looking image. An image is not a record."*

---

## Slide 6 — Why existing approaches fail

**On slide**
| Approach | Why it fails here |
|---|---|
| Traditional OCR (Tesseract etc.) | No trained Modi model; assumes word spaces |
| Image "restoration" only | Produces a cleaner **picture**, still no searchable text |
| Cloud LLM APIs | Upload of heritage documents; cost; latency; no privacy |
| Large VLM (7B+) | Does not fit a 4 GB GPU |

**Say:** *"We didn't restore images for the sake of it. We need text, and we
need it to run on hardware a student actually owns."*

---
---

# SECTION C — WHAT WE SET OUT TO DO

## Slide 7 — Objectives

**On slide**
```
1. Transliterate handwritten Modi → Devanagari with MEASURED accuracy
2. Run entirely on consumer hardware (no paid cloud, no Colab)
3. Never destroy the original — preserve both draft and human correction
4. Make results archived and searchable
5. Show the work honestly, including what did not work
```

**Say:** *"Objective 5 is deliberate. We shipped a feature we believed improved
accuracy, measured it, found it cost 26 accuracy points, and turned it off.
I'll show you that in the results."*

---

## Slide 8 — Our contribution

**On slide**
```
1. A measured finding: the standard fix for low visual-token budgets
   (line segmentation) COST 26 accuracy points in this setting
2. A reproducible evaluation harness — claims checkable, not anecdotal
3. A job + progress architecture that makes a 5-minute inference watchable
4. An honest human-in-the-loop design calibrated to real model capability
```

**Say:** *"Contribution 1 is the research result. 2 is what makes it defensible.
3 and 4 are engineering."*

---
---

# SECTION D — WHAT OTHERS HAVE DONE

## Slide 9 — Prior work

**On slide**
| Work | Contribution | Gap we address |
|---|---|---|
| **MoDeTrans** corpus (IIT Roorkee / MIT) | 1,635 real Modi line-crops + expert Devanagari references | We build the *application*, not just the corpus |
| **SynthMoDe** | 4,086 synthetic Modi images for training | Augmentation only |
| **Qwen2.5-VL** (Alibaba) | Strong general VLM; handles documents | No Modi script capability |
| **qwen25vl-3b-modi-synth-lora** | Fine-tuned adapter, CER **0.328** | **A model, not a system.** No UI, no archive, no verification |

**Say:** *"We did not train a model. We built a system on top of a public
adapter and measured it honestly. That's the contribution."*

---
---

# SECTION E — THE SOLUTION

## Slide 10 — Proposed solution

**On slide**
```
LipiLens — two acts, deliberately separated

ACT 1 · RESTORE        CPU, OpenCV, ~184 ms      never waits on the GPU
ACT 2 · TRANSCRIBE     GPU, background job       the only slow step

Then: VERIFY (human) → ARCHIVE (SQLite) → SEARCH

Why separate?
  Restoration is instant and CPU-only, so the user gets visual feedback
  immediately. Only the model read is allowed to be slow — and we make
  that slow step watchable instead of opaque.
```

**Say:** *"This split is the core design idea. Fast feedback where we can have
it; honesty and progress where we can't."*

---

## Slide 11 — System architecture

**On slide**
```
┌──────────────┐   POST /api/manuscripts          ┌─────────────────┐
│   Browser    │──────────────────────────────────▶│  FastAPI :8000  │
│ React 19 +   │   POST /transcribe → 202 Accepted │                 │
│ Vite :5173   │   GET  /progress  (poll 1 s)     │  ┌───────────┐  │
└──────────────┘◀──────────────────────────────────│  │ Restoration│  │
                                                  │  │ (OpenCV)   │  │
                       GET /files/processed/...   │  └───────────┘  │
                                                  │  ┌───────────┐  │
                                                  │  │Transcribe │  │
                                                  │  │ background│  │
                                                  │  └───────────┘  │
                                                  │  ┌───────────┐  │
                                                  │  │  SQLite   │  │
                                                  │  └───────────┘  │
                                                  └─────────────────┘
```

**Say:** *"The critical design decision is on the left. The browser starts the
job and returns — it never holds a request open for five minutes."*

---
---

# SECTION F — TECHNICALITIES

> **The section judges will ask about.** Be precise.

## Slide 12 — Tech stack

**On slide**
```
Frontend   React 19 · Vite 8 · oxlint            (no business logic)
Backend    Python 3.12 · FastAPI · Uvicorn        (thin routes)
Vision     OpenCV 5 · NumPy 2.5                   (restoration)
AI         PyTorch 2.14 (CUDA 12.6) · Transformers 5.17
           PEFT 0.21 · bitsandbytes 0.50 (4-bit NF4)
Storage    SQLite · SQLAlchemy 2.0                (repository pattern)
Hardware   NVIDIA RTX 2050 · 4 GB VRAM
```

---

## Slide 13 — The model

**On slide**
```
Base            Qwen2.5-VL-3B-Instruct        (3.75 B params, vision + LLM)
Adapter         lgtk/qwen25vl-3b-modi-synth-lora
                  QLoRA · rank 32 · alpha 64
                  74 M trainable params (1.94 %)
                  trained on MoDeTrans + SynthMoDe (5,721 samples)
Quantisation    4-bit NF4 · bf16 compute dtype   → fits 4 GB VRAM
Published CER   0.328 (204 held-out pages)  vs 0.930 zero-shot
```

**Say:** *"We deliberately did not fine-tune. Training needs ~8.5 GB and many
GPU-hours. A public adapter let us spend our time on the system and, more
importantly, on measuring it."*

---

## Slide 14 — Dataset

**On slide**
```
MoDeTrans   IIT Roorkee + MIT · authentic handwritten Modi line-crops
            1,635 real samples, each with an expert Devanagari reference
            images 1268×463 px · ground truth from domain experts

Used here  10 pages (MT-001..010) per experiment, 90 model calls total

Degraded set  scripts/make_realistic.py re-photographs the SAME authentic
              pages: aged paper, uneven lighting, foxing stains, skew,
              JPEG artefacts — authentic text, authentic references,
              simulated capture
```

**Say:** *"Using the corpus's own expert references means our accuracy numbers
are not self-graded."*

---

## Slide 15 — Restoration pipeline

**On slide**
```
7 named configs, pure OpenCV, no GPU, ~184 ms:

  original          no-op — the honest baseline
  grayscale         luminance only
  denoised          non-local means
  enhanced          + CLAHE local contrast
  deskewed          Hough + warpAffine
  binarized         Otsu threshold        ← measured worse everywhere
  full_restoration  the full chain        ← worst measured

Each stage is a pure function with its own tests.
Preview endpoint returns instantly and never touches the model.
```

---

## Slide 16 — Inference

**On slide**
```
prompt     fixed instruction (verbatim from the adapter's model card):
           "Transliterate the text in this image into Devanagari script."
decode     greedy (do_sample=False), max_new_tokens 512
           repetition_penalty 1.05 (guards against loops)
precision  4-bit NF4 via bitsandbytes, bf16 compute, device_map="auto"
input      whole page, original pipeline, no segmentation  ← measured
```

**Say:** *"The prompt is the adapter author's recommended wording, verbatim.
We did not invent a prompt and hope."*

---

## Slide 17 — The job + progress architecture

**On slide**
```
WHY      a page takes ~55–120 s. A single blocking HTTP request gives the
         user nothing to look at, and browsers abort long requests.

1  POST /api/manuscripts/{id}/transcribe   → 202 Accepted, immediately
2  work runs on a background thread; the archive row is written exactly once
3  GET  /api/manuscripts/{id}/progress     → polled every 1 s

progress reports:   stage · percent · lines done · elapsed · text so far · error
stages:             loading_model → model_ready → reading → done
```

**On slide (continued)** — bar behaviour
```
Determinate  when a line count exists      → real percentage
Indeterminate model load / whole-page read → sweep, no invented percentage
```

**Say:** *"The bar never invents a number. When we don't know the denominator,
we show motion instead of a fake percentage."*

---

## Slide 18 — Data model

**On slide**
```
manuscripts           original image · restored image · status · sha256
preprocessing_configs  named config + exact JSON parameters (reproducibility)
transcriptions         ai_transcription · verified_transcription · status

INVARIANTS
  ai_transcription is NEVER modified after creation
  verified_transcription is written only through the verify endpoint
  identical (image, config) upload → existing record returned, not duplicated
```

**Say:** *"The AI draft is a permanent record of what the model produced. A
reviewer's correction is stored beside it, never over it."*

---
---

# SECTION G — RESULTS

## Slide 19 — How we measured

**On slide**
```
Problem:  8 of our first 18 local transcriptions had NO ground truth
          and could not be scored at all.

Fix:      scripts/evaluate_local.py
          · runs the REAL pipeline (restoration included)
          · scores against expert references with a fixed CER/WER module
          · saves every hypothesis to disk
          · re-scores any result without using the GPU

Scope:    90 real model calls · 10 pages · same scorer every time
Noise:    ±0.05 CER on 10-page runs — stated before every comparison
```

**Asset:** none

**Say:** *"This slide is here so you trust the next three."*

---

## Slide 20 — Results

**Asset:** `chart-clean-arms.svg`

**On slide**
| Configuration | CER | Accuracy |
|---|---|---|
| **Whole page + `original` (shipped)** | **0.363** | **63.7 %** |
| + repetition guard + 512 tokens | 0.363 | 63.7 % |
| `enhanced` on clean input | 0.367 | 63.3 % |
| 1.5× pre-upscale | 0.417 | 58.3 % |
| Line segmentation | 0.623 | 37.7 % |

**Say:** *"Two rows contradict what we expected. The 1.5× upscale, which our
own token-budget theory said would be the highest-value lever available,
measured worse. The repetition guard changed nothing — byte-identical output on
all ten pages."*

---

## Slide 21 — Our main finding

**On slide**
```
BEFORE  README claimed:
        "segmentation multiplies visual tokens per character
         0.49 → 7.3, and is the accuracy fix"

MEASURED
        without segmentation   CER 0.363
        with segmentation      CER 0.623        −26 accuracy points

WHY
        the band detector cut ascenders and matras off every line and
        fed the model fragments at 23:1 – 40:1 aspect ratios

WE REPAIRED IT  (full-line padding, aspect clamp, config-driven pixel budget)
        re-measured  0.623          the theory was wrong, not the code

NOW      SEGMENT_LINES defaults to OFF
```

**Say:** *"We removed a flagship claim from our README rather than softening it.
The visual-token argument is real in general — it just does not apply when the
segments it produces are not text lines."*

---

## Slide 21b — Then we tested our own explanation, and it was wrong

**Asset:** `fig7-context.svg`

**On slide**
| Intervention | ΔCER |
|---|---|
| Add a whole extra page of context | **−0.001** (worse 10 / better 9 / tie 1) |
| Remove the page's internal line structure | **+0.290** (worse 19 / tie 1, p = 3.8 × 10⁻⁶) |

Every bar at **full native resolution**; identical prompt; only the presence of
a neighbouring page varies. The model reads two complete pages in one call on a
4 GB card.

**Say:** *"We'd been saying 'keep the page whole because context is valuable'.
Then we tested it. Adding a second whole page changes nothing — not one page out
of twenty moved. Context is worthless here *and* free. So the real reason to
keep the page whole is its internal geometry: the relationship between a line's
baseline, its ascenders, and the matras hanging below it. Cropping to 23:1
slivers deletes exactly that, and neither more tokens nor more pages can put it
back. Same instruction, wrong reason, until we measured it."*

---

## Slide 22 — Preprocessing on degraded input

**Asset:** `chart-degraded.svg` (or `chart-clean-vs-dirty.svg`)

**On slide**
| Config | Clean scan | Degraded capture (n=23) |
|---|---|---|
| `original` | **63.7 %** | **65.2 %** |
| `denoised` | — | 66.6 % *(p=0.68, not significant)* |
| `binarized` | — | 56.0 % |
| `enhanced` | 63.3 % | **49.6 %** |

**Say:** *"Our corpus was already deskewed and clean, so preprocessing had no
job — only ink to destroy. We built a degradation ladder on authentic pages and
expected cleaning to help on damaged input. At ten pages it looked like a
two-point gain. At twenty-three it reversed: `enhanced` became the *worst*
config, losing fifteen points, and nothing beat leaving the image alone. The
ten pages we started with still favour it — the reversal lives entirely in the
pages we added. That's not a bug in our harness; it's the harness working. And
it means we retracted a claim that was already in our own documentation."*

---
---

# SECTION H — ENGINEERING REALITY

## Slide 23 — Challenges we faced

**On slide**
| Challenge | How we resolved it |
|---|---|
| App appeared to hang for minutes, then error | A 120 s client timeout was killing a call that takes ~110 s; replaced with a background job + polling |
| Clicks silently did nothing | Re-entry latch was seeded from the auto-file prop, so every run started from the Home page was discarded |
| Results were fluent but wrong | Line segmentation was fragmenting lines — measured, then disabled |
| "Restoration" made things worse | Split the two acts; restoration is instant CPU preview only |
| 4 GB VRAM is very tight | One model process at a time; harness detects a dead CUDA context and stops rather than recording false results |
| Server logs were silent | Called `configure_logging()` at startup — every CUDA error now visible |

**Say:** *"The first three are the ones worth remembering — each looked like a
model failure and was not."*

---

## Slide 24 — Limitations

**On slide**
```
• 4 GB VRAM, below the adapter's recommended ≥6 GB — a hardware ceiling
• n = 10 per experiment; ±0.05 CER noise. Smaller differences are NOT results
• Degradation is SIMULATED capture on authentic text — never a real photograph
• Possible train/eval overlap on the public corpus (disclosed)
• 75–80 % accuracy is NOT reachable on this hardware
• Progress state is in-memory; a restart loses the live view, not the result
• Single-user, no authentication — must not be exposed publicly
```

**Say:** *"Read this slide out loud. The adapter's own published distribution
has 53 % of pages in the 0.20–0.40 CER band and only 21 % below 0.20. Holding
0.20 as an average would mean beating its authors on their own held-out set."*

---

## Slide 25 — Future scope

**On slide**
```
Measured and closed out
  · beam search       +0.004 CER, 4.9x latency      no gain
  · LoRA merge        CER 1.064, worse 20/20       destroys the model
  · fp16              +0.010 CER                  no gain
  · conditional preprocessing                    evidence AGAINST it (n=23)

Short term (no new hardware)
  · n = 50 on degraded input so 1-point effects resolve
  · crop *within* a page (overlapping half/three-quarter windows at native
    resolution) to find where within-page structure actually breaks
  · document-scale transcription — now justified, because two pages per call
    measured free, not because extra context helps

Medium term
  · larger model (7B+) on more VRAM — the only real path to better accuracy
  · named-entity highlighting for archival search

Long term
  · fine-tuning an adapter ourselves on MoDeTrans at native resolution
  · crowd-sourced verification across many readers
```

---
---

# SECTION I — CLOSING

## Slide 26 — Conclusion

**On slide**
```
• We solved the retrieval problem, not the OCR ceiling
• 63.7 % character accuracy turns unreadable pages into searchable ones
• Our strongest result is NEGATIVE and we stand behind it:
  the standard token-budget fix cost 26 accuracy points here
• We then tested our own explanation and corrected it:
  adding a whole page is free (-0.001), cropping one page costs +0.290.
  Structure, not context, is what breaks
• We retracted two of our own claims when measurement contradicted them
• The evaluation harness makes every claim in this deck reproducible
```

**Say:** *"A reviewer correcting one character in three converts an unreadable
page into a searchable record. That is a useful product, stated honestly."*

---

## Slide 27 — Demo

**On slide:** title card, then the live app

**Demo script**
1. Home → click the **Dirty demo** sample
2. Restoration preview appears instantly — *"CPU only, 184 ms"*
3. Click **Read with AI** → point at the progress bar:
   *"that is a real measurement, not an animation"*
4. Text arrives; open the verification panel; download the `.txt`
5. Library → show the archived record and search

**Fallback if the GPU stalls:** `04-progress-reading.png` (a real captured
in-flight run) and `05-result.png` (a real 54.3 s run).

---

## Slide 28 — References

**On slide**
```
[1] MoDeTrans dataset — IIT Roorkee / MIT, via historyHulk/MoDeTrans
[2] qwen25vl-3b-modi-synth-lora — model card (Sachin Godse, lgtkgtv)
[3] Qwen2.5-VL Technical Report — Alibaba
[4] LoRA: Low-Rank Adaptation of Large Language Models — Hu et al.
[5] QLoRA: Efficient Finetuning of Quantized LLMs — Dettmers et al.
[6] This project's evaluation data and harness
    → experiments/results/eval/  ·  scripts/evaluate_local.py
```

> Add any survey citations your guide requires — we deliberately left the
> literature list to only those we can vouch for directly.

---

## Slide 29 — Thank you / Q&A

**On slide**
```
Thank you
Questions?

lipilens · github.com/ckhot18/lipilensv2
```

---
---

# Q&A BANK

Anticipated hard questions with defensible answers.

**"What's your accuracy?"**
63.7% character accuracy (CER 0.363), 10 MoDeTrans pages against authentic
expert references. The adapter's authors publish CER 0.328 over 204 held-out
pages — we're within noise of that on a much smaller GPU.

**"Why not 90%?"**
Three reasons. Capacity — their distribution has 53% of pages at 0.20–0.40 CER
and only 21% below 0.20. Hardware — 8.5 GB to develop, ≥6 GB recommended, we
have 4 GB. And evidence — the two obvious levers both made it worse.

**"Isn't 63% useless?"**
For automated indexing, yes — and that isn't the product. The draft makes the
page searchable and a reviewer's correction is stored permanently beside it.
Verification is the design, not a workaround.

**"If preprocessing doesn't help, why is it in the pipeline?"**
The premise is dirty input, so we built the ladder to test it rather than assume
it. The answer is that nothing beats leaving the image alone — at n=23 every
config is within noise of `original` and `enhanced` is actively harmful. It
stays because the premise is testable, not because it was confirmed. We default
to `original` and it is what we recommend.

**"How do you know your references are correct?"**
MoDeTrans is a published corpus with expert transliterations from IIT Roorkee
and MIT. We did not write our own ground truth.

**"Is 10 pages enough?"**
No — that's why we state ±0.05 CER and refuse to claim smaller differences.
Our three conclusions are each larger than that band or explicitly labelled
directional.

**"Is the degradation dataset real?"**
The text and ground truth are authentic. The photographic damage is simulated.
It is a controlled degradation and we never present it as a photograph.

**"What's actually new in your work?"**
The negative finding on segmentation; a reproducible evaluation harness; and a
job/progress architecture that makes a long inference watchable.

**"Why didn't you train your own model?"**
Training needs ~8.5 GB and many GPU-hours. A public adapter let us invest in
the system and in measuring it — which is where the actual contribution is.

**"Could you use a bigger model?"**
Not on this hardware — 7B does not fit in 4 GB. That is the single largest
constraint on the project.

---

# DELIVERY NOTES

- **Order matters.** Problem (5) → objectives (7) → solution (10) →
  technicalities (12–17) → results (19–22) → limits (24). Do not open with
  features; the audience must feel the problem first.
- **Lead the results with the negative finding (slide 21).** "We shipped a
  feature we thought improved accuracy, measured it, and found it cost 26
  points" buys more credibility than any feature list.
- **Always say "draft", never "accurate transcription".** 63% without that
  framing will be heard as 63% accurate.
- **Show your working.** Slide 19 exists so the results slides are trusted.
- **Slides 24 and 26 should be read aloud, not skimmed.** Saying what you cannot
  do is what makes the rest credible.
- **Timing:** 18–25 s per content slide, 10 s for section headers, 2 min demo.
- **If asked a number that isn't in the facts sheet: "we haven't measured
  that."** That answer earned this project's credibility; guessing spends it.