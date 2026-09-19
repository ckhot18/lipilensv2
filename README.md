# LipiLens

AI-assisted transcription pipeline for historical Modi-script manuscripts,
with an embedded empirical study on how image restoration affects
vision-language transcription accuracy.

```
photo ──► restore ──► transcribe ──► verify ──► archive ──► search
           (OpenCV)   (Qwen2.5-VL-3B   (human,      (SQLite)
                       + Modi LoRA)    explicit)
```

## Problem

Modi was Maharashtra's administrative script from the 13th century until the
mid-20th. Tens of millions of documents survive only in Modi; fluent readers
are disappearing, pages are degrading, and no production OCR exists for the
script. General VLMs with LoRA specialization can draft transliterations, but
a fluent draft can be entirely wrong — so the draft must never be treated as
output.

## Architecture

| Layer | Implementation | Notes |
|---|---|---|
| Frontend | React + Vite (Transcribe / Library / About) | No business logic; talks HTTP only |
| API | FastAPI, thin routes, OpenAPI at `/docs` | Sync handlers (threadpool); static `/files` serving |
| Restoration | OpenCV, 7 named configs, stage-level modular | Pure functions; independently tested |
| Inference | `transcribe(image, prompt)` interface | Local Qwen+LoRA or Colab GPU endpoint via `INFERENCE_MODE` |
| Persistence | SQLite via SQLAlchemy, repository pattern | `ai_transcription` immutable; verification writes a separate column |
| Evaluation | Standalone CER/WER module | Operates on saved outputs, never live requests |

## Restoration conditions

Seven cumulative configs, from no-op control to full pipeline:

![All seven preprocessing outputs for one page](docs/phase2_comparison_grid.png)

`original` · `grayscale` · `denoised` (non-local-means) · `enhanced` (CLAHE) ·
`binarized` (Otsu) · `deskewed` (Hough) · `full_restoration` (all stages)

## Measured results

50 real MoDeTrans pages (IIT Roorkee, MIT) with expert Devanagari references;
Qwen2.5-VL-3B + Modi LoRA (pinned revisions), official prompt, greedy
decoding. Baseline (original images): **mean CER 0.304, range 0.026–0.912.**
140-call sweep over 7 conditions × 20 pages:

![Mean CER/WER per condition](docs/sweep_means.png)

| Condition | Mean CER | Pages worse than original |
|---|---|---|
| original | 0.317 | — |
| grayscale | 0.317 | 0/20 (exact no-op control) |
| denoised | 0.321 | 11/20 |
| enhanced | 0.328 | 10/20 |
| deskewed | 0.332 | 8/20 |
| binarized | 0.355 | **17/20** |
| full restoration | 0.359 | **14/20 (worst overall)** |

Conclusion: on clean historical pages, send the original to the model.
Binarization destroys faint-stroke detail the VLM uses; stacking neutral
stages compounds into harm. Descriptive statistics (n=20); possible
train-split overlap disclosed in the paper. Full per-sample data:
`experiments/results/sweep_metrics.csv`. Formal write-up:
`research/lipilens_paper.pdf`.

## Quickstart

Prerequisites: Python 3.12, Node 22+, a free Google Colab account (GPU).

```bash
git clone https://github.com/<you>/lipilensv2.git
cd lipilensv2

python -m venv .venv && .\.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # set COLAB_ENDPOINT_URL + INFERENCE_MODE=colab
```

Serve the model (one time, ~5 min): open `colab/lipilens_colab_server.py`
in a Colab GPU notebook, run all cells, expose port 8000 via ngrok, paste the
URL into `.env`. (Local-GPU path: `python scripts/download_model.py`, then
`INFERENCE_MODE=local` — requires ~6 GB VRAM and a long first download.)

```bash
python -m uvicorn backend.main:app --port 8000   # API + docs at /docs
cd frontend && npm install && npm run dev        # UI at localhost:5173
```

Verify the install: `python -m pytest tests/ -q` (50 tests), health at
`GET /api/health` (probes Colab reachability in colab mode).

## Repository layout

```
backend/         FastAPI app, routes, schemas, services, database
frontend/src/    React pages + single API client
colab/           GPU inference server (runs in Colab, not locally)
experiments/     evaluation code, sweep scripts, results CSVs, figures
scripts/         smoke tests, pipeline CLI, dataset fetch, report generators
showcase/        50 demo images (git-tracked)
research/        IEEE paper PDF + generator
presentation/    slide deck + generator
```

## Limitations

Single-user, no auth — do not expose publicly. Inference runs synchronously
(20–70 s per upload). Colab-dependent; sessions are ephemeral. Stats are
descriptive; clean short pages only. See the paper §VII for the full list.

## Credits

- Dataset and expert transliterations: **MoDeTrans** — H. Kausadikar, T. Kale,
  O. Susladkar, S. Mittal, IIT Roorkee (MIT License), arXiv:2503.13060.
  https://huggingface.co/datasets/historyHulk/MoDeTrans
- Transcription adapter: **lgtk/qwen25vl-3b-modi-synth-lora** — Sachin Godse
  (lgtk). https://huggingface.co/lgtk/qwen25vl-3b-modi-synth-lora
- Base model: **Qwen2.5-VL-3B-Instruct** — Qwen Team (Apache-2.0).
  https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct

Pipeline, application, evaluation, and findings are this project's work; the
model weights and dataset are their authors' — cited above.
