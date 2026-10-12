# LipiLens

AI-assisted transcription pipeline for historical Modi-script manuscripts,
with an embedded empirical study on how image restoration affects
vision-language transcription accuracy.

**Team working document and deck: [`docs/team_brief/TEAM_BRIEF_REPORT.md`](docs/team_brief/TEAM_BRIEF_REPORT.md) · [`docs/team_brief/PRESENTATION.md`](docs/team_brief/PRESENTATION.md)**

```
photo -> restore -> transcribe -> verify -> archive -> search
        (OpenCV)   (Qwen2.5-VL-3B  (human,       (SQLite)
                     + Modi LoRA)    explicit)
```

Line segmentation exists (`SEGMENT_LINES=1`) but is **off by default**: it was
added to raise the visual-token budget and measured worse (CER 0.363 -> 0.623).
See Measured results below.

## Problem

Modi was Maharashtra's administrative script from the 13th century until the
mid-20th. Tens of millions of documents survive only in Modi; fluent readers
are disappearing, pages are degrading, and no production OCR exists for the
script. General VLMs with LoRA specialization can draft transliterations, but
a fluent draft can be entirely wrong - so the draft must never be treated as
output.

## Measured results

All numbers below come from `scripts/evaluate_local.py`, which runs the real
restore -> transcribe path on MoDeTrans pages (IIT Roorkee / MIT, authentic
expert Devanagari references) and scores with `experiments/evaluation/`.
Raw hypotheses are kept per experiment so any row can be re-scored.

Run-to-run variance on 10 pages is about **±0.05 CER**, so treat differences
smaller than that as noise. Runs: `EVAL-01` (clean pages, 50 model calls),
`SEG20` (paired whole-page vs segmentation, 40 calls), `DEG-MED`
(medium-severity captures, 92 calls at n=23), `PIXELS` (token-budget sweep,
60 calls), `LEVERS` (inference levers, 80 calls), `CTX` (context-vs-structure
probe, 40 calls). The control arm of `LEVERS` reproduces the `PIXELS` arm
byte-for-byte on 20/20 pages, which is how the sweep is validated.

**1. The default configuration: whole page, `original`, no segmentation.**

| Arm | mean CER | accuracy | hyp/ref |
|---|---|---|---|
| **whole page + `original`** | **0.363** | **63.7%** | 0.95 |
| + repetition guard, 512-token cap | 0.363 | 63.7% | 0.95 |
| `enhanced` preprocessing | 0.367 | 63.3% | 0.96 |
| 1.5x pre-upscale | 0.417 | 58.3% | 1.00 |
| line segmentation | 0.623 | 37.7% | 1.20 |

Two of these contradict earlier beliefs in this repo and are worth stating
plainly:

- **Line segmentation is harmful, not the fix it was introduced as.** It was
  added to raise the visual-token budget (0.49 tokens/character for a whole
  page). Measured, it costs **0.363 -> 0.623**. The band detector was cutting
  ascenders and matras off every line and feeding the model anonymous slivers
  at 23:1-40:1; fixing that geometry did not rescue it (still 0.623).
  `SEGMENT_LINES` therefore now defaults to **off**.
- **Raising resolution by upscaling hurts** (0.363 -> 0.417). Note
  `max_pixels` is a ceiling, not a target: a 1268x463 page is already under
  the budget, so raising the budget alone buys nothing and only upscaling
  changes anything.
- The repetition guard and the larger token cap changed **nothing** on clean
  pages (byte-identical output). They are harmless, not a win.

**2. Preprocessing does not help even on dirty captures. (Corrected.)**

`make_realistic.py` re-photographs authentic pages (paper tone, uneven
lighting, foxing, skew, JPEG artefacts) with authentic ground truth. At medium
severity, **n=23** (92 calls):

| Config | mean CER | accuracy | paired ΔCER | sign *p* | verdict |
|---|---|---|---|---|---|
| `original` | 0.348 | 65.2% | — | — | baseline on dirty input |
| `denoised` | 0.334 | 66.6% | −0.014 | 0.68 | +1.4 pts, **not significant** |
| `binarized` | 0.440 | 56.0% | +0.092 | 0.13 | **harms** |
| **`enhanced`** | **0.504** | **49.6%** | **+0.156** | 0.52 | **harms badly** |

An earlier n=10 pass on this data suggested `enhanced` *gained* ~2 accuracy
points, and this README said so. **That claim was wrong and is retracted.** The
same 10 pages still favour it (−0.023); across all 23 it is strongly adverse
(+0.156). The n=10 number measured page selection, not configuration — exactly
the failure mode documented in finding 1, which we had not applied to our own
result before publishing it.

