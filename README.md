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

## Two findings

**1. Restoration does not help, and binarization actively harms.** 50 real
MoDeTrans pages (IIT Roorkee, MIT) with expert Devanagari references; 140 calls
across 7 conditions. Sign test on win/tie/loss against the unmodified scan:

| Condition | mean CER | delta | W/T/L | p | verdict |
|---|---|---|---|---|---|
| original | 0.317 | - | - | - | baseline |
| grayscale | 0.317 | +0.0000 | 0/20/0 | 1.000 | perfect control |
| denoised | 0.321 | +0.0041 | 8/1/11 | 0.648 | no effect |
| enhanced | 0.328 | +0.0119 | 5/4/11 | 0.210 | no effect |
| deskewed | 0.332 | +0.0151 | 3/9/8 | 0.227 | no effect |
| **binarized** | **0.355** | **+0.0386** | **3/0/17** | **0.0026** | **HARMS** |
| full_restoration | 0.359 | +0.0425 | 5/1/14 | 0.064 | borderline |

Binarization survives Bonferroni correction (0.0026 x 6 = 0.0156). The
practical takeaway: **default to `original`**; offer restoration as an option,
never as the default.

`grayscale` is a built-in control that ties 20/20 with means identical to four
decimals - and it genuinely alters the image (100% of pixels change). A no-op
that changes everything and changes nothing is what makes the rest credible.

**2. The real bottleneck was visual token budget, not preprocessing.** A page
arrives as 1268x463 = 587,084 px. With `max_pixels` at the old 512*28*28 the
processor downsampled it to 1048x382, leaving **128 merged visual tokens for a
page containing up to 262 characters - under 0.5 tokens per character.** Qwen
merges 28x28 patches 2x2, so one token covers 14x14 px; the model was being
shown glyphs smaller than its own feature extractor.

That is why restoration could not help: no amount of resampling or local
contrast adds information the input does not contain.

The fix is `backend/services/transcription/segment.py`: split the page into
text lines (horizontal ink projection, Otsu threshold), crop each to its ink
extent, and upscale to fill the pixel budget. Each line then gets the whole
budget instead of sharing it six ways.

| | whole page | per line |
|---|---|---|
| visual tokens | 128 | ~320 per line |
| tokens per character | **0.49** | **~7.3** |

Measured on the real corpus: MT-038 (CER 0.912) splits into 4 lines for a 6.8x
token gain; MT-003 (CER 0.567) into 6 lines for 9.7x. Segmentation is pure
OpenCV and costs **no GPU**. Disable with `SEGMENT_LINES=0` to reproduce the
old behaviour for comparison.

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

Verify: `python -m pytest tests/ -q` (84 tests) and `GET /api/health`, which
must report `"status": "ok"`. In local mode the model loads lazily, so a fresh
server reports `"model_loaded": false` until the first transcription - that is
healthy, not degraded. `model_loaded: true` after a transcription confirms the
round trip. In colab mode it probes the tunnel and reports `colab_reachable` /
`colab_model_loaded`; if the endpoint is missing, unreachable, or the model is
down, it reports `"degraded"` with a `reason`.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `INFERENCE_MODE` | `local` | `local` (Qwen+LoRA on this machine) or `colab` |
| `COLAB_ENDPOINT_URL` | - | Tunnel URL of the Colab inference server |
| `SEGMENT_LINES` | `1` | Transcribe line by line (the accuracy fix) |
| `MAX_MODEL_PIXELS` | `1280*28*28` | Processor pixel budget; **must match** the Colab server |

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
  from memory, so a server restart loses the live view (not the result) and a
  page still costs N model calls, raising wall-clock per page even though total
  output tokens fall.
- The progress registry is per-process, so running more than one worker process
  would need it moved into the database.
- Colab sessions are ephemeral.
- Descriptive statistics on clean, short pages; train-split overlap disclosed
  in the paper.
- The token-budget fix is implemented but the improved CER has not yet been
  re-measured across the full sweep. Run it with `SEGMENT_LINES=1` before
  quoting an accuracy figure.

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
