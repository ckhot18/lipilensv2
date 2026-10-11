# LipiLens

AI-assisted transcription pipeline for historical Modi-script manuscripts,
with an embedded empirical study on how image restoration affects
vision-language transcription accuracy.

```
photo -> restore -> segment -> transcribe -> verify -> archive -> search
        (OpenCV)   (OpenCV)   (Qwen2.5-VL-3B  (human,       (SQLite)
                                + Modi LoRA)    explicit)
```

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
`DEG-MED` (medium-severity captures, 40 calls).

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

**2. Preprocessing earns a little on dirty captures, and loses on clean ones.**

`make_realistic.py` re-photographs authentic pages (paper tone, uneven
lighting, foxing, skew, JPEG artefacts) with authentic ground truth. At medium
severity, 10 pages:

| Config | mean CER | accuracy | verdict |
|---|---|---|---|
| `original` | 0.399 | 60.1% | on dirty input the untouched capture is 2.3 pts worse |
| `denoised` | 0.378 | 62.2% | small gain |
| **`enhanced`** | **0.376** | **62.4%** | small gain, inside the noise band |
| `binarized` | 0.433 | 56.7% | **HARMS**, confirmed on dirty input too |

So the product thesis is directionally right and small: cleaning helps a dirty
scan by ~2 points and costs ~0.4 on a clean one. **Binarization loses
everywhere** and should not be reachable from the default UI path.

**3. The ceiling is the model, not the pipeline.** The published adapter
reports CER **0.328** over 204 held-out pages, with only 21% of examples below
0.20 and 53% in the 0.20-0.40 band. It was developed on an 8.5 GB RTX 5060 and
recommends >=6 GB; this runs on a 4 GB RTX 2050, which the evaluation harness
shows sitting at ~3.9 GB of 4 GB during inference. Holding 75-80% accuracy
*on average* is not reachable with a 3B model at this VRAM, and no
preprocessing change moves it by more than a couple of points.

**4. Always score against a reference.** 8 of the 18 local transcriptions in
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
python scripts/evaluate_local.py --configs original denoised enhanced \
    --images data/raw/realistic_medium --pages 10 --tag DEG-MED
python scripts/evaluate_local.py --report --configs original denoised enhanced \
    --images data/raw/realistic_medium --tag DEG-MED      # re-score, no GPU
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `INFERENCE_MODE` | `local` | `local` (Qwen+LoRA on this machine) or `colab` |
| `COLAB_ENDPOINT_URL` | - | Tunnel URL of the Colab inference server |
| `SEGMENT_LINES` | `0` | Line-by-line transcription. **Measured harmful (CER 0.363 -> 0.623); off by default.** |
| `MAX_MODEL_PIXELS` | `1280*28*28` | Processor pixel budget; **must match** the Colab server |
| `REPETITION_PENALTY` | `1.05` | Greedy decoding loops on hard lines. `1.0` disables. |
| `MAX_NEW_TOKENS` | `512` | Devanagari is ~1 token/char; lines reach 254 tokens |
| `MODEL_UPSCALE` | `1.0` | Pre-upscale before the model. **Measured harmful at 1.5.** |

Only `original` and `enhanced` are worth shipping in the UI. `binarized` and
`full_restoration` measured worse in every condition tested.

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
