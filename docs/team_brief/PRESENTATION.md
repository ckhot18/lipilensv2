# LipiLens — Presentation Deck Outline

**Working file.** Each slide below has the on-slide content, the exact asset to
place, and what to say. Build the PPT from this; do not invent new numbers.

Deck target: **14 slides, ~12 minutes**, then Q&A.
Everything traces to **[TEAM_BRIEF_REPORT.md](TEAM_BRIEF_REPORT.md)**.

---

## Slide 1 — Title

**On slide**
```
LipiLens
Transcribing historical Modi-script manuscripts with a 3B model
on consumer hardware

Team name · Date
```

**Say:** *"Modi is the cursive administrative script of Maharashtra, used from
the 13th century to the mid-20th. Most surviving documents are property, tax
and court records. Almost none of them are searchable. This is our attempt to
change that."*

---

## Slide 2 — The problem

**On slide**
- Modi: no word spaces, heavy headline joining characters into continuous runs
- 17th–19th century administrative, legal and correspondence records
- Property, revenue and court history — currently unreadable to search
- The task is **transliteration**, not translation: same Marathi, different script

**Say:** *"Emphasise transliteration. A Marathi reader can read the output
directly — we're not translating content, we're converting script."*

---

## Slide 3 — What we built

**On slide** (pipeline)

```
photo → restore → transcribe → verify → archive → search
        OpenCV    Qwen2.5-VL-3B   human      SQLite
                 + Modi LoRA
```

**Asset:** none (draw the diagram natively, or paste `chart-*.svg` style arrows)

**Say:** *"Two acts. Restoration is CPU-only and instant — it never waits on
the GPU. Only transcription is slow, and only that step waits."*

---

## Slide 4 — The hard constraint

**On slide**
```
Hardware        RTX 2050 · 4 GB VRAM
Adapter needs   ≥6 GB (developed on 8.5 GB)
In use          ~3.9 GB of 4 GB during inference
Model           Qwen2.5-VL-3B-Instruct + Modi LoRA, 4-bit NF4
```

**Say:** *"This constraint shaped every decision. We could not go bigger, so
everything had to be earned by measurement instead."*

---

## Slide 5 — Where it stands

**On slide**
```
63.7%  character accuracy, clean scans
62.4%  on degraded captures
```
*Measured on 10 MoDeTrans pages against authentic expert references.*

**Say:** *"For calibration, the adapter's authors publish CER 0.328 over 204
held-out pages — we're within noise of the published baseline on a much
smaller GPU. At 63.7% a reviewer corrects roughly one character in three,
which is why the product is built around verification."*

> **Do not say 75–80%.** See guardrails §2.1.

---

## Slide 6 — Product screenshot

**Asset:** `05-result.png`

**On slide:** the result view, with the model name and the Devanagari draft visible

**Say:** *"This is a real 54.3-second run. The AI draft is never overwritten —
the reviewer edits below it and the original stays intact forever."*

---

## Slide 7 — The bug that started everything

**On slide**
- Symptom: upload → button changes → minutes of silence → error
- Cause 1: a **120-second timeout on every request**, including a call that takes ~110 s
- Cause 2: the **re-entry latch was seeded from the auto-file prop** — every run started from the Home page was silently discarded
- Restoration (~184 ms) always worked, which is why only the AI step appeared broken

**Asset:** `02-transcribe-empty.png`

**Say:** *"The team assumed the model was broken. It wasn't — a direct API call
returned HTTP 200 in 106 seconds with real Devanagari. The bug was in how we
called it."*

---

## Slide 8 — Our flagship feature was making things worse

**On slide** (the headline finding)
```
Line segmentation — introduced as "the accuracy fix"

CER 0.363  without segmentation
CER 0.623  with segmentation        −26 points of accuracy

Now OFF by default.
```

**Say:** *"The README claimed segmentation improved accuracy by raising the
visual-token budget from 0.49 to ~7.3 tokens per character. When we finally
measured it, it cost 26 points. Its band detector cut ascenders and matras off
every line and fed the model fragments at 23:1 to 40:1 aspect ratios. We fixed
the geometry completely — full-line padding, an aspect clamp, a config-driven
pixel budget — and re-measured 0.623. The theory was wrong, not the
implementation."*

> **This is the strongest slide in the deck.** Lead with it if time is short.

---

## Slide 9 — All configurations, measured

**Asset:** `chart-clean-arms.svg`

**Say:** *"Two of our own predictions were wrong. The 1.5× upscale, which we
reasoned would be the highest-value lever available, measured worse. The
repetition guard changed nothing — byte-identical output on all ten pages. We
report both because they're what the data said."*

---

## Slide 10 — Preprocessing only earns its keep on dirty input

**Asset:** `chart-degraded.svg` (and `chart-clean-vs-dirty.svg` if room)

**On slide**
| Config | Clean scan | Degraded capture |
|---|---|---|
| `original` | **63.7%** | 60.1% |
| `enhanced` | 63.3% | **62.4%** |
| `binarized` | — | **56.7%** |

