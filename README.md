# LipiLens

**AI-assisted transcription for historical Modi-script manuscripts, with human verification built in.**
LipiLens turns photographs of Modi-script pages into searchable, human-verified Devanagari records — and embeds an empirical study of how image restoration affects vision-language transcription accuracy.

`Python 3.12` · `Node 22+` · `FastAPI` · `React 19 + Vite` · `SQLite` · `MIT`

**Team report and deck:** [`docs/team_brief/TEAM_BRIEF_REPORT.md`](docs/team_brief/TEAM_BRIEF_REPORT.md) · [`docs/team_brief/PRESENTATION.md`](docs/team_brief/PRESENTATION.md)

---

## Contents

- [Why this exists](#why-this-exists)
- [How it works](#how-it-works)
- [What the application provides](#what-the-application-provides)
- [Evaluation summary](#evaluation-summary)
- [Architecture](#architecture)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Development](#development)
- [Repository layout](#repository-layout)
- [Scripts](#scripts)
- [Limitations](#limitations)
- [Credits](#credits)
- [License](#license)

---

## Why this exists

Modi was Maharashtra's administrative script from the 13th century until the mid-20th. Tens of millions of documents survive only in Modi; fluent readers are disappearing, pages are degrading, and no production OCR exists for the script. General vision-language models specialized with a LoRA adapter can draft transliterations — but a fluent draft can still be entirely wrong, so **the draft must never be treated as final output**. LipiLens therefore ships a human-in-the-loop product: the AI draft is immutable by design, and corrections are stored separately and become the searchable record.

```
photo → restore → transcribe → verify → archive → search
        (OpenCV)  (Qwen2.5-VL-3B  (human,     (SQLite)  (library UI)
                   + Modi LoRA)    explicit)
```

## How it works

1. **Restore** — seven OpenCV presets (denoise, binarize, deskew, segments). Restoration is CPU-only and instant, so any preset can be previewed live without ever touching the GPU. The measured optimum is the untouched scan (`original`); the UI defaults to it and tells the reviewer that restoration can affect recognition.
2. **Transcribe** — "Read with AI" issues a `202`, runs the model on a background thread, and the page polls `GET /api/manuscripts/{id}/progress` once a second for the stage, line count, and partial text. If transcription fails, the restored image is already archived and safe.
3. **Verify** — the AI draft is displayed read-only. The reviewer edits a separate **verified transcription**; the model output is never overwritten.
4. **Archive & search** — every record lands in a dashboard with source image, restored image, an interactive before/after compare slider, AI draft, verified text, status tracking, and full-text search.

## What the application provides

| Page (`/`) | Purpose |
|---|---|
| **Home** | Hero overview of the photograph → restore → AI-draft → verified pipeline, one-click sample pages that jump straight into transcription |
| **Transcribe** | Drop a scan, toggle fit/100% zoom, restore with any preset and compare original vs restored in place, watch the AI read stream line by line, correct it, save the verified text, archive |
| **Library** | Dashboard with record stats, full-text search, status and date-range filters, grid/list views, pagination; per-record detail view with the compare slider and side-by-side AI draft / human verification editors |
| **About** | The process, the design principles (immutable AI output, mandatory human review, measured preprocessing), and sample records |

Interface invariants: **immutable AI transcription** (`ai_transcription` is never rewritten; fixes go to `verified_transcription`) and **verification before archive prominence** (archiving happens at upload, but "verified" status and the searchable record require a human pass).

## Evaluation summary

All numbers come from real `restore → transcribe` runs scored by `scripts/evaluate_local.py`
against **MoDeTrans** pages (expert Devanagari references) with the CER/WER module in
`experiments/evaluation/`. Raw model outputs are kept per experiment, so any row can be
re-scored without GPU access. Run-to-run variance on 10 pages is ≈ **±0.05 CER**; treat
smaller differences as noise.

**Default configuration — whole page, `original`, no segmentation:**

| Arm | mean CER | accuracy | verbatim/ref |
|---|---|---|---|
| **whole page + `original`** (default) | **0.363** | **63.7 %** | 0.95 |
| + repetition guard, 512-token cap | 0.363 | 63.7 % | 0.95 |
| `enhanced` preprocessing | 0.367 | 63.3 % | 0.96 |
| 1.5× pre-upscale | 0.417 | 58.3 % | 1.00 |
| line segmentation | 0.623 | 37.7 % | 1.20 |

**Degraded-capture study** (`make_realistic.py` re-photographs authentic pages with
authentic ground truth at medium severity, **n = 23**, 92 model calls):

| Config | mean CER | accuracy | paired ΔCER | sign *p* | verdict |
|---|---|---|---|---|---|
| `original` | 0.348 | 65.2 % | — | — | baseline |
| `denoised` | 0.334 | 66.6 % | −0.014 | 0.68 | +1.4 pts, **not significant** |
| `binarized` | 0.440 | 56.0 % | +0.092 | 0.13 | **harms** |
| `enhanced` | 0.504 | 49.6 % | +0.156 | 0.52 | **harms badly** |

### Findings

1. **Line segmentation is harmful, not the fix it was proposed as** (`0.363 → 0.623`). The band
   detector cut ascenders and matras off every line and fed the model anonymous slivers at
   23:1–40:1 aspect ratios; `SEGMENT_LINES` now defaults to **off**.
2. **Preprocessing does not help even on dirty captures.** Contrast/gamma operations suppress
   the faint strokes that carry matras and the anusvāra (deletions rise 16.5 % → 37.8 % under
   `enhanced`). `original` stays the default for clean and degraded input alike.
3. **The ceiling is the model, not the pipeline.** The published adapter reports CER 0.328 over
   204 held-out pages; nothing in the input pipeline moves that by more than a couple of points.
4. **Tokens are not the constraint.** `max_pixels` is a ceiling, not a target: pages already
   under the budget are forwarded untouched, and raising it changes nothing (byte-identical
   outputs on 20/20 pages).
5. **Cross-page context is free; within-page structure is load-bearing.** Adding a whole extra
   page costs nothing (−0.001 CER) while cropping a page into line slivers costs +0.290 CER.
6. **Nothing outside the input pipeline helps.** Beam search (+0.004 CER at **4.9× latency**)
   and fp16 (+0.010) are noise; merging the QLoRA adapter into the NF4-quantised base is
   **catastrophic** (CER 0.316 → 1.064, worse on 20/20 pages) because PEFT re-quantizes the base
   on merge. `MERGE_LORA` must stay off.
7. **Always score against a reference.** An unscored run is not a result.

<details>
<summary><strong>Reproduce the evaluation</strong> (commands; stop the API server first — one GPU at a time)</summary>

```bash
# degraded-capture study (paired original / denoised / enhanced / binarized)
python scripts/evaluate_local.py --configs original denoised enhanced binarized \
    --images data/raw/realistic_medium --pages 23 --tag DEG-MED
python scripts/evaluate_local.py --report --configs original denoised enhanced binarized \
    --images data/raw/realistic_medium --pages 23 --tag DEG-MED   # re-score only, no GPU

# token-budget sweep and inference levers
python scripts/evaluate_local.py --pixels px512 px1280 px2048 --pages 20 --tag PIXELS
python scripts/evaluate_local.py --levers lever_base lever_beam4 lever_merge lever_fp16 \
    --pages 20 --tag LEVERS

# context-vs-structure probe (same page at native resolution, alone vs stacked)
python scripts/make_context_probe.py --out data/raw/ctx_single --mode single --pages 20
python scripts/make_context_probe.py --out data/raw/ctx_pair   --mode pair   --pages 20
python scripts/evaluate_local.py --images data/raw/ctx_single --arm noseg --pages 20 \
    --tag CTXSINGLE --max-pixels 1605632 --prompt-file experiments/prompts/context_probe.txt
python scripts/evaluate_local.py --images data/raw/ctx_pair --arm noseg --pages 20 \
    --tag CTXPAIR   --max-pixels 1605632 --prompt-file experiments/prompts/context_probe.txt
python scripts/score_context_probe.py          # splits stacked output, no GPU
```

- `--report` scores what is on disk and never calls the model; omit it to run missing pages.
- Paired comparisons must share the **identical** prompt; use `--prompt-file`, not `--prompt`.
- Raise `--max-pixels` for any arm feeding a larger composite, or the processor silently
  downsamples it and the arm stops measuring what it claims.
- Run multi-arm `--levers` groups in fresh processes; repeated ~85 s model reloads fragment a
  4 GB card and the last arm can spill to CPU.

</details>

## Architecture

| Layer | Implementation | Notes |
|---|---|---|
| Frontend | React 19 + Vite, four pages, single API client | No business logic; HTTP only |
| API | FastAPI, thin sync routes, OpenAPI at `/docs` | Static `/files` serving; CORS pinned to the Vite dev origin |
| Restoration | OpenCV, 7 named configs, stage-level modular | Pure functions; independently tested |
| Preview | `POST /api/manuscripts/preview` | Restoration only — no DB row, no model call (61–545 ms) |
| Segmentation | OpenCV line detection + upscale | No GPU; wraps any inference backend |
| Inference | `transcribe(image, prompt, on_progress)` | Local Qwen+LoRA or Colab GPU, selected by `INFERENCE_MODE` |
| Job progress | `GET /api/manuscripts/{id}/progress` | In-process registry; polled ~1 Hz during a read |
| Persistence | SQLite via SQLAlchemy, repository pattern | `ai_transcription` immutable; verification writes a separate column |
| Evaluation | Standalone CER/WER module | Operates on saved outputs, never live requests |

The two-act split is deliberate: restoration is instant and CPU-only, so only "Read with AI"
ever waits on the model. The draft is immutable; humans correct into a separate column; the
library makes the verified text the searchable record.

## Quickstart

Prerequisites: **Python 3.12**, **Node 22+**, and either a CUDA GPU (local mode) or a free
Google Colab account (Colab mode).

```bash
git clone https://github.com/ckhot18/lipilensv2.git
cd lipilensv2

python -m venv .venv
.\.venv\Scripts\activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
```

### Option A — local inference (CUDA GPU)

```bash
python scripts/download_model.py     # ~7.8 GB pinned weights; resumable, Ctrl+C safe
```

Downloads pinned revisions of `Qwen/Qwen2.5-VL-3B-Instruct` and the Modi LoRA into the
Hugging Face cache (skip-resumable, live progress, heartbeat log). Smoke-test with
`python scripts/smoke_test_model.py`.

Set `INFERENCE_MODE=local` in `.env`. Measured footprint: 4-bit NF4, **≈3.4 GB VRAM**
(RTX 2050 4 GB) and ≈4 GB RAM. First transcription loads the model lazily (~25 s, once); a
whole page then reads in ~15–60 s. Close other apps on low-RAM machines before the first load.

### Option B — Colab inference (no local GPU)

Open **`colab/lipilens_colab_server.ipynb`** in Colab with a **T4 GPU** runtime and run the
cells in order. The notebook installs pinned dependencies, starts the API in a background
thread, opens a tunnel (ngrok or Colab's built-in), and self-tests the round trip.

> Do **not** run `!python lipilens_colab_server.py` — it blocks the cell and nothing after it
> can execute. Keep the Colab tab open; closing it takes the model down.

```bash
cp .env.example .env        # set COLAB_ENDPOINT_URL + INFERENCE_MODE=colab
```

### Run the application

```bash
python -m uvicorn backend.main:app --port 8000   # API + docs at /docs
cd frontend
npm install
npm run dev                                      # UI at http://localhost:5173
```

The backend's CORS origins pin the Vite dev server to port **5173** — if you must run it
elsewhere, update `backend/config.py` accordingly.

### Verify

```bash
python -m pytest tests/ -q              # 104 tests
python -m pytest tests/test_api.py -q   # API subset
```

`GET /api/health` must report `"status": "ok"`. In local mode the model loads lazily, so a
fresh server reports `"model_loaded": false` until the first transcription — that is healthy,
not degraded. In Colab mode it probes the tunnel and reports `colab_reachable` /
`colab_model_loaded`; a missing or unreachable endpoint reports `"degraded"` with a reason.

## Configuration

Environment lives in `.env` (copy from `.env.example`; never commit it — it holds tunnel URLs).

| Variable | Default | Purpose |
|---|---|---|
| `INFERENCE_MODE` | `local` | `local` (Qwen+LoRA on this machine) or `colab` |
| `COLAB_ENDPOINT_URL` | — | Tunnel URL of the Colab inference server |
| `SEGMENT_LINES` | `0` | Line-by-line transcription. **Measured harmful (0.363 → 0.623); off by default** |
| `MAX_MODEL_PIXELS` | `1280*28*28` | Processor pixel budget; **must match** the Colab server. A ceiling, not a target |
| `REPETITION_PENALTY` | `1.05` | Greedy decoding loops on hard lines; `1.0` disables |
| `MAX_NEW_TOKENS` | `512` | Devanagari is ≈1 token/char; lines reach 254 tokens |
| `MODEL_UPSCALE` | `1.0` | Pre-upscale before the model; **measured harmful at 1.5** |
| `NUM_BEAMS` | `1` | Greedy; 4 beams measured as noise at 4.9× latency |
| `COMPUTE_DTYPE` | `bfloat16` | 4-bit compute dtype; `float16` measured as noise |
| `MERGE_LORA` | `0` | **Never enable.** Merging a QLoRA adapter into the NF4 base is catastrophic (0.316 → 1.064); kept only for reproducibility |

The Transcribe UI defaults to `original` — the measured optimum for clean and degraded input
alike — offers quick cards for the common choices, and exposes the full preset list for
experimentation, with a note that restoration can affect recognition.

## Development

```bash
cd frontend
npm run dev       # Vite dev server (port 5173)
npm run build     # production bundle -> frontend/dist
npm run lint      # oxlint
npm run preview   # preview the production build
```

Backend is pure Python under `backend/`; restoration, schemas, and the API layer are covered
by the 104 tests in `tests/`. `python scripts/refresh_library.py` prunes orphans and reseeds
the demo library.

## Repository layout

```
backend/         FastAPI app, routes, schemas, services, database
frontend/        React 19 + Vite app (pages, components, single API client)
colab/           Inference server + ready-to-run Colab notebook
experiments/     evaluation code, sweep scripts, results CSVs, figures
scripts/         model download, smoke tests, dataset prep, degradation + report generators
data/            downloaded datasets and generated degradation sets
demo_images/     demo set for the seeded library
docs/            team brief and presentation deck
research/        IEEE paper PDF + generator
presentation/    slide deck + generator
tests/           pytest suite (backend API + restoration)
```

## Scripts

| Script | Purpose |
|---|---|
| `scripts/download_model.py` | Pinned, resumable weight download into the HF cache |
| `scripts/smoke_test_model.py` | Isolated model check: load 4-bit, transcribe one page |
| `scripts/evaluate_local.py` | Accuracy harness: run pipeline arms against expert refs; re-score without GPU |
| `scripts/run_sweep.py` | Resume-safe 7-condition sweep with per-call progress log |
| `scripts/summarize_sweep.py` | Means, std, win/tie/loss per condition |
| `scripts/make_realistic.py` | Simulates photographic capture (aged paper, uneven light, stains, skew, noise, JPEG) with **authentic** ground truth |
| `scripts/make_degraded.py` | Older greyscale-only degradation set |
| `scripts/fetch_modetrans.py` | Pull pages + expert ground truth from Hugging Face |
| `scripts/seed_library.py` | Seed the demo library with real manuscripts |
| `scripts/refresh_library.py` | Prune orphans, reseed demos, seed verifications |

`make_realistic.py` keeps the authentic script and ground truth and simulates only the
capture. The output is a controlled degradation, not a real photograph, and is never presented
as one.

## Limitations

- **Single-user demo**: no auth, no rate limiting — do not expose publicly.
- Transcriptions run on an in-process background thread with an in-memory progress registry;
  a server restart loses the live progress view (not the archived result), and a
  multi-worker deployment would need the registry moved to the database.
- Whole-page transcription has no line denominator, so the progress bar intentionally omits a
  percentage for the reading step rather than inventing one.
- Colab sessions are ephemeral; the app degrades visibly when the tunnel is gone.
- Accuracy figures carry ≈±0.05 CER run-to-run variance; re-run `scripts/evaluate_local.py`
  before quoting individual numbers.
- The product is human-in-the-loop by design: at ~64 % character accuracy a human corrects
  roughly one character in three, which is exactly what the verification workflow exists for.
  The AI draft is never a finished reading.

## Credits

- Dataset and expert transliterations: **MoDeTrans** — H. Kausadikar, T. Kale, O. Susladkar,
  S. Mittal, IIT Roorkee (MIT), arXiv:2503.13060.
  <https://huggingface.co/datasets/historyHulk/MoDeTrans>
- Transcription adapter: **lgtk/qwen25vl-3b-modi-synth-lora** — Sachin Godse (lgtk).
  <https://huggingface.co/lgtk/qwen25vl-3b-modi-synth-lora>
- Base model: **Qwen2.5-VL-3B-Instruct** — Qwen Team (Apache-2.0).
  <https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct>

The pipeline, application, evaluation, and findings are this project's work; the model weights
and dataset belong to their authors, cited above.

## License

[MIT](LICENSE) — © 2026 Chirayu Khot
