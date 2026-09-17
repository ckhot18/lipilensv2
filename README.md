# LipiLens — AI-assisted Modi manuscript transcription

LipiLens takes a photographed/scanned **Modi Lipi** manuscript page, restores it
with OpenCV, drafts a Devanagari transcription with **Qwen2.5-VL-3B + a
Modi-specialized LoRA adapter** (`lgtk/qwen25vl-3b-modi-synth-lora`), and keeps
a human reviewer in the loop: AI drafts stay visibly drafts until explicitly
verified. It is also a small, honest research experiment on whether image
restoration helps or hurts VLM transcription.

**Status: working MVP.** Upload → restore → transcribe → verify → library →
search runs end-to-end (50/50 backend tests green, live Colab inference
proven). See `docs/` for phase reports and `RESEARCH_PAPER.md` for the lab
notebook (no fabricated numbers — every claim traces to an experiment file).

## Quickstart

Prereqs: Python 3.12 + venv, Node 22+, NVIDIA GPU optional (Colab works).

```powershell
# 1. Environment
cp .env.example .env          # then set COLAB_ENDPOINT_URL (see below)
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Inference (pick one)
#    a) Colab GPU (recommended): run colab/lipilens_colab_server.py in a
#       Colab GPU notebook, expose port 8000 (ngrok), paste the URL into .env
#       as COLAB_ENDPOINT_URL with INFERENCE_MODE=colab
#    b) Local GPU: needs ~6 GB VRAM + weight download;
#       scripts/download_model.py, then INFERENCE_MODE=local

# 3. Backend + frontend
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000
cd frontend; npm install; npm run dev   # http://localhost:5173
```

Health: `GET /api/health` (probes Colab reachability in colab mode).
API docs: `http://localhost:8000/docs`.

## API (thin routes; logic lives in services/)

| Method & path | What |
|---|---|
| `POST /api/manuscripts` (multipart: `file`, `title?`, `identifier?`, `config_name?`) | store original → restore → transcribe → archive; 503 on model failure (work preserved) |
| `GET /api/manuscripts?search=&verified=&limit=&offset=` | list/search (idempotent re-upload returns existing row) |
| `GET /api/manuscripts/{id}` | detail: original/restored URLs + transcription |
| `PUT /api/transcriptions/{id}/verify` `{verified_transcription}` | human verification (AI draft never touched) |
| `GET /files/raw/...`, `/files/processed/...` | manuscript images |

## Research in one paragraph

On 20 real MoDeTrans pages (IIT Roorkee, MIT), mean CER is **0.317** (range
0.099–0.567). Grayscale is a perfect no-op control; **binarization clearly
hurts** (17/20 losses) and the full pipeline is worst overall (0.359);
denoise/enhance/deskew hover at neutral. So on clean pages: default to the
original image. Details: `docs/PHASE8_REPORT.md`, figures in `docs/`,
per-sample data in `experiments/results/`.

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -q
.\.venv\Scripts\python.exe scripts\smoke_test_opencv.py
cd frontend; npm run build
```

## Limits (see paper §20 for all)

No auth (single-user, don't expose publicly); Colab-dependent inference;
synchronous 20–70 s uploads; n=20 descriptive stats only; possible
train-split overlap (adapter trained on MoDeTrans-train).

## Attribution

Dataset: `historyHulk/MoDeTrans` (Kausadikar et al., IIT Roorkee, MIT).
Adapter: `lgtk/qwen25vl-3b-modi-synth-lora`. Base model:
`Qwen/Qwen2.5-VL-3B-Instruct` (Apache-2.0).