**Say:** *"The product premise is dirty scan in, clean text out — but every
corpus page we had was already deskewed and contrast-normalised, so
preprocessing had no job, only ink to destroy. We built a degradation ladder
that re-photographs authentic pages with authentic ground truth. Cleaning is
worth about two points on a degraded scan and costs 0.4 on a clean one. The
thesis holds — it's just small. Binarisation loses everywhere."*

---

## Slide 11 — How we know

**On slide**
- 90 real model calls, every hypothesis saved to disk
- Same scorer, same 10 pages, same references for every configuration
- **±0.05 CER noise band on 10-page runs** — stated before any comparison
- Re-scorable without a GPU
- Before this: **8 of 18 local transcriptions had no ground truth at all**

**Say:** *"This is the part I'd defend hardest. Most of the earlier accuracy
work in this project was unmeasurable, because the outputs had nothing to be
scored against. An unscored run isn't a result. The harness exists so that
claims here are reproducible by anyone who runs one command."*

---

## Slide 12 — Honest limits

**On slide**
- 4 GB VRAM, below the adapter's recommended 6 GB — the ceiling is hardware
- n=10 per experiment; ±0.05 CER noise; differences smaller than that are not results
- Degradation is **simulated** damage on authentic text — never a real photograph
- Possible train/eval overlap on the public corpus (disclosed)
- 75–80% accuracy is **not reachable** on this hardware

**Say:** *"Read this slide out loud. The adapter's own published distribution
has 53% of pages in the 0.20–0.40 band and only 21% below 0.20 — holding 0.20
as an average means beating its authors on their own held-out set."*

---

## Slide 13 — What we'd do next

**On slide**
1. **More pages** — n=10 cannot resolve a 2-point difference; n=50 can
2. **Conditional preprocessing** — only if (1) confirms the effect
3. **Untested inference levers** — beam search, LoRA merge, bf16 vs fp16. All one-line changes, none measured
4. **More VRAM** — the only real path to materially better accuracy

**Say:** *"We're not done. But we're now measuring instead of hoping, which is
the actual change."*

---

## Slide 14 — Demo

**On slide:** live transcription, or `04-progress-reading.png` if the live run
is too slow on venue hardware

**Demo script:**
1. Open Home, pick the *Dirty demo* sample from the strip
2. Show the restoration preview appearing instantly
3. Click **Read with AI** — point at the progress bar: *"that number is a real
   measurement, not an animation"*
4. Text appears; show the verification panel; download the `.txt`

**Fallback:** if the GPU stalls, show `04-progress-reading.png` (a real captured
run) and `05-result.png` (a real 54.3 s run).

---

# Q&A BANK

Anticipated hard questions, with the answer that is actually defensible.

**"What's your accuracy?"**
63.7% character accuracy, CER 0.363, on 10 MoDeTrans pages against authentic
expert references. The adapter's authors publish CER 0.328 on 204 held-out
pages, so we're within noise of the published baseline on a much smaller GPU.

**"Why not 90%?"**
Capacity, hardware, and evidence. Their own distribution: 53% of pages sit in
0.20–0.40 CER, only 21% below 0.20. They developed on 8.5 GB and recommend
≥6 GB; we're on 4 GB. And the two obvious levers we tried — segmentation and
upscaling — both made it worse.

**"Isn't 63% useless?"**
For automated indexing, yes — and that isn't the product. The draft converts an
unreadable page into a searchable one, and a reviewer fixing a third of
characters preserves their edit permanently. Verification is the design.

**"If preprocessing doesn't help, why is it in your pipeline?"**
Because the product premise is dirty input. On degraded captures it's worth ~2
points; on clean scans it's neutral. We now default to `original` and offer
restoration rather than imposing it. Binarisation measured worse everywhere and
isn't reachable from the default path.

**"How do you know your references are correct?"**
MoDeTrans is a published corpus from IIT Roorkee and MIT with expert
transliterations. We didn't write our own ground truth.

**"What's actually new here?"**
Three things: the finding that line segmentation — the standard fix for
low visual-token budgets — cost 26 accuracy points in this setting; a
reproducible measurement harness that makes claims checkable rather than
anecdotal; and the job/progress architecture that makes a five-minute inference
watchable instead of opaque.

**"Isn't 10 pages too few?"**
Yes — that's why we state ±0.05 CER and refuse to claim differences below it.
The three conclusions we draw are each larger than that band or explicitly
labelled as directional.

**"Is the degradation dataset real?"**
The text and the ground truth are authentic. The photographic damage is
simulated. It's a controlled degradation, and we never present it as a
photograph.

**"Could you just use a bigger model?"**
With your hardware, no — 7B does not fit in 4 GB. That is the single largest
constraint on the project.

---

# DELIVERY NOTES

- **Lead with the negative finding (slide 8), not the feature list.** "We shipped
  a feature we thought improved accuracy, we measured it, and it was costing 26
  points" is the most credible thing in the deck.
- **Say "draft" out loud.** Never let "63%" float without the human-in-the-loop
  framing attached.
- **Show your working.** Slide 11 exists so the audience trusts the rest.
- **Have the guardrails table open** during Q&A. It is there because we removed a
  flagship claim once already.
- **If you are asked a number that isn't in the facts sheet, say "we haven't
  measured that."** That answer has earned this project's credibility; guessing
  will spend it.