`enhanced` drives deletions from 16.5% to **37.8%**, the same failure signature
segmentation produces. Contrast and gamma operations on a faded capture suppress
the faint strokes carrying matras and the anusvāra. **Keep `original` as the
default for dirty input too; binarization must not be reachable from the
default UI path.**

**3. The ceiling is the model, not the pipeline.** The published adapter
reports CER **0.328** over 204 held-out pages, with only 21% of examples below
0.20 and 53% in the 0.20-0.40 band. It was developed on an 8.5 GB RTX 5060 and
recommends >=6 GB; this runs on a 4 GB RTX 2050, which the evaluation harness
shows sitting at ~3.9 GB of 4 GB during inference. Holding 75-80% accuracy
*on average* is not reachable with a 3B model at this VRAM, and no
preprocessing change moves it by more than a couple of points.

**4. Tokens are not the constraint - they saturate at native resolution.**
Sweeping the pixel
budget on an unscaled page (`PIXELS`, n=20): 518 → 765 tokens/char improves CER
0.344 → 0.316, but a budget of 2048 tokens/char produces output
**byte-identical** to 1280 on 20/20 pages, because the page is already under
both ceilings. `max_pixels` is a ceiling, not a target. Line segmentation
supplies ~6.6× more tokens per character than the whole page and scores 0.290
CER *worse*. Keep `SEGMENT_LINES=0`. (Finding 5 shows why.)

**5. Cross-page context is free; within-page structure is what breaks.** The
obvious follow-up to finding 4: if tokens are capped, does *more page context*
help? A controlled probe (`CTX`, n=20) gives the model page P at **full native
resolution in every arm**, same prompt, same pixel ceiling, varying only whether
P's neighbour is present:

| Arm | mean CER | accuracy |
|---|---|---|
| P alone | 0.325 | 67.5% |
| P above its neighbour (top page) | 0.324 | 67.6% |
| the neighbour, read second | 0.351 | 64.9% |
| P split into line slivers | 0.606 | 39.4% |

Paired deltas: neighbour present **−0.001** (worse 10 / better 9 / tie 1); same
page read second **+0.015** (95% CI [−0.021, +0.052], p = 0.65); segmentation
**+0.290** (p = 3.8 × 10⁻⁶).

So adding a whole extra page costs nothing, while cropping one page costs
0.290 CER. **This corrects our own explanation**: the reason to keep the page
whole is not that context is valuable — cross-page context is nearly worthless
*and* nearly free. It is that the page's internal geometry (baseline to ascenders
to matras) is load-bearing and 23:1 slivers delete it. A useful side effect:
two full pages fit in one call on this 4 GB card at no accuracy cost.

**6. Nothing outside the input pipeline helps.** Three standard levers, paired
against a control running the shipped settings (`LEVERS`, n=20): beam search
(+0.004 CER, 9 worse / 8 better, at **4.9× the latency**), fp16 (+0.010, no
speed gain), and merging the LoRA into the NF4-quantised base, which is
**catastrophic** — CER 1.064, worse on **20 of 20 pages**. The merge failure is
documented behaviour, not a bug: PEFT's `merge_adapter()` dequantizes the base,
adds the adapter, and re-quantizes, so a QLoRA adapter is merged into weights
it was never fitted against. Do not enable `MERGE_LORA`.

**7. Always score against a reference.** 8 of the 18 local transcriptions in
the archive had no ground truth and could not be scored at all. An unscored
run is not a result.

## Architecture

| Layer | Implementation | Notes |
|---|---|---|
| Frontend | React 19 + Vite | No business logic; talks HTTP only |
| API | FastAPI, thin routes, OpenAPI at `/docs` | Sync handlers (threadpool); static `/files` serving |
| Restoration | OpenCV, 7 named configs, stage-level modular | Pure functions; independently tested |
| Preview | `POST /api/manuscripts/preview` | Restoration only: no DB row, no model call, 61-545 ms |
| Segmentation | OpenCV line detection + upscale | No GPU; wraps any inference backend |
| Inference | `transcribe(image, prompt, on_progress)` interface | Local Qwen+LoRA or Colab GPU via `INFERENCE_MODE` |
| Job progress | `GET /api/manuscripts/{id}/progress` | In-process registry; polled once a second while a page is read |
| Persistence | SQLite via SQLAlchemy, repository pattern | `ai_transcription` immutable; verification writes a separate column |
| Evaluation | Standalone CER/WER module | Operates on saved outputs, never live requests |

The two-act split is deliberate: **restoration is CPU-only and instant, so it
never waits on the GPU.** The UI previews any pipeline live and only the
"Read with AI" action waits on the model. That action returns `202` at once
and runs the model on a background thread; the page then follows
`GET /api/manuscripts/{id}/progress` once a second, which reports the stage,
the line count and the text read so far. If transcription fails, the restored
image is already archived and safe.

