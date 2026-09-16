# LipiLens Research Paper Notebook

**Purpose of this document:** a living, append-only research notebook. It is not a polished paper draft. Every claim here must trace to an actual experiment, file, or observation. Placeholders are marked explicitly and must never be silently treated as results. See Section 27 (Research Integrity Rules) before writing anything in this file.

**How to use this file during the project:** append to Sections 0, 7, 8, 9, 11, 14–20 as work happens. Do not write the polished narrative sections (22–26) until real results exist to narrate.

---

## 0. Research Status

*Update this section every time something material changes. This is the fastest way for a future session (human or agent) to know where things actually stand.*

- **Research question:** defined (Section 2) — not yet answered.
- **Dataset status:** TO BE DETERMINED — depends on what real Modi manuscript images are actually obtained (see `FOR_DEV.md` Section 10).
- **Baseline status:** not yet run.
- **Preprocessing status:** pipeline design specified in `PROJECT_GUIDE.md` Section 12 — implementation status TO BE UPDATED here once Phase 2 completes.
- **Model status:** not yet confirmed working — see `PROJECT_GUIDE.md` Section 15 for the local-vs-Colab decision, to be recorded here once made.
- **Experiment status:** no experiments run yet.
- **Results status:** none yet — no numbers exist in this document until an `EXP-XXX` entry produces them.
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

- **Dataset name:** TO BE DETERMINED (informal collection, not a named public dataset unless one is actually used and cited).
- **Source:** TO BE DETERMINED — record exactly where each image came from (archive name/URL, or self-created if applicable) as it's added.
- **Number of images:** TO BE DETERMINED — record the real count, however small.
- **Ground-truth availability:** TO BE DETERMINED — record, per image, whether a real human-verified reference transcription exists.
- **Image properties:** TO BE DETERMINED — resolution, format, approximate condition/degradation level per image, recorded honestly.
- **Train/test split:** likely not applicable at this scale — this is an evaluation-only study, not model training. State explicitly if this is the case in the final write-up.
- **Licensing:** record the licensing/usage terms of any archival source used; do not redistribute copyrighted manuscript images beyond what's needed for this academic project without checking terms.
- **Limitations:** record honestly as they become apparent (e.g. small sample size, limited degradation diversity, uncertain provenance).

---

## 8. Model

*Fill in with real, confirmed values only — do not guess a version number.*

- **Base model:** Qwen2.5-VL-3B — exact revision/commit hash used: TO BE CONFIRMED AGAINST THE ACTUAL ENVIRONMENT.
- **Adapter:** `lgtk/qwen25vl-3b-modi-synth-lora` — exact revision/commit hash used: TO BE CONFIRMED AGAINST THE ACTUAL ENVIRONMENT.
- **Model version notes:** TO BE UPDATED once Phase 3 confirms what actually loads and runs.
- **Quantization:** TO BE CONFIRMED (e.g. "4-bit via bitsandbytes" or "none — ran on Colab at full/half precision") — record whichever was actually used, and if it changed between local and Colab, record both, noting which condition each experiment result corresponds to.
- **Inference configuration:** `max_new_tokens`, sampling vs. greedy decoding, temperature (if any) — TO BE RECORDED once Phase 3/8 determine sensible values empirically.
- **Hardware:** local — RTX 2050, 4GB VRAM, 8GB system RAM, Windows; OR Colab — TO BE RECORDED (GPU type actually allocated by Colab, which varies).
- **Memory behavior:** TO BE MEASURED — actual peak VRAM usage observed via `nvidia-smi` during a real inference call, recorded here once available.
- **Prompt format:** TO BE CONFIRMED AGAINST THE ACTUAL ENVIRONMENT — record the exact prompt text/template that was found to work, once determined per `PROJECT_GUIDE.md` Section 13.
- **Image resolution used at inference:** TO BE RECORDED — whatever resolution was actually fed to the model's processor.

---

## 9. Restoration Pipeline

*For each stage, document purpose/implementation/parameters (known now) and expected/observed effect and experiment ID (filled in as experiments run).*

| Stage | Purpose | Implementation | Parameters | Reason for inclusion | Expected effect | Observed effect | Experiment ID |
|---|---|---|---|---|---|---|---|
| Grayscale conversion | Normalize channels | `cv2.cvtColor(..., COLOR_BGR2GRAY)` | — | Required precursor for most other stages | Neutral (enabling step) | TO BE RECORDED | — |
| Denoising | Reduce scan/camera noise | `cv2.fastNlMeansDenoising` | `h` parameter TBD, tune empirically | Historical scans/photos often noisy | Improve legibility of fine strokes | TO BE RECORDED | — |
| CLAHE / contrast enhancement | Improve legibility of faded ink | `cv2.createCLAHE` | clip limit, tile grid size TBD | Faded ink is a common degradation mode | Improve model's ability to distinguish ink from background | TO BE RECORDED | — |
| Adaptive/Otsu thresholding | Binarization | `cv2.adaptiveThreshold` / `cv2.threshold(..., THRESH_OTSU)` | block size/C or auto-threshold TBD | Standard OCR preprocessing step | Uncertain — may help (clean separation) or hurt (destroy faint strokes); this is a central research question, not assumed | TO BE RECORDED | — |
| Background correction | Remove uneven illumination | TBD implementation | TBD | Uneven photography lighting is common | Improve downstream thresholding quality | TO BE RECORDED | — |
| Deskewing | Correct rotation | e.g. Hough-transform or minAreaRect-based angle detection + `cv2.warpAffine` | TBD | Manuscripts are rarely perfectly aligned when photographed | Improve model's ability to read consistent line orientation | TO BE RECORDED | — |

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

### EXP-001
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
| Original | TBD | TBD | TBD | TBD |
| Grayscale | TBD | TBD | TBD | TBD |
| Denoised | TBD | TBD | TBD | TBD |
| Enhanced (CLAHE) | TBD | TBD | TBD | TBD |
| Binarized | TBD | TBD | TBD | TBD |
| Deskewed | TBD | TBD | TBD | TBD |
| Full restoration | TBD | TBD | TBD | TBD |

*No row in this table may be filled with an estimated or "expected" number — only a number that came from an actual computed CER/WER against a real reference transcription, cited by experiment ID.*

---

## 15. Ablation Study

*Narrative summary of the table in Section 14, written only once that table has real data. Until then, this section stays empty except for this note: no ablation study has been conducted yet.*

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
