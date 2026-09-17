# LipiLens Research Paper Notebook

**Purpose of this document:** a living, append-only research notebook. It is not a polished paper draft. Every claim here must trace to an actual experiment, file, or observation. Placeholders are marked explicitly and must never be silently treated as results. See Section 27 (Research Integrity Rules) before writing anything in this file.

**How to use this file during the project:** append to Sections 0, 7, 8, 9, 11, 14–20 as work happens. Do not write the polished narrative sections (22–26) until real results exist to narrate.

---

## 0. Research Status

*Update this section every time something material changes. This is the fastest way for a future session (human or agent) to know where things actually stand.*

- **Research question:** defined (Section 2) — not yet answered.
- **Dataset status:** REAL DATA 2026-09-17: 20 MoDeTrans samples (MT-001..MT-020, refs 73–203 chars) with expert ground truth in `data/raw/mode_trans/` + `data/evaluation/`. Plus the unprovenanced chart sample.
- **Baseline status (n=20, original condition, Colab):** mean CER 0.317 / WER 0.688 — same ballpark as the card's self-reported 0.328 (NOT a comparison: train-split overlap, n=20 vs 204).
- **Restoration comparison (first data):** EXP-003 on MT-002 only — original 0.099 → enhanced 0.121 → binarized 0.176 (WER flat 0.286). n=1 page, descriptive only; supports H3 directionally on clean samples.
- **Archive status (Phase 5, 2026-09-17):** SQLite schema live (`lipilens.db`, 3 tables, 0 rows) matching guide §16 + `image_sha256`; repository enforces AI-draft immutability and verify-only-writes-verified; 8/8 DB tests pass; `get_manuscript` refreshes collections (same-session staleness fixed and tested).
- **API status (Phase 6, 2026-09-17):** routes live (upload→restore→transcribe→detail, list/search with pagination, idempotent re-upload, verify) with 9/9 stubbed API tests; static `/files` image serving; transcription failure preserves manuscript (503 path tested). LIVE end-to-end PASSED (real HTTP + real Colab + verify + search through the app).
- **Flaws fixed this round:** Colab retry-with-backoff (proved live: 1 SSL blip auto-recovered, 17/17 batch); health probes Colab in colab mode; cache key now includes pinned model revisions (base 6628554…, adapter 5b9957d…); sync upload handler (no event-loop block); pagination; verify max-length; scratch dir moved out of served paths; deskew-before-binarize (full_restoration truly binary again, metrics regenerated).
- **Frontend status (Phase 7, 2026-09-17):** Transcribe/Library/About implemented with state-based nav (no router dep); `vite build` passes; API contract checked field-for-field against backend schemas. Browser click-through still to be done by the user (backend: `uvicorn backend.main:app`, frontend: `npm run dev`, Colab warm).
- **Dataset expansion (2026-09-17):** 17 more MoDeTrans samples fetched and transcribed (MT-004..MT-020) — n=20 with ground truth (EXP-004a–q; one SSL blip auto-recovered, 17/17 complete).
- **Preprocessing status:** IMPLEMENTED + VALIDATED 2026-09-17 (Phase 2). 7 preset configs run standalone via `scripts/smoke_test_opencv.py` (all OK); 16/16 unit tests pass (`tests/test_restoration.py`); real image metrics in `experiments/results/phase2_metrics.csv` and visual report `docs/PHASE2_REPORT.md`. No transcription effect measured yet — image-quality proxies only.
- **Model status:** WORKING VIA COLAB (2026-09-17, EXP-001). First real inference succeeded: 79-char Devanagari output in 73.6 s (includes Colab cold-start/model load) on `sample_modi_page.png`. Local full-weight inference remains blocked (weight-download stall, see `PHASE3_BLOCKER.md`); local code is recipe-aligned but unrunnable here. Colab is the primary inference path.
- **Experiment status:** EXP-001 run (qualitative only — no ground truth, no CER/WER).
- **Results status:** REAL NUMBERS (EXP-002, n=3, original condition): CER 0.171 / 0.099 / 0.567 (mean 0.279); WER 0.381 / 0.286 / 0.955 (mean 0.541). No other conditions measured yet — restoration-vs-original comparison is still open (Phase 8).
- **Paper status:** notebook only; no draft of the final paper (Section 22's structure) has been filled in with real content.

---

## 1. Working Titles

*Provisional. Not final. Revisit once results exist — a title should reflect what was actually found, not just what was attempted.*

1. "Evaluating Manuscript Image Restoration for Vision-Language Transcription of Historical Modi Script" *(provisional)*
2. "LipiLens: A Restoration-Aware Vision-Language Pipeline for Historical Modi Manuscript Digitization" *(provisional)*
3. "Does Preprocessing Help? A Small-Scale Study of Image Restoration Effects on VLM-Based Modi Transcription" *(provisional — more honest about scale if the final sample size stays small)*

---

## 2. Central Research Question

**How does manuscript image restoration/preprocessing affect the transcription performance of a modern vision-language model (Qwen2.5-VL-3B + a Modi-specific LoRA adapter) on degraded historical Modi-script documents?**

Secondary questions, time permitting:
- Which individual restoration stage (denoising, contrast enhancement, binarization, deskewing) has the largest effect, positive or negative?
- Does restoration help more, less, or unpredictably as document degradation increases?

---

## 3. Hypotheses

These are hypotheses — stated before results exist — **not conclusions**. They must not be silently reworded as findings later.

- **H1:** Certain restoration operations (denoising, contrast enhancement) improve transcription accuracy relative to the unprocessed original, for at least some manuscript conditions.
- **H2:** The impact of restoration (positive or negative) increases with the degree of manuscript degradation — cleaner source images should show smaller restoration effects than heavily degraded ones.
- **H3:** A full/aggressive restoration pipeline is not necessarily optimal for every manuscript — some stages (particularly binarization/thresholding) may destroy faint ink strokes and hurt accuracy on already-marginal images, even while helping on others.

---

## 4. Research Contribution

**Existing work:** general OCR/HTR (handwritten text recognition) restoration-preprocessing studies exist for other scripts (see Section 6, to be populated with real citations only). VLM-based transliteration of low-resource historical scripts is an emerging area; a Modi-specific LoRA adapter (`lgtk/qwen25vl-3b-modi-synth-lora`) already exists as prior work by its author(s) — LipiLens does not claim to have created this adapter.

**Our experiment:** a small-scale, empirical comparison of how several classical restoration configurations affect this specific model+adapter's transcription accuracy on real (or best-available) Modi manuscript images — something that, as far as this project's literature review determines (Section 6), has not been specifically studied for this model/adapter/script combination. This claim of novelty must be checked against Section 6's actual findings before being stated in any final paper draft, not assumed here.

**Our software contribution:** an end-to-end, human-in-the-loop digitization pipeline (LipiLens itself) that operationalizes the experiment's findings into a usable preservation tool, with an explicit, structural separation between AI draft and human-verified transcription.

---

## 5. Background

*(Write this section in your own words once you've done enough reading to summarize accurately — do not fabricate historical or technical claims. Rough scope to cover, to be filled in with real, checkable content:)*

- Historical Modi script: what it was used for, roughly when, why it's now hard to read.
- Digital preservation of historical manuscripts generally: why it matters, common challenges (degradation, access, scale).
- Manuscript degradation types relevant here: fading, staining, skew, bleed-through, uneven lighting from photography.
- OCR/HTR (handwritten text recognition) background, including why classical OCR approaches struggle with historical/low-resource scripts.
- Vision-language models as a newer approach to this problem: how they differ from traditional OCR pipelines (holistic image understanding + language generation vs. character-segmentation-based recognition).
- Human verification / human-in-the-loop design in digital humanities and archival tooling: why AI-authoritative transcription is broadly considered inappropriate for scholarly/archival use without review.

---

## 6. Related Work

*Do not invent citations. Leave rows empty until a real source is found and read. An empty table is honest; a fabricated one is not.*

| Paper title | Authors | Year | Venue | Method | Dataset | Metrics | Limitations | Relevance to LipiLens |
|---|---|---|---|---|---|---|---|---|
| *TO BE POPULATED — literature search not yet performed* | | | | | | | | |

---

## 7. Dataset

*Update as the real dataset is assembled.*

- **Dataset name:** `historyHulk/MoDeTrans` subset (IIT Roorkee; paper: arXiv 2503.13060, accepted ICDAR 2025) + 1 unprovenanced chart sample. Paper claims 2,043 expert-transliterated real document images across Shivakalin/Peshwekalin/Anglakalin eras; we use 3.
- **Source:** Hugging Face `historyHulk/MoDeTrans` (parquet, columns filename/image/text), fetched 2026-09-17 via `datasets` streaming. Manifest: `data/raw/mode_trans/MANIFEST.json` (MT-001←1.jpg, MT-002←10.jpg, MT-003←1000.jpg).
- **Number of images:** 20 with ground truth (+ 1 chart sample without).
- **Ground-truth availability:** expert Devanagari transliterations shipped with MoDeTrans, stored verbatim in `data/evaluation/MT-*.txt` (MT-001..MT-020). Ground-truth producer: dataset authors (expert-verified per paper); our confidence: taken as reference, not independently re-checked.
- **Image properties:** real continuous Modi handwriting (verified visually for MT-002: 3 ruled lines with headline flourish); refs 91–120 chars.
- **Train/test split:** not applicable — evaluation-only study, no model training (as anticipated).
- **Licensing:** MoDeTrans is MIT-licensed (per its HF page) — compatible with this academic use; attribution: Kausadikar et al., IIT Roorkee (arXiv 2503.13060). Chart sample `sample_modi_page.png`: provenance/license still TO BE CONFIRMED.
- **Limitations:** n=3 with ground truth (single digits — descriptive stats only); short texts selected (91–120 chars, for inference speed); one streaming hiccup observed during fetch (auto-retried, recovered). Chart sample: 552×424, provenance unconfirmed. See also Section 20.

---

## 8. Model

*Fill in with real, confirmed values only — do not guess a version number.*

- **Base model:** Qwen2.5-VL-3B — exact revision COMMITTED weights never downloaded, so NO verified hash. Hub API resolved `main` to `66285546d2b821cf421d4f5eb2576359d3770cd3` during the fetch attempt (observed, unverified — do not cite as the used revision).
- **Adapter:** `lgtk/qwen25vl-3b-modi-synth-lora` — revision likewise UNCONFIRMED (weights never downloaded). Card facts (read 2026-09-17): QLoRA rank 32 / alpha 64, 4-bit NF4, targets q/k/v/o + gate/up/down, 74M trainable (1.94%), trained 5,721 images (1,635 real MoDeTrans + 4,086 synthetic SynthMoDe), 2 epochs, ~9.75h on RTX 5060, self-reported test CER 0.328 (204 held-out real examples) vs 0.930 zero-shot.
- **Model version notes:** Phase 3 (2026-09-17): full local load NOT achieved — see Model status in Section 0. Local loader (`backend/services/transcription/local_qwen.py`) matches the card's official recipe (4-bit NF4, `device_map="auto"`, `AutoProcessor max_pixels=512*28*28`); compute dtype set to bfloat16 per recipe (RTX 2050 reports bf16 supported).
- **Quantization:** intended 4-bit NF4 via bitsandbytes 0.50.2 (imports OK on this Windows env) — never exercised on real weights. Colab path will use the same recipe; record actual VRAM there when run.
- **Inference configuration:** `max_new_tokens=256`, greedy (`do_sample=False`) — taken from the adapter card's usage script, not yet empirically tuned. TO BE RECORDED if changed after first real run.
- **Hardware:** local — RTX 2050, 4GB VRAM (3962 MiB free at idle), 8GB system RAM, Windows, torch 2.14.0+cu126, driver 592.82. NOTE: card author reports 3–4 GB VRAM at 4-bit and recommends ≥6 GB — local 4 GB is marginal even before Windows/CUDA overhead, which supports the Colab-primary decision. Colab GPU type TO BE RECORDED when first used. HF cache relocated to `D:\hf_cache` (C: had only ~4.4 GB free; D: ~36 GB).
- **Memory behavior:** local — never measured (weights never downloaded). Colab — TO BE MEASURED (server has no VRAM-reporting endpoint yet; suggested addition).
- **Prompt format:** official card prompt recorded verbatim (also used in `scripts/smoke_test_model.py`): "This image contains handwritten text in Modi script, a historical cursive script used to write the Marathi language. Transliterate the text in this image into Devanagari script. Output only the Devanagari text, with no explanation." Processor-verified: applies through `Qwen2_5_VLProcessor.apply_chat_template` (265 template chars) and encodes the real sample to input_ids (1,349). PROVEN END-TO-END in EXP-001 (Colab): this prompt produced 79-char Devanagari output with no echo — prompt format confirmed working, not just plausible.
- **Image resolution used at inference:** processor capped at `max_pixels=512*28*28`; sample encoded locally to pixel_values (1200,1176) during the processor check. Exact tensor shape on the Colab run TO BE RECORDED (server does not log it yet — suggested addition).

---

## 9. Restoration Pipeline

*For each stage, document purpose/implementation/parameters (known now) and expected/observed effect and experiment ID (filled in as experiments run).*

| Stage | Purpose | Implementation | Parameters | Reason for inclusion | Expected effect | Observed effect | Experiment ID |
|---|---|---|---|---|---|---|---|
| Grayscale conversion | Normalize channels | `cv2.cvtColor(..., COLOR_BGR2GRAY)` | — | Required precursor for most other stages | Neutral (enabling step) | Confirmed neutral on sample: mean/std/sharpness identical to original (204.48/29.91/1425.74) — see `docs/PHASE2_REPORT.md` | Phase-2 validation 2026-09-17 (image metrics only, no transcription) |
| Denoising | Reduce scan/camera noise | `cv2.fastNlMeansDenoising` | `h=10`, template 7, search 21 | Historical scans/photos often noisy | Improve legibility of fine strokes | Sharpness metric fell 1425.7→565.2 (smoothing confirmed); std 29.91→29.10. Transcription effect NOT yet measured | Phase-2 validation 2026-09-17 |
| CLAHE / contrast enhancement | Improve legibility of faded ink | `cv2.createCLAHE` | clipLimit 2.0, tiles (8,8) | Faded ink is a common degradation mode | Improve model's ability to distinguish ink from background | Contrast rose (std 29.1→32.9), dark-pixel share 2.6%→4.5%. Transcription effect NOT yet measured | Phase-2 validation 2026-09-17 |
| Adaptive/Otsu thresholding | Binarization | `cv2.adaptiveThreshold` / `cv2.threshold(..., THRESH_OTSU)` | Otsu auto (measured threshold 176 on sample); adaptive block 31, C 10 | Standard OCR preprocessing step | Uncertain — may help (clean separation) or hurt (destroy faint strokes); this is a central research question, not assumed | Otsu output verified truly binary (2 unique values); ink share 17.83%. Adaptive path unit-tested binary. Transcription effect NOT yet measured | Phase-2 validation 2026-09-17 |
| Background correction | Remove uneven illumination | NOT IMPLEMENTED | — | Uneven photography lighting is common | Improve downstream thresholding quality | Not implemented (optional per guide §12); recorded as gap, not silently omitted | — |
| Deskewing | Correct rotation | Hough-lines median angle + `cv2.warpAffine`, cap ±15° | measured −1.01° (deskewed), −1.36° (full) on near-upright sample | Manuscripts are rarely perfectly aligned when photographed | Improve model's ability to read consistent line orientation | Small correction applied; shape preserved; sharpness metric 1425.7→493.7 (resampling smoothing). Untested on strongly skewed images | Phase-2 validation 2026-09-17 |

**Known ordering effect (2026-09-17, real observation):** `full_restoration` output is NOT binary (256 unique values) despite including Otsu, because deskew runs after binarization and re-interpolates edges. If a strictly binary full output is ever needed, deskew must run before binarization. This ordering was left as-is and recorded here rather than silently changed, since no experiment has used it yet (reproducibility rule).

---

## 10. Experimental Design

- **Baseline:** the unprocessed original image, sent directly to the model ("original" condition).
- **Independent variable:** preprocessing configuration applied before the image is sent to the model (see `PROJECT_GUIDE.md` Section 12 for the defined configs: original, grayscale, denoised, enhanced, binarized, deskewed, full_restoration).
- **Dependent variables:** CER and WER (when ground truth exists); qualitative accuracy assessment (when it doesn't).
- **Controls:** same model/adapter/revision, same prompt, same inference parameters (`max_new_tokens`, decoding strategy) across all conditions for a given image — only the input image variant changes.
- **Evaluation metrics:** CER, WER (Sections 12–13); qualitative side-by-side comparison (Section 17) as a fallback/supplement.
- **Reproducibility requirements:** every experiment run must record the exact `preprocessing_config_id` (per `PROJECT_GUIDE.md` Section 16's schema), model revision, and prompt used, so it can be re-run identically later.

---

## 11. Experiment Log

*Append-only. One `EXP-XXX` block per run. Never edit a past entry's results after the fact — if a mistake is found, add a new entry noting the correction and why, rather than silently rewriting history.*

**Note (2026-09-17, Phase 2):** no transcription experiment has been run yet, so no
`EXP-XXX` entry exists. The Phase 2 pipeline validation (7 configs, real image
metrics, 16/16 unit tests) is logged in `docs/PHASE2_REPORT.md` and
`experiments/results/phase2_metrics.csv` — deliberately NOT as an `EXP-XXX`
entry, because no model inference occurred and no CER/WER could be computed.
The `EXP-001` template below remains empty until Phase 3/8 produce a real
model output.

**Note (2026-09-17, Phase 3):** first real model output NOT obtained. Local
weight fetch (Qwen/Qwen2.5-VL-3B-Instruct + `lgtk/qwen25vl-3b-modi-synth-lora`,
HF cache on `D:\hf_cache`) stalled at "Fetching 2 files: 0%" for the full
30-minute attempt window and was aborted per time-boxing (guide §§14–15);
only 16.8 MB of config/metadata reached disk. This is a network/time
outcome, NOT a code failure — the loader matches the card's official recipe
and the processor path is verified on the real sample. No EXP entry is
created for the processor check or the stub-server client test (neither
produced model text), but both are recorded here: processor
`Qwen2_5_VLProcessor` → chat template 265 chars → input_ids (1,349),
pixel_values (1200,1176); Colab client + `INFERENCE_MODE` dispatcher 5/5
tests pass; `colab/lipilens_colab_server.py` boots (`/health` OK). Next
action: run the Colab server on a GPU runtime and execute the first real
transcription there (becomes EXP-001).

**Update (2026-09-17, same day — SUPERSEDES the "NOT obtained" note above):**
EXP-001 succeeded via Colab (entry below). The earlier note is preserved
per the append-only rule but no longer describes the current state.

### EXP-001
- **Date:** 2026-09-17 ~12:30 IST
- **Objective:** Phase 3 smoke test — first real inference call (local or Colab), non-empty Devanagari output on the real sample.
- **Dataset:** `data/raw/sample_modi_page.png` (552×424). NOTE: visually confirmed to be a 6×8 handwritten Modi character chart (48 isolated glyphs), not a continuous manuscript page.
- **Input:** original image as-is (no restoration; "original" condition), via `ColabTranscriptionService.transcribe`.
- **Preprocessing:** none (original).
- **Model:** Qwen/Qwen2.5-VL-3B-Instruct + `lgtk/qwen25vl-3b-modi-synth-lora`, 4-bit NF4 bf16 (server side); revisions unconfirmed (weights live on Colab, hashes not recorded).
- **Hardware:** Colab GPU (type TO BE RECORDED — server exposes only `/health`); local side: RTX 2050 idle, network only.
- **Parameters:** official card prompt (Section 8); `max_new_tokens=256`, greedy `do_sample=False`.
- **Result:** 79-char single-line Devanagari output, saved verbatim in `experiments/results/EXP-001_transcription.json` (also `data/outputs/first_transcription.txt`). Rendered in `docs/phase3_output_card.png`. First two codepoints U+0906 U+0930.
- **CER:** N/A — no ground truth available.
- **WER:** N/A — no ground truth available.
- **Observations:** output is character-spaced (consistent with 48-glyph chart input); 50/79 Devanagari chars incl. 10 Devanagari digits (possible look-alike substitutions — unconfirmed without ground truth); no prompt echo, no repetition loop, clean termination. Total wall time 73.6 s including Colab cold-start/model load — steady-state latency unknown.
- **Files generated:** `experiments/results/EXP-001_transcription.json`, `experiments/results/exp_log.csv` (EXP-001 row), `data/outputs/first_transcription.txt`, `docs/phase3_*.png`.
- **Conclusion:** Phase 3 completion criterion met via the Colab path: real model, real image, real Devanagari string, directly observed. Local path remains blocked (download stall).
- **Next action:** Phase 4+ (API/DB/frontend wiring around the proven Colab path); obtain a real continuous-text manuscript page + ground truth for EXP-002 with CER/WER.

### EXP-002 (a/b/c — first quantitative baseline)
- **Date:** 2026-09-17 ~13:00 IST
- **Objective:** transcribe 3 real MoDeTrans pages (original condition, Colab) and score against shipped ground truth — first CER/WER.
- **Dataset:** MT-001 (1.jpg, ref 111 chars), MT-002 (10.jpg, ref 91), MT-003 (1000.jpg, ref 120).
- **Input:** original PNGs as saved (`data/raw/mode_trans/MT-00{1,2,3}.png`).
- **Preprocessing:** none (original) — all three rows; restoration comparison still open.
- **Model:** Qwen2.5-VL-3B + `lgtk/qwen25vl-3b-modi-synth-lora` via Colab (warm model: 18.8–25.0 s/call vs 73.6 s cold in EXP-001).
- **Hardware:** Colab GPU (type unrecorded); local RTX 2050 idle.
- **Parameters:** official card prompt; `max_new_tokens=256`, greedy.
- **Result:** hyps in `experiments/results/EXP-002_{MT-001,MT-002,MT-003}_hyp.txt`; metrics in `EXP-002_metrics.{csv,json}`; chart in `docs/exp002_results.png`.
- **CER:** MT-001 0.171 (S7/D5/I7) · MT-002 0.099 (S3/D5/I1) · MT-003 0.567 (S45/D16/I7) · mean 0.279.
- **WER:** MT-001 0.381 · MT-002 0.286 · MT-003 0.955 · mean 0.541.
- **Observations:** MT-002 near-perfect (only small sub/insertions, e.g. extra word, matra swaps); MT-001 fair; MT-003 fluent-but-wrong hallucination (grammatical Marathi, different content — see §18). Mean CER 0.279 is close to the card's self-reported 0.328 on 204 held-out examples — same ballpark, NOT a comparison (n=3, possibly overlapping training data — the adapter trained on MoDeTrans train split, and these 3 rows come from that same split, so scores may be OPTIMISTIC; treat as pipeline validation, not a generalization claim).
- **Files generated:** `experiments/results/EXP-002_*_hyp.txt`, `EXP-002_metrics.csv/.json`, `docs/exp002_results.png`, `exp_log.csv` rows EXP-002a/b/c.
- **Conclusion:** pipeline produces measurable, sane output on real pages with wide per-sample variance (0.099–0.567) — variance itself is the finding that motivates the restoration comparison.
- **Next action:** run restored-image conditions through the same 3 samples (Phase 8) for the first restoration-vs-original CER table.

### EXP-003
- **Date:** 2026-09-17 ~13:30 IST
- **Objective:** Phase 4 validation + first restoration comparison: same page (MT-002) through `run_full_pipeline` under enhanced and binarized configs.
- **Dataset:** MT-002 only (MoDeTrans 10.jpg, ref 91 chars).
- **Input:** `data/raw/mode_trans/MT-002.png` via `run_full_pipeline` (restored PNGs in `data/processed/_pipeline/`).
- **Preprocessing:** enhanced (CLAHE, no binarization) and binarized (CLAHE+Otsu).
- **Model:** Qwen2.5-VL-3B + Modi LoRA via Colab (warm; restore ~0.2 s, transcribe ~18.5 s per run).
- **Hardware:** Colab GPU (type unrecorded); local CPU restore.
- **Parameters:** official card prompt; `max_new_tokens=256`, greedy.
- **Result:** `experiments/results/EXP-003_MT-002_{enhanced,binarized}_hyp.txt` (97 chars each).
- **CER:** enhanced 0.121 · binarized 0.176 (vs original 0.099).
- **WER:** 0.286 for all three conditions (identical — damage is character-level only).
- **Observations:** same error pattern across conditions (inserted word, matra swaps); binarization added ~7 extra char errors on clean ruled writing. Pipeline ran 3× with no wiring faults (incl. one re-run after a CLI save bug — fixed, disclosed in `docs/PHASE4_REPORT.md`).
- **Files generated:** restored PNGs + hyp files above, `exp_log.csv` rows EXP-003a/b, `docs/phase4_*.png`.
- **Conclusion:** Phase 4 complete (image-in → transcription-out works repeatedly). Research-wise: first directional H3 evidence — on clean samples, heavier processing degrades slightly. n=1 page; full sweep across samples/conditions is Phase 8.
- **Next action:** Phase 5 (SQLite) → Phase 6 (API) per MVP order; then Phase 8 sweep.

### EXP-004 (a–q — baseline expansion to n=20)
- **Date:** 2026-09-17 ~14:00 IST
- **Objective:** transcribe 17 more MoDeTrans pages (original condition) to grow the baseline from n=3 to n=20.
- **Dataset:** MT-004..MT-020 (refs 73–203 chars).
- **Input:** original PNGs via `run_full_pipeline(..., "original")`.
- **Preprocessing:** none (original).
- **Model:** Qwen2.5-VL-3B + Modi LoRA via Colab, pinned revisions (base 6628554…, adapter 5b9957d…).
- **Hardware:** Colab GPU (type unrecorded); first call cold (~150 s incl. load), warm calls 15–55 s.
- **Parameters:** official card prompt; `max_new_tokens=256`, greedy.
- **Result:** `experiments/results/EXP-004_*_hyp.txt`; per-sample metrics in `baseline_n20_metrics.{csv,json}` (includes EXP-002 rows).
- **CER:** range 0.099–0.567, mean 0.317 (n=20). Full table in `baseline_n20_metrics.csv`.
- **WER:** range 0.286–0.955, mean 0.688.
- **Observations:** substitutions dominate every sample (S≫D,I) — differs from the card's "deletions dominate (46%)" claim on their 204-example test set; at n=20 this is an observation, not a refutation. One SSL tunnel blip auto-recovered via new client retry (17/17 batch complete). No truncation observed up to 203-char refs (longest hyp 202 chars).
- **Files generated:** `EXP-004_*_hyp.txt`, `EXP-004_times.json`, `baseline_n20_metrics.csv/.json`, `exp_log.csv` rows EXP-004a–q, `docs/exp002_results.png` (older n=3 chart; n=20 chart pending).
- **Conclusion:** baseline is now n=20 with mean CER 0.317 — same ballpark as card's 0.328, with the mandatory train-overlap caveat. Baseline variance (0.099–0.567) remains the dominant signal.
- **Next action:** Phase 8 restoration sweep across the n=20 set (7 configs × 20 = 140 Colab calls — batch overnight or sample subset first).

### EXP-005
- **Date:** TO BE FILLED IN WHEN RUN
- **Objective:** TO BE FILLED IN
- **Dataset:** TO BE FILLED IN (which image(s))
- **Input:** TO BE FILLED IN
- **Preprocessing:** TO BE FILLED IN (config name + id)
- **Model:** TO BE FILLED IN (revision, quantization, local/Colab)
- **Hardware:** TO BE FILLED IN
- **Parameters:** TO BE FILLED IN (prompt, max_new_tokens, decoding)
- **Result:** TO BE FILLED IN (raw transcription text or reference to saved output file)
- **CER:** TO BE MEASURED (or "N/A — no ground truth available")
- **WER:** TO BE MEASURED (or "N/A — no ground truth available")
- **Observations:** TO BE FILLED IN
- **Files generated:** TO BE FILLED IN (paths under `experiments/results/`)
- **Conclusion:** TO BE FILLED IN
- **Next action:** TO BE FILLED IN

*(Duplicate this template for EXP-002, EXP-003, etc. as real experiments run. Do not pre-fill future entries with anticipated results.)*

---

## 12. CER

**Character Error Rate.** Formula:

```
CER = (S + D + I) / N
```
where, comparing the hypothesis (model output) against the reference (ground truth), at the character level:
- `S` = number of substitutions
- `D` = number of deletions
- `I` = number of insertions
- `N` = total number of characters in the reference

Computed via minimum edit distance (Levenshtein distance) between the two character sequences. A CER of 0 means a perfect match; a CER above 1.0 (100%) is possible if the hypothesis required more insertions than the reference has characters.

**Interpretation:** lower is better. CER is more granular than WER and is generally more informative for scripts/languages where word boundaries are ambiguous or where partial-character-level errors matter (relevant for a script like Modi/Devanagari with complex conjunct characters).

---

## 13. WER

**Word Error Rate.** Same formula as CER, but computed over whitespace/word-tokenized sequences instead of characters:

```
WER = (S + D + I) / N
```
where `S`, `D`, `I` are word-level substitutions/deletions/insertions, and `N` is the total word count in the reference.

**Interpretation:** lower is better. WER is coarser than CER — a single wrong character in an otherwise-correct word still counts as a full word error, so WER can look worse than CER suggests for languages with long/complex words, which is relevant for Devanagari output.

---

## 14. Results Tables

*Placeholders only. No fabricated numbers. Populate rows as real `EXP-XXX` entries produce data.*

### Ablation: Preprocessing Condition vs. CER/WER

| Condition | Image | CER | WER | Experiment ID |
|---|---|---|---|---|
| Original | MT-001 (MoDeTrans 1.jpg) | 0.171 | 0.381 | EXP-002a |
| Original | MT-002 (MoDeTrans 10.jpg) | 0.099 | 0.286 | EXP-002b |
| Original | MT-003 (MoDeTrans 1000.jpg) | 0.567 | 0.955 | EXP-002c |
| Original | mean (n=3) | 0.279 | 0.541 | EXP-002 |
| Original | mean (n=20, MT-001..MT-020) | 0.317 | 0.688 | EXP-002+004 |
| Grayscale | TBD | TBD | TBD | TBD |
| Denoised | TBD | TBD | TBD | TBD |
| Enhanced (CLAHE) | MT-002 (MoDeTrans 10.jpg) | 0.121 | 0.286 | EXP-003a |
| Binarized | MT-002 (MoDeTrans 10.jpg) | 0.176 | 0.286 | EXP-003b |
| Deskewed | TBD | TBD | TBD | TBD |
| Full restoration | TBD | TBD | TBD | TBD |

*No row in this table may be filled with an estimated or "expected" number — only a number that came from an actual computed CER/WER against a real reference transcription, cited by experiment ID.*

---

## 15. Ablation Study

*Narrative summary of the table in Section 14, written only once that table has real data. Until then, this section stays empty except for this note: no ablation study has been conducted yet.*

First data point (EXP-002, original condition only — not an ablation yet): per-sample CER spans 0.099–0.567 on 3 pages, i.e. the model's baseline variance across pages already exceeds any restoration effect we could plausibly measure without more samples. No condition comparison exists; the restoration sweep (Phase 8) is the next step.

Update (EXP-003, MT-002 only): original 0.099 → enhanced 0.121 → binarized 0.176, WER flat at 0.286. First directional evidence for H3 on a clean sample (heavier processing hurts slightly at char level); n=1 page, no generalization claimed.

Update (EXP-004, n=20 baseline): mean CER 0.317 / WER 0.688, range 0.099–0.567. Substitutions dominate every sample's error profile (S≫D,I) — an incorporates-observation difference from the adapter card's "deletions dominate (46%)" on their 204-example set; at n=20 with possible train overlap this is noted, not contested. Per-image numbers live in `experiments/results/baseline_n20_metrics.csv` (kept out of this table for readability). Baseline variance still dwarfs any restoration effect measured so far.

---

## 16. Degradation Robustness Study

*Optional/P2 per `PROJECT_GUIDE.md` Section 26 — attempt only if time and dataset diversity allow.*

Conditions to test, if pursued:
- Synthetic blur (e.g. Gaussian blur at a defined kernel size)
- Synthetic noise (e.g. added Gaussian or salt-and-pepper noise)
- Reduced contrast (simulated fading)
- Rotation/skew (simulated photography misalignment)
- Simulated background stains/degradation (if a reasonable synthetic method is available)

*No results recorded yet. If this study is not attempted due to time constraints, record that explicitly as a limitation (Section 20) rather than omitting mention of it entirely.*

---

## 17. Qualitative Analysis

*For each example, once available:*

```
### Example 1
Original:            [image reference, e.g. data/raw/sample1.jpg]
Restored:             [image reference, e.g. data/processed/sample1_full.png]
AI output:            [exact model output text]
Ground truth:         [exact reference text, or "not available"]
Verified output:      [exact human-corrected text, if verification was performed]
Observations:         [honest notes — what did the model get right/wrong, did restoration
                        visibly help or hurt, any surprising behavior]
```

*No examples recorded yet — populate once Phase 3/8 produce real model output on real images.*

### Example 1 (EXP-001, 2026-09-17)
Original:            `data/raw/sample_modi_page.png` (6×8 Modi character chart, 48 isolated glyphs)
Restored:             none — original image sent (no restoration condition yet)
AI output:            79-char Devanagari string in `experiments/results/EXP-001_transcription.json`, rendered in `docs/phase3_output_card.png`
Ground truth:         not available
Verified output:      none (no verification performed)
Observations:         character-spaced output matches chart-like input; 10 Devanagari digits present (possible look-alike substitutions, unconfirmed); no echo/loop; 73.6 s wall time incl. cold start.

### Example 2 (EXP-002b, CER 0.099 — near-perfect)
Image: `data/raw/mode_trans/MT-002.png` (MoDeTrans 10.jpg, 3-line Modi letter opening)
Reference (91 chars): expert transliteration in `data/evaluation/MT-002_ref.txt` ("अखंडित लक्ष्मी…" — full text in file)
AI output (95 chars): `experiments/results/EXP-002_MT-002_hyp.txt` — matches except small edits (one inserted word, सुभा→सुभेर-class matra swap, उपरी→उपरि, जाणो→मणो)
Observations: clean ruled handwriting transcribes almost perfectly; residual errors are single-matra/word insertions, the kind a reviewer fixes in seconds.

### Example 3 (EXP-002c, CER 0.567 — fluent hallucination)
Image: `data/raw/mode_trans/MT-003.png` (MoDeTrans 1000.jpg)
Reference (120 chars): a dispute/record passage ("देव सिद दडस…" — full text in file)
AI output (129 chars): grammatical Marathi letter-like text with largely different content ("देवसींपंपूर्व…" — full text in file)
Observations: the output READS fluently but does not SAY the same thing — the classic VLM failure mode and the strongest possible evidence for why human verification is mandatory (§19). Whether difficult handwriting triggered the confabulation is unconfirmed.

---

## 18. Failure Cases

**This section is important and must not be skipped or minimized.** Document real observed failures as they occur:

- Cases where restoration visibly hurt transcription (e.g. thresholding erased faint but genuine ink strokes).
- Cases where the model hallucinated plausible-looking but incorrect Devanagari text rather than indicating uncertainty.
- Characters or character combinations the model confused (e.g. visually similar Modi ligatures).
- Manuscript regions with genuinely ambiguous handwriting where even a human reader would struggle — note these separately from clear model errors, since they represent a different kind of limitation.
- Cases where background/border cleanup accidentally removed a portion of the actual text near the page edge.
- Any case where the model's output length/structure diverged oddly from the input (e.g. repeated phrases, truncation, refusal-like behavior).

*No failure cases recorded yet — this section must be updated honestly and specifically once real inference runs happen, even if it makes the results look less clean. A project with zero documented failure cases after real experimentation is a red flag for under-reporting, not a sign of a flawless system.*

Observed behaviors pending confirmation (EXP-001, NOT confirmed errors — no ground truth):
- 10 Devanagari digits in a 79-char output on a character-chart input: consistent with look-alike glyph substitution, but could also be correct if the chart contains numeral-like glyphs. Needs a labeled chart to resolve.
- Infrastructure (not model) failures actually hit this phase: local weight download stall (XET success ratio 0.23, `PHASE3_BLOCKER.md`); one transient ngrok `RemoteDisconnected` on `/health` that succeeded on immediate retry; Windows console crash printing Devanagari (fixed via safe-ascii printing). Recorded here because demo reliability depends on them.
- CONFIRMED model failure (EXP-002c/MT-003, CER 0.567): fluent-but-wrong hallucination — grammatical Marathi output with substantially different content from the reference (45 substitutions over 120 ref chars). No uncertainty signal; output looks as confident as the near-perfect MT-002. This is the human-verification justification case.

---

## 19. Human Verification

*Document why human verification is needed (draw on Section 18's failure cases once populated — this is the strongest evidence) and track real before/after examples.*

```
### Verification Example 1
AI transcription:        [exact text]
Human-corrected text:    [exact text]
Nature of corrections:   [e.g. "one character substitution," "reordered a clause,"
                           "corrected a hallucinated word not present in the source image"]
```

*No examples recorded yet.*

---

## 20. Limitations

*Append to, never silently remove from, this list as they become apparent. Known/likely limitations to track from the start, to be confirmed or refined with real detail as the project proceeds:*

- Small dataset size (record the real final count once known — likely single digits to low tens of images given the time budget).
- Possible reliance on non-historical or self-created test images if genuine historical samples were not obtainable in time (record honestly which was the case).
- Limited handwriting-style diversity (likely only one or a few "hands"/scribes represented).
- Hardware constraints (4GB VRAM) may have forced quantization or a Colab fallback, which could itself affect measured output relative to an unquantized/full-precision run — record which inference path was actually used for each experiment.
- Ground truth may itself be imperfect if produced under time pressure by someone without deep Modi-reading expertise — record who produced ground truth and their confidence level, if known.
- Model bias: Qwen2.5-VL-3B + this specific LoRA was trained on some particular distribution of Modi data (per its own model card) that may not represent the diversity of real historical manuscripts.
- Preprocessing parameter sensitivity: results reflect one chosen parameter setting per stage (e.g. one CLAHE clip limit), not an exhaustive parameter sweep — different parameter choices might change conclusions.
- **Confirmed 2026-09-17 (Phase 2):** n=1 image only; sample provenance/license unconfirmed; background-correction and line-segmentation stages not implemented (optional/P2); deskew untested on strongly skewed images; `full_restoration` output is non-binary due to deskew-after-binarize ordering (documented in Section 9); image metrics in this notebook are quality proxies, NOT transcription accuracy — no CER/WER claimed.
- **Confirmed 2026-09-17 (Phase 3/EXP-001):** the single sample is a 48-glyph character chart, NOT a continuous manuscript page — off-distribution for a document-trained adapter, so EXP-001 proves the pipeline runs, not that it reads real manuscripts well; no ground truth → qualitative only; Colab GPU type/VRAM/adapter-revision unrecorded; 73.6 s wall time includes cold-start (steady-state latency unknown); Colab session ephemerality means EXP-001 is re-runnable only while a matching runtime+tunnel exist — the saved JSON is the permanent record.
- **Confirmed 2026-09-17 (EXP-002):** scores on MoDeTrans-train-split rows may be optimistic (adapter trained on this split — possible train-test overlap); n=3 short texts (91–120 chars), not a generalization claim; mean CER 0.279 is same-ballpark as the card's 0.328 but NOT a comparison; restoration conditions untested — the core research question is still open.
- **Confirmed 2026-09-17 (EXP-004, n=20):** same train-overlap caveat at larger n; refs 73–203 chars — no truncation observed up to ~200 chars (longest hyp 202 chars), behavior beyond that untested; substitution-dominant profile differs from card's deletion-dominant claim (observation only); warm-call latency 15–55 s, cold ~70–150 s.
- **Confirmed 2026-09-17 (Phase 4/EXP-003):** integration validated (3 consecutive runs, no wiring faults); restoration comparison exists for ONE clean page only — degraded-page behavior may differ arbitrarily; run-1 hyp was lost to a CLI save bug (fixed; disclosed, not hidden).
- **Confirmed 2026-09-17 (Phase 5):** schema via `create_all` (no migration tooling — acceptable single-user MVP scope, but schema changes later need manual handling); `ai_transcription` immutability enforced at repository level and covered by a dedicated test; LIKE search is substring-only (no FTS5 — P2).
- **Confirmed 2026-09-17 (Phase 6 + infra):** no auth (single-user scope — do not expose publicly); inference runs synchronously inside the upload request (20–70 s, no background jobs); no pagination; no upload dedupe (sha stored, unused); `/api/health` reports the local model flag only (misleading in Colab mode); transcription cache key excludes model revision (a Colab-side model update would serve stale cache silently); Colab tunnel is a single point of failure with no client retry (observed: SSL EOF mid-batch + ngrok 404 on stale URL); max_new_tokens=256 truncation on long pages untested; new samples (MT-004..MT-010) same train-split optimism as before.

---

## 21. Threats to Validity

- **Dataset bias:** a small, possibly non-representative sample of manuscripts/degradation types may not generalize to the broader population of historical Modi documents.
- **Sample size:** with likely single-digit-to-low-tens of images, statistical claims of significance are not appropriate — report descriptive results only, explicitly avoid words like "significantly" in the statistical sense unless an actual statistical test with adequate power was performed (unlikely at this scale — default to not claiming statistical significance).
- **Ground-truth reliability:** as above (Section 20).
- **Model dependency:** findings are specific to this base model + this LoRA adapter + this quantization setting; they may not generalize to other VLMs or other Modi-specific models.
- **Preprocessing selection bias:** the specific restoration configs tested were chosen by the project team based on common OCR-preprocessing practice, not an exhaustive search — other configurations might perform differently.
- **Generalization:** conclusions should be scoped explicitly to "under these specific experimental conditions," not stated as general truths about VLM+restoration interactions.

---

## 22. Final Research Paper Structure

*For each section below: what eventually needs to go there. Do not fill in actual content until real results exist — this is a structural skeleton for the eventual paper, referencing the notebook sections above where that content will come from.*

1. **Abstract** — problem, gap, method, experiment, results, contribution (see Section 23's framework). Write last.
2. **Keywords** — Modi script, digital preservation, vision-language models, OCR/HTR, image restoration, LoRA, historical manuscripts.
3. **Introduction** — draws from Section 3 (Problem Statement) of `PROJECT_GUIDE.md` and Section 5 (Background) above.
4. **Problem Statement** — as above.
5. **Related Work** — draws from Section 6 above (must be populated with real citations before this section can be written).
6. **Dataset** — draws from Section 7 above.
7. **Methodology** — draws from Sections 9–10 above (restoration pipeline + experimental design).
8. **Restoration Pipeline** — draws from Section 9 above and `PROJECT_GUIDE.md` Section 12.
9. **Vision-Language Transcription** — draws from Section 8 above and `PROJECT_GUIDE.md` Section 13.
10. **Experimental Setup** — draws from Section 10 above.
11. **Evaluation Metrics** — draws from Sections 12–13 above.
12. **Results** — draws from Section 14 above (must have real data).
13. **Ablation Study** — draws from Section 15 above.
14. **Robustness Study** — draws from Section 16 above (if attempted).
15. **Human Verification** — draws from Section 19 above.
16. **Discussion** — answers the questions in Section 25 below, grounded in actual results.
17. **Limitations** — draws from Section 20 above.
18. **Future Work** — draws from `PROJECT_GUIDE.md` Section 30.
19. **Conclusion** — summary, restating the research question (Section 2) and the actual (not hoped-for) answer found.
20. **References** — only real, checked citations from Section 6.

---

## 23. Abstract Drafting Framework

```
Problem      → [1-2 sentences on why Modi manuscript digitization is hard]
Gap          → [1 sentence on what wasn't previously known/tested — pending
                Section 6's literature review confirming this gap is real]
Method       → [1-2 sentences: LipiLens pipeline + the restoration-comparison
                experiment design]
Experiment   → [1 sentence: what was actually run — N images, M conditions]
Results      → [1-2 sentences, using real numbers only, e.g.:
                "[X% reduction in CER]" — DO NOT fill this in until Section 14
                has real data]
Contribution → [1 sentence on the software + the empirical finding]
```

**Do not fabricate the results sentence.** Leave the bracketed placeholder exactly as shown until Section 14 has real numbers to draw from.

---

## 24. Results Narrative Template

*Sentence templates only — fill in blanks with real numbers from Section 14 once available, never before.*

> "Compared with the unprocessed baseline, the ____ preprocessing strategy [reduced / increased] CER from ____ to ____, representing a ____% relative [improvement / degradation]."

> "Across the ____ manuscript images tested, the ____ condition produced the [lowest / highest] mean CER (____), while the ____ condition produced the [lowest / highest] mean WER (____)."

> "Binarization [improved / did not improve / had a mixed effect on] transcription accuracy, [helping / hurting] on ____ of the ____ images tested, most notably [helping/hurting] in cases of ____."

---

## 25. Discussion Questions

*The final Discussion section (Section 22 item 16) should answer these, grounded in real results — not speculated on in advance:*

- Which preprocessing stage mattered most, and was its effect consistent across images or highly variable?
- Did enhancement (CLAHE/contrast) always improve recognition, or were there exceptions, and what characterized them?
- When did binarization hurt, specifically — what visual characteristics of the source image predicted this?
- How sensitive was transcription accuracy to degradation severity (if the robustness study, Section 16, was attempted)?
- Did the model benefit more from contrast correction or from denoising, or were these roughly comparable?
- What kinds of Modi characters or constructs remained difficult regardless of preprocessing?
- How much did human verification actually change the final output, quantitatively (e.g. average number of character-level corrections per manuscript) and qualitatively (what kinds of errors were caught)?

---

## 26. Publication Strategy

Publication quality — if pursued beyond this course project — depends on: genuine novelty (confirmed via a real literature review, Section 6), experimental rigor appropriate to the claimed scope, sufficient data to support the claims made, reproducibility (this notebook's discipline is exactly what supports that), clear writing, and ethical, honest reporting including limitations and failure cases.

**This project does not guarantee, claim, or imply any journal or venue acceptance.** No claims about specific venues' current acceptance rates, indexing status, or review timelines should be made without checking current, real information at the time such a claim is needed — none is asserted here.

**Possible venues (to be researched later, not decided now):** *placeholder section — populate with real, checked options only if/when actually pursuing publication beyond the course submission.*

---

## 27. Research Integrity Rules

**This section is strict and non-negotiable, regardless of time pressure or how the project is otherwise going.**

**Never:**
- Fabricate measurements. If a number isn't the direct output of a real computation on real data, it does not go in this document.
- Invent citations. An empty Related Work table (Section 6) is honest; a populated one with unchecked or invented entries is academic misconduct.
- Invent dataset sizes. State the real count, however small.
- Invent model performance. If inference wasn't actually run, no output exists to report.
- Cherry-pick results without disclosure. If 5 images were tested and 2 showed the hypothesized effect while 3 didn't, report all 5 — not just the 2.
- Claim causality without evidence. At this sample size, findings are observational/descriptive, not causal proof.
- Claim novelty without a literature review. Section 4's novelty claim is explicitly conditional on Section 6 being genuinely completed.

**Always:**
- Record experiment IDs for every reported number (Section 11).
- Preserve raw results (the actual output files under `experiments/results/`, not just a summarized number in this document).
- Preserve the code/configuration used for each experiment (the `preprocessing_config_id` and model revision, per Section 10).
- Report failures (Section 18) as visibly as successes.
- Report limitations (Section 20) specifically, not vaguely.
- Distinguish hypothesis (Section 3) from result (Sections 14–19) — never let a hypothesis get quietly reworded into a conclusion without the data to back it.
- Distinguish existing work (Section 6, other people's contributions) from this project's own work (Section 4) — particularly important here since the Modi LoRA adapter itself is existing prior work, not something this project created.