## Quickstart

Prerequisites: Python 3.12, Node 22+, plus either a GPU (local mode) or a free
Google Colab account (Colab mode).

```bash
git clone https://github.com/ckhot18/lipilensv2.git
cd lipilensv2

python -m venv .venv && .\.venv\Scripts\activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
```

### 1a. Local mode (recommended with a GPU)

```bash
python scripts/download_model.py     # ~7.8 GB, resumable; Ctrl+C safe, rerun to continue
```

Downloads pinned revisions of `Qwen/Qwen2.5-VL-3B-Instruct` and the Modi LoRA
into the Hugging Face cache, with a live byte progress bar, a heartbeat every
30 s, and a `download_progress.log` beside the cache. Already-cached files are
skipped, so rerunning is cheap. Smoke-test with
`python scripts/smoke_test_model.py`.

Then set `INFERENCE_MODE=local` in `.env`. Measured footprint: 4-bit NF4,
**~3.4 GB VRAM** on an RTX 2050 (4 GB) and ~4 GB RAM. First transcription loads
the model lazily (~25 s, one time); a page with line segmentation costs ~1 call
per line (~10-15 s each), so the first page takes ~2-3 min and later pages
~15-60 s. On low-RAM machines, close other apps before the first load.

### 1b. Colab mode (no local GPU)

Open **`colab/lipilens_colab_server.ipynb`** in Colab with a **T4 GPU** runtime
and run the cells in order. It installs pinned dependencies, starts the API in
a background thread, opens a tunnel (ngrok, or Colab's built-in one with no
signup), and self-tests the round trip before you leave the browser.

Do **not** run `!python lipilens_colab_server.py` - it blocks the cell and
nothing after it can execute.

```bash
cp .env.example .env        # set COLAB_ENDPOINT_URL + INFERENCE_MODE=colab
```

Keep the Colab tab open. Closing it takes the model down and the app falls back
to degraded.

### 2. Run the app

```bash
python -m uvicorn backend.main:app --port 8000   # API + docs at /docs
cd frontend && npm install && npm run dev        # UI at localhost:5173
```

Verify: `python -m pytest tests/ -q` (93 tests) and `GET /api/health`, which
must report `"status": "ok"`. In local mode the model loads lazily, so a fresh
server reports `"model_loaded": false` until the first transcription - that is
healthy, not degraded. `model_loaded: true` after a transcription confirms the
round trip. In colab mode it probes the tunnel and reports `colab_reachable` /
`colab_model_loaded`; if the endpoint is missing, unreachable, or the model is
down, it reports `"degraded"` with a `reason`.

**One GPU at a time.** The API server keeps the model resident, so a second
process loading the same 3B model exhausts the 4 GB card and kills the CUDA
context mid-run. Stop the server before any offline evaluation:

```bash
python scripts/evaluate_local.py --configs original denoised enhanced binarized \
    --images data/raw/realistic_medium --pages 23 --tag DEG-MED
python scripts/evaluate_local.py --report --configs original denoised enhanced binarized \
    --images data/raw/realistic_medium --pages 23 --tag DEG-MED   # re-score, no GPU

# token budget and inference levers
python scripts/evaluate_local.py --pixels px512 px1280 px2048 --pages 20 --tag PIXELS
python scripts/evaluate_local.py --levers lever_base lever_beam4 lever_merge lever_fp16 \
    --pages 20 --tag LEVERS

# context vs structure: same page at native resolution, alone vs stacked
python scripts/make_context_probe.py --out data/raw/ctx_single --mode single --pages 20
python scripts/make_context_probe.py --out data/raw/ctx_pair   --mode pair   --pages 20
python scripts/evaluate_local.py --images data/raw/ctx_single --arm noseg --pages 20 \
    --tag CTXSINGLE --max-pixels 1605632 --prompt-file experiments/prompts/context_probe.txt
python scripts/evaluate_local.py --images data/raw/ctx_pair --arm noseg --pages 20 \
    --tag CTXPAIR   --max-pixels 1605632 --prompt-file experiments/prompts/context_probe.txt
python scripts/score_context_probe.py          # splits the stacked output, no GPU
```

`--report` means report-only: it scores what is on disk and never calls the
model. Omit it to actually run the missing pages. Run each `--levers` arm group
in a fresh process if it spans more than two arms — repeated 85 s model reloads
fragment a 4 GB card and the last arm can spill to CPU.

`--prompt` is mangled by shell argument splitting when it contains spaces; use
`--prompt-file`. Both arms of a paired comparison must carry the *identical*
prompt, or the comparison measures the wording rather than the image.
`--max-pixels` must be raised for any arm that feeds a larger composite, or the
processor silently downsamples it and the arm stops being the resolution it
claims to be.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `INFERENCE_MODE` | `local` | `local` (Qwen+LoRA on this machine) or `colab` |
| `COLAB_ENDPOINT_URL` | - | Tunnel URL of the Colab inference server |
| `SEGMENT_LINES` | `0` | Line-by-line transcription. **Measured harmful (CER 0.363 -> 0.623); off by default.** |
| `MAX_MODEL_PIXELS` | `1280*28*28` | Processor pixel budget; **must match** the Colab server. A ceiling, not a target: pages under it are forwarded untouched. |
| `REPETITION_PENALTY` | `1.05` | Greedy decoding loops on hard lines. `1.0` disables. |
| `MAX_NEW_TOKENS` | `512` | Devanagari is ~1 token/char; lines reach 254 tokens |
| `MODEL_UPSCALE` | `1.0` | Pre-upscale before the model. **Measured harmful at 1.5.** |
| `NUM_BEAMS` | `1` | Greedy. `4` measured as noise at 4.9x the latency. |
| `COMPUTE_DTYPE` | `bfloat16` | 4-bit compute dtype. `float16` measured as noise. |
| `MERGE_LORA` | `0` | **Never enable. Measured catastrophic: CER 0.316 -> 1.064, worse on 20/20 pages.** PEFT re-quantizes the NF4 base on merge, so a QLoRA adapter is folded into weights it was never fitted against. Kept only so the experiment is reproducible. |

Only `original` and `enhanced` are reachable in the UI. `binarized` and
`full_restoration` measured worse in every condition tested. Note that
`enhanced` is *also* the weakest preprocessing choice on damaged input
(finding 2), so `original` is the default for clean and dirty captures alike.

## Repository layout

```
backend/         FastAPI app, routes, schemas, services, database
frontend/src/    React pages + single API client
colab/           Inference server + ready-to-run Colab notebook
experiments/     evaluation code, sweep scripts, results CSVs, figures
scripts/         smoke tests, dataset prep, degradation + report generators
showcase/        50 demo images
research/        IEEE paper PDF + generator
presentation/    slide deck + generator
```

## Scripts

| Script | Purpose |
|---|---|
| `scripts/download_model.py` | Pinned, resumable weight download into the HF cache |
| `scripts/smoke_test_model.py` | Isolated model check: load 4-bit, transcribe one page |
| `scripts/evaluate_local.py` | Accuracy harness: run real pipeline arms against expert refs, re-score without GPU |
| `scripts/run_sweep.py` | Resume-safe 7-condition sweep; per-call progress log |
| `scripts/summarize_sweep.py` | Means, std, win/tie/loss per condition |
| `scripts/make_realistic.py` | Simulates photographic capture (aged paper, uneven light, stains, skew, noise, JPEG) |
| `scripts/make_degraded.py` | Older greyscale-only degradation set |
| `scripts/fetch_modetrans.py` | Pull pages + expert ground truth from Hugging Face |
| `scripts/refresh_library.py` | Prune orphans, reseed demos, seed verifications |

`make_realistic.py` keeps the **authentic** script and ground truth and only
simulates the capture. The output is a controlled degradation, not a real
photograph, and should never be presented as one.

## Limitations

- Single-user, no auth, no rate limiting - do not expose publicly.
- A transcription runs on an in-process background thread and reports progress
  from memory, so a server restart loses the live view (not the result).
- The progress registry is per-process, so running more than one worker process
  would need it moved into the database.
- Whole-page transcription has no line denominator, so the progress bar sweeps
  without a percentage for the reading step. That is deliberate: it will not
  invent a number it cannot know.
- Colab sessions are ephemeral.
- Accuracy figures are 10-page runs with about +/-0.05 CER of run-to-run
  variance. Treat smaller differences as noise, and re-run with
  `scripts/evaluate_local.py` before quoting any single number.
- The product is human-in-the-loop. At ~64% character accuracy a human is
  correcting roughly one character in three, which is what the verification
  workflow exists for. Do not present the draft as a finished reading.

## Credits

- Dataset and expert transliterations: **MoDeTrans** - H. Kausadikar, T. Kale,
  O. Susladkar, S. Mittal, IIT Roorkee (MIT License), arXiv:2503.13060.
  https://huggingface.co/datasets/historyHulk/MoDeTrans
- Transcription adapter: **lgtk/qwen25vl-3b-modi-synth-lora** - Sachin Godse
  (lgtk). https://huggingface.co/lgtk/qwen25vl-3b-modi-synth-lora
- Base model: **Qwen2.5-VL-3B-Instruct** - Qwen Team (Apache-2.0).
  https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct

Pipeline, application, evaluation, and findings are this project's work; the
model weights and dataset are their authors' - cited above.
