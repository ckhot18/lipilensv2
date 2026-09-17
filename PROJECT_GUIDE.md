# LipiLens Project Guide

**Status of this document:** SINGLE SOURCE OF TRUTH for architecture and implementation.
**Audience:** AI coding agents (Antigravity, Claude Code, etc.) and human developers.
**Rule for agents:** If something in this file conflicts with your assumptions, this file wins. If something is unknown, it is explicitly marked `VERIFY THIS DURING IMPLEMENTATION`, `TO BE MEASURED`, or `TO BE CONFIRMED AGAINST THE ACTUAL ENVIRONMENT` — do not fill these in with invented values. Stop and report instead of guessing.

---

## 1. Executive Summary

**LipiLens** is an AI-assisted digital preservation and transcription system for historical **Modi Lipi** manuscripts — a historical script used primarily for Marathi before Devanagari became dominant.

**What it solves:** Modi manuscripts are hard to read even for trained scholars, and there is no mature, accessible OCR for Modi script. LipiLens provides a pipeline that takes a photographed/scanned manuscript page, optionally restores/cleans the image, and uses a vision-language model (Qwen2.5-VL-3B + a Modi-specific LoRA adapter) to produce a draft Devanagari transcription. A human reviewer then corrects and verifies that draft. Both the AI draft and the human-verified version are archived, searchable, and traceable.

**What the MVP is:** A working, demonstrable, end-to-end pipeline: upload → restore → transcribe (AI) → human-correct → verify → archive → search. It does not need to be beautiful. It needs to actually run, on the student's actual hardware, on at least one real manuscript image, and produce a real (not fabricated) transcription and a real (not fabricated) restoration comparison.

**What the long-term vision is:** A general-purpose, research-backed Modi manuscript digitization tool that supports larger corpora, better models, confidence estimation, line-level transcription, translation, and archival integration — none of which is in scope for the 20–22 hour MVP. See Section 30.

This project has two deliverables that must both be real:
1. A working software system (Sections 6–19).
2. A genuine, small-scale research experiment about how image restoration affects VLM transcription accuracy (Section 20, and `RESEARCH_PAPER.md`).

---

## 2. Project Philosophy

- **AI-assisted, not AI-authoritative.** The model produces a draft. It is never treated as ground truth. Every screen and every database record must make it visually and structurally obvious which text came from the AI and which text was human-verified.
- **Preservation first.** The original uploaded image is never overwritten or deleted. Restoration produces a *new* derived image; the original stays intact on disk and in the database.
- **Human verification is a first-class workflow step**, not an afterthought. "Verified" is a real state, not a UI decoration.
- **Research-backed engineering.** The restoration pipeline is not just "make OCR nicer" — it is instrumented so that its effect on transcription quality can be measured and reported honestly, including when it makes things worse.
- **Reproducibility.** Every experiment logged in `RESEARCH_PAPER.md` must be re-runnable: same input image, same preprocessing config, same model version, same prompt.
- **Modular design.** Restoration, inference, database, and API are independent modules that can be tested in isolation and swapped without touching the others (this matters enormously given the Colab fallback risk — see Section 15).
- **Time-constrained development.** ~20–22 hours total. Every design decision in this document has already been filtered through "is this necessary for a working, honest, demonstrable MVP?" Anything that isn't survives only in Section 30 (Future Roadmap).

---

## 3. Problem Statement

Modi is a historic script used for writing Marathi (and some Konkani/Hindi administrative records) from roughly the 12th century until it was officially phased out in favor of Devanagari in the mid-20th century. Large numbers of historical documents — land records, correspondence, court records, personal papers — exist only in Modi script, and the number of people who can read Modi fluently is small and shrinking. Physical manuscripts are also frequently damaged: faded ink, foxing/staining, torn edges, uneven lighting from photography, skew from imperfect scanning, and bleed-through from the reverse side of the page.

There is no mature commodity OCR engine for Modi script (unlike Devanagari, which is well supported). Recent general-purpose vision-language models (VLMs) have shown some capability at few-shot / fine-tuned transliteration of low-resource historical scripts, and LoRA adapters allow specializing a general VLM for a narrow domain like Modi without full retraining.

The computational problem LipiLens addresses is two-fold:
1. **Engineering problem:** build a reliable pipeline from raw manuscript photo to reviewable Devanagari transcription, on consumer-grade hardware, with a human always in the loop.
2. **Research problem:** determine, empirically, whether and how classical image restoration (denoising, contrast enhancement, binarization, deskewing) helps or hurts a modern VLM's transcription accuracy on degraded historical documents — since applying "more" preprocessing is not obviously always better for a model trained on natural-looking images.

---

## 4. MVP Objective

By the end of ~20–22 hours of implementation time, the following must be TRUE and DEMONSTRABLE (not merely coded):

1. A user can upload a Modi manuscript image through the React frontend.
2. The backend stores the original image untouched.
3. The backend runs at least a minimal OpenCV restoration pipeline and stores the restored image.
4. The backend sends an image (original or restored, per configuration) to the Qwen2.5-VL-3B + Modi LoRA pipeline (local OR Colab fallback — see Section 15) and receives an actual model-generated Devanagari transcription string. **This must be a real inference call, not a mocked/hardcoded string**, at least once, on at least one real image, before the project is considered done.
5. The transcription is shown to the user, editable.
6. The user can mark a transcription as "verified," and the verified text is stored separately from the AI draft.
7. The manuscript (with both versions of the transcription) appears in "My Library" and is searchable.
8. At least one small, real, documented restoration-vs-transcription experiment exists with real (not fabricated) output logged in `RESEARCH_PAPER.md`, even if the sample size is tiny (n=1 or n=few is acceptable and must be disclosed as a limitation).

If item 4 cannot be achieved locally due to VRAM constraints, the Colab fallback (Section 15) must be used — the project is NOT done if local OOM errors are simply left unresolved with no fallback executed.

---

## 5. Non-Goals

These are explicitly OUT of scope for the MVP. An agent must not spend MVP hours on these unless all P0/P1 work (Section 26) is complete and time remains:

- Training a new foundation model or LoRA from scratch.
- Full automatic English translation of Modi/Devanagari text.
- Massive cloud infrastructure (Kubernetes, multi-service deployment, load balancing).
- Enterprise authentication, user accounts, roles/permissions.
- Complex document understanding beyond page-level transcription (e.g., layout analysis, table extraction).
- Elaborate, animation-heavy, pixel-perfect UI. The reference screenshot is a *vibe* reference, not a spec.
- Production-scale deployment, CI/CD pipelines, containerization (unless trivially useful and free — e.g., a single `docker-compose.yml` is acceptable as P3, never required).
- Support for scripts other than Modi → Devanagari.
- Line-level or word-level bounding-box transcription (page-level text output is sufficient for MVP).
- Multi-user concurrency handling, queuing systems, background job workers (a single synchronous/async request is fine for a demo).

---

## 6. System Architecture

```
                    ┌─────────────────────┐
                    │   React Frontend    │
                    │  (Transcribe /       │
                    │   Library / About)   │
                    └──────────┬──────────┘
                               │ HTTP (JSON, multipart upload)
                               ▼
                    ┌─────────────────────┐
                    │     FastAPI API     │
                    │  (routes → services) │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
      ┌────────────┐   ┌────────────────┐   ┌────────────┐
      │   OpenCV   │   │ Qwen2.5-VL-3B  │   │   SQLite   │
      │ Restoration│   │  + Modi LoRA   │   │   Archive  │
      │  Service   │   │  Inference Svc │   │  (via ORM  │
      │            │   │ (local OR      │   │  or raw    │
      │            │   │  Colab remote) │   │  sqlite3)  │
      └─────┬──────┘   └───────┬────────┘   └────────────┘
            │                  │
            └──────────┬───────┘
                       ▼
             ┌────────────────────┐
             │ Human Verification │
             │ (edit + confirm in  │
             │   frontend, PATCH   │
             │   endpoint in API)  │
             └─────────┬──────────┘
                       ▼
                Verified Archive
             (SQLite: transcriptions
              table, verified=true)
```

**Component responsibilities:**

- **React Frontend:** Presentation and interaction only. No business logic beyond form validation and display formatting. Talks to FastAPI exclusively over HTTP.
- **FastAPI API:** Orchestration layer. Receives requests, validates input, calls services in order, returns JSON. Route handlers must stay thin (see Section 10).
- **OpenCV Restoration Service:** Pure image-in, image(s)-out module. No knowledge of the database or the model. Testable with a standalone script and no server running.
- **Qwen2.5-VL-3B + Modi LoRA Inference Service:** Image-in, text-out module. Abstracted behind an interface so the *caller* doesn't care whether inference happens locally or via a remote Colab endpoint (Section 15). No knowledge of the database.
- **SQLite Archive:** Persistence layer for manuscripts, transcriptions, preprocessing configs, and verification state. Accessed only through the `database`/`services/archive` layer, never directly from routes.
- **Human Verification:** Not a separate service — a workflow enforced by the schema (separate `ai_transcription` and `verified_transcription` fields) and the frontend UX (an explicit "Mark as Verified" action that is never automatic).

**Dependency direction:** Frontend → API → Services → (OpenCV | Inference | Database). Services never call each other directly except through the API orchestration layer, which keeps each service independently testable.

---

## 7. End-to-End Workflow

```
User selects manuscript image file in "Transcribe" screen
        ↓
Frontend POSTs multipart/form-data to POST /api/manuscripts
        ↓
API: validate file (type, size, is it actually an image)
        ↓
API: save original image to data/raw/{manuscript_id}/original.<ext>
        ↓
API: create manuscript DB record (status = "uploaded")
        ↓
API: call restoration service with configured pipeline
        ↓
Restoration service: run stages, save intermediate + final restored
        image to data/processed/{manuscript_id}/restored.png
        ↓
API: update manuscript DB record (restored_image_path, status="restored")
        ↓
API: call transcription service with chosen image (original or restored,
        per config) + prompt
        ↓
Transcription service: run Qwen2.5-VL-3B + Modi LoRA inference
        (local or Colab fallback)
        ↓
API: create transcription DB record
        (ai_transcription = model output, verified_transcription = NULL,
         verification_status = "pending", model_name, model_version,
         preprocessing_config_id, timestamps)
        ↓
API returns manuscript + transcription JSON to frontend
        ↓
Frontend displays: original image | restored image | AI transcription
        (editable textarea)
        ↓
User edits text (optional) and clicks "Mark as Verified"
        ↓
Frontend PATCHes PUT /api/transcriptions/{id}/verify
        with { verified_transcription: <edited text> }
        ↓
API: update transcription DB record
        (verified_transcription = text, verification_status = "verified",
         verified_at = now())
        ↓
Manuscript now appears, fully verified, in "My Library"
        ↓
User can search library by title/identifier/text content
        ↓
GET /api/manuscripts?search=... returns matches
```

Every arrow above corresponds to a concrete function call or HTTP request — an agent implementing Phase 6 (Section 27) should treat this list as the literal call sequence to implement.

---

## 8. Repository Structure

```
lipilens/
│
├── PROJECT_GUIDE.md          # this file — architecture source of truth
├── FOR_DEV.md                # student's step-by-step operational manual
├── TO_SETUP_AI.md            # how to operate the coding agent
├── RESEARCH_PAPER.md         # living research notebook
├── README.md                 # short public-facing overview (write LAST)
├── .gitignore
├── requirements.txt
│
├── backend/
│   ├── main.py                # FastAPI app instantiation, CORS, router mounting
│   ├── config.py               # paths, constants, env-driven settings
│   ├── api/
│   │   ├── manuscripts.py      # /api/manuscripts routes
│   │   ├── transcriptions.py   # /api/transcriptions routes
│   │   └── health.py           # /api/health — used for smoke tests
│   ├── schemas/
│   │   ├── manuscript.py       # pydantic request/response models
│   │   └── transcription.py
│   ├── services/
│   │   ├── restoration/
│   │   │   ├── pipeline.py     # ordered stage runner
│   │   │   └── stages.py       # individual OpenCV operations
│   │   ├── transcription/
│   │   │   ├── inference.py    # abstract interface: transcribe(image) -> str
│   │   │   ├── local_qwen.py   # local Qwen+LoRA implementation
│   │   │   └── colab_client.py # fallback: HTTP client to a Colab endpoint
│   │   └── archive/
│   │       └── repository.py   # DB read/write functions
│   ├── database/
│   │   ├── models.py           # SQLAlchemy models OR raw schema.sql
│   │   ├── session.py          # engine/session setup
│   │   └── migrations/         # optional; even a single schema.sql is fine
│   ├── models/                 # (if using local model files) cached weights
│   │   └── README.md           # explains this dir is gitignored
│   └── utils/
│       ├── image_io.py
│       └── logging.py
│
├── frontend/
│   ├── src/
│   │   ├── pages/ (Transcribe.jsx, Library.jsx, About.jsx)
│   │   ├── components/
│   │   ├── api/ (client.js — fetch wrappers)
│   │   └── App.jsx
│   └── package.json
│
├── data/
│   ├── raw/                    # original uploaded manuscripts (gitignored, sample kept)
│   ├── processed/               # restored images
│   ├── evaluation/              # ground-truth text for CER/WER experiments
│   └── outputs/                 # experiment result artifacts (json/csv)
│
├── experiments/
│   ├── preprocessing/           # standalone scripts, one per experiment condition
│   ├── evaluation/               # CER/WER computation scripts
│   └── results/                  # experiment result tables (csv/json/png)
│
├── scripts/
│   ├── smoke_test_opencv.py
│   ├── smoke_test_model.py
│   └── seed_test_data.py
│
├── tests/
│   ├── test_restoration.py
│   ├── test_api.py
│   └── test_database.py
│
└── docs/
    └── architecture-diagram.png   # optional exported diagram for the paper/README
```

**Rationale for deviations from the prompt's suggested structure:** none of substance — this is the same structure, with explicit file-level detail added so an agent knows exactly what to create in each phase.

---

## 9. Technology Stack

| Technology | Role | Why chosen | Rejected alternatives |
|---|---|---|---|
| **FastAPI** | Backend API framework | Async-friendly, automatic OpenAPI docs (useful for manual testing during a time-crunched build), minimal boilerplate, pydantic validation built in | Flask (no async/validation out of the box), Django (too heavy for this scope) |
| **React** | Frontend framework | Required by project brief; component model fits Transcribe/Library/About screen split well | Vue/Svelte — not rejected for technical reasons, just not the brief |
| **SQLite** | Persistence | Zero-infrastructure, file-based, perfectly adequate for single-user demo scale, trivial to inspect/back up/reset | Postgres/Mongo/Firebase — unnecessary operational overhead for a 20-hour student project with one user |
| **OpenCV (cv2)** | Image restoration | Industry-standard, fast, CPU-only (doesn't compete with the GPU the model needs), well-documented primitives for exactly the operations needed (denoise, CLAHE, threshold, deskew) | Pillow alone (lacks advanced restoration ops), scikit-image (viable alternative, but OpenCV specified in brief and has better performance) |
| **Qwen2.5-VL-3B** | Base vision-language model | Small enough (3B) to be plausible on 4GB VRAM *with quantization*, strong general VLM baseline, open weights | Larger Qwen-VL variants (won't fit), other VLMs (no available Modi LoRA) |
| **`lgtk/qwen25vl-3b-modi-synth-lora`** | Modi-specialized adapter | Only known existing LoRA fine-tuned for Modi transcription at time of writing; PEFT-compatible | Training a custom adapter — explicitly a non-goal (Section 5), no time |
| **PEFT / Transformers** | Model loading & LoRA application | Standard HuggingFace stack, required to load base model + apply adapter | — |
| **bitsandbytes (conditionally)** | Quantization | Needed to fit a 3B VLM in 4GB VRAM; use 4-bit if compatible with the installed CUDA/Transformers/PEFT versions | Full precision (will not fit), other quantization libs — only introduce if bitsandbytes proves incompatible; **VERIFY THIS DURING IMPLEMENTATION** |
| **Google Colab (fallback)** | Remote inference | Free GPU access if local VRAM is insufficient; keeps rest of architecture unchanged (Section 15) | Paid cloud GPU (unnecessary cost/complexity for a student project) |

Do not add additional infrastructure/services beyond this table without a concrete, written reason in a commit message.

---

## 10. Backend Architecture

FastAPI app (`backend/main.py`) mounts three routers: `manuscripts`, `transcriptions`, `health`.

**Route handlers must be thin** — a route function should: parse/validate input (mostly done by pydantic automatically), call exactly one or two service functions, return a response model. No image processing, no SQL, no model-loading logic inside a route function.

Example shape (illustrative, not literal code to copy blindly):

```
POST /api/manuscripts
  -> parses UploadFile + optional metadata fields
  -> calls archive.create_manuscript(...)
  -> calls restoration.run_pipeline(...)
  -> calls archive.update_manuscript_restored(...)
  -> calls transcription.transcribe(...)
  -> calls archive.create_transcription(...)
  -> returns ManuscriptResponse

GET /api/manuscripts?search=&verified=
  -> calls archive.search_manuscripts(...)
  -> returns list[ManuscriptSummary]

GET /api/manuscripts/{id}
  -> calls archive.get_manuscript(...)
  -> returns ManuscriptDetail (includes transcription)

PUT /api/transcriptions/{id}/verify
  -> parses { verified_transcription: str }
  -> calls archive.verify_transcription(...)
  -> returns TranscriptionResponse

GET /api/health
  -> returns { status: "ok", model_loaded: bool }
```

**Separation of concerns:**
- `schemas/` — pydantic models only, no logic.
- `services/restoration/` — pure functions operating on image arrays/paths; no FastAPI imports.
- `services/transcription/` — a single abstract function `transcribe(image_path: str, prompt: str) -> str`, implemented by either `local_qwen.py` or `colab_client.py`, selected via `config.py` (e.g. an `INFERENCE_MODE` setting of `"local"` or `"colab"`). This abstraction is what makes Section 15's fallback painless.
- `services/archive/` — all SQL/ORM interaction lives here. Nothing outside this module touches the database directly.
- `database/` — schema definition and session/connection management only.

**Async note:** Model inference and heavy OpenCV work are CPU/GPU-bound, not I/O-bound. If using `async def` route handlers, either run blocking work in a thread pool (`fastapi.concurrency.run_in_threadpool` or `asyncio.to_thread`) or simply use synchronous `def` route handlers (FastAPI runs these in a threadpool automatically). For a single-user demo, synchronous handlers are simpler and acceptable — do not over-engineer this.

---

## 11. Frontend Architecture

Three pages, matching the brief:

**`Transcribe.jsx`**
- File upload input (image only, client-side type/size check as a first pass, but the API is the source of truth for validation).
- Preview of the selected image before upload.
- On submit: show a processing/loading state (this call can take a while due to model inference — a spinner with a message like "Restoring image and running transcription..." is sufficient; no need for granular progress).
- On success: display original image, restored image, and AI transcription in an editable text area, side by side or stacked (mobile-friendly stacking is fine).
- "Save" / "Mark as Verified" button that PATCHes the transcription and confirms success.

**`Library.jsx`**
- List of manuscripts (title, identifier, thumbnail, verification badge: "Verified" / "Pending Review").
- Search box that filters via the backend `?search=` query param (debounce input; don't fire a request per keystroke without at least a short delay).
- Clicking an item opens a detail view showing original, restored, AI transcription, and verified transcription (if present) — read-only unless the user explicitly re-enters edit mode.

**`About.jsx`**
- Static content: what LipiLens is, why it's AI-*assisted* (not authoritative), how human verification works, and a short note on the research angle. This page can be written last and does not need dynamic data.

**State management:** React's built-in `useState`/`useEffect` is sufficient. Do not introduce Redux/Zustand/React Query unless the agent judges, after Phase 7 begins, that manual fetch-and-state-management is becoming unmanageable — this is unlikely at this project's scale and should not be a default choice.

**API client:** a single `src/api/client.js` wrapping `fetch` calls to the FastAPI backend (base URL from an env var, e.g. `VITE_API_BASE_URL=http://localhost:8000`).

**Styling:** keep it simple — plain CSS or a lightweight utility approach (e.g. Tailwind, if the agent judges setup time is worth it). Visual polish is explicitly capped by Section 5 (Non-Goals) and must never be prioritized over pipeline correctness.

---

## 12. OpenCV Restoration Architecture

The pipeline is **modular and configurable** — a sequence of named, independently testable stages, not a monolithic function.

| Stage | Purpose | Mandatory? |
|---|---|---|
| 1. Image validation/inspection | Confirm readable image, report dimensions/format/basic quality stats | Mandatory |
| 2. Grayscale conversion | Normalize to single channel for downstream ops | Mandatory (if any restoration is applied) |
| 3. Denoising | Reduce scan/camera noise (e.g. `fastNlMeansDenoising`) | Configurable |
| 4. Contrast enhancement / CLAHE | Improve legibility of faded ink | Configurable |
| 5. Adaptive thresholding | Local binarization for uneven lighting | Configurable, experimental |
| 6. Otsu thresholding | Global binarization for even lighting | Configurable, experimental |
| 7. Binarization (generic) | Umbrella term for #5/#6 — pick one, not both, per run | Configurable |
| 8. Background correction | Remove uneven illumination before thresholding | Optional |
| 9. Border/background cleanup | Remove scanner borders/margins | Optional |
| 10. Deskewing | Correct rotation from imperfect photography/scanning | Configurable |
| 11. Line segmentation | Split page into text lines | Optional / P2, only if time remains — not required for page-level transcription |

**Do not force every manuscript through every stage.** The pipeline is driven by a config object (e.g. a `PreprocessingConfig` with boolean/enum flags per stage), and different configs are exactly what the research experiment (Section 20) compares. Example configs to implement for the experiment:

```
original            -> no processing at all
grayscale            -> stage 2 only
denoised             -> stages 2, 3
enhanced             -> stages 2, 3, 4
binarized            -> stages 2, 3, 4, 6 (or 5)
deskewed             -> stages 2, 10 (+ others as available)
full_restoration      -> stages 2, 3, 4, 6, 9, 10 (a reasonable "everything" pipeline)
```

**Intermediate outputs:** the pipeline function should be able to return (or optionally save) every intermediate image, not just the final one — this is required for both debugging and the qualitative analysis section of the paper.

**Independent testability:** `scripts/smoke_test_opencv.py` must run the pipeline on a sample image with zero dependency on FastAPI, the database, or the model, and save results to `data/outputs/` for visual inspection. This should be one of the very first things implemented (Phase 2) — it de-risks the least uncertain part of the project first, so time pressure later falls on the model integration, which is the genuinely uncertain part.

---

## 13. Qwen + Modi LoRA Architecture

**Conceptual relationship:**

```
   Qwen2.5-VL-3B (base model, pretrained, general vision-language)
                    +
   lgtk/qwen25vl-3b-modi-synth-lora (LoRA adapter, low-rank weight
   deltas specialized for Modi manuscript image -> Devanagari
   transcription, applied on top of specific base-model layers
   via PEFT)
                    =
   Modi-specialized inference model
```

- The **base model** provides general vision-language understanding (it can "see" an image and generate text conditioned on it, via its own image processor/tokenizer).
- The **LoRA adapter** is a small set of additional trained weights that, when merged/applied at inference time via the PEFT library, shift the base model's behavior toward the Modi-specific task it was fine-tuned on (image of Modi text → Devanagari transliteration/transcription).
- The **processor/tokenizer** used must match what the base model expects (Qwen2.5-VL ships its own `AutoProcessor` that handles both image preprocessing — resizing, normalization — and text tokenization/prompt templating). **Do not assume**, without checking, that a generic `CLIPImageProcessor` or similar will work — Qwen-VL has its own conventions.
- **Image input:** the model has its own expected input resolution/format handled by its processor. Do not hand-roll a separate resize step for the *model's* input unless the processor requires pre-resizing that OpenCV should do instead — **VERIFY THIS DURING IMPLEMENTATION** by reading the adapter's model card and the base model's processor config.
- **Generation:** standard `model.generate(...)` call with the processed image + a text prompt (e.g. "Transcribe this Modi manuscript into Devanagari script.") — the exact prompt format expected by this specific LoRA (chat template? plain instruction? special tokens?) must be read from the adapter's model card / any example usage code in its repository, not invented. **VERIFY THIS DURING IMPLEMENTATION.**
- **Output:** raw generated text, which should already be Devanagari (per the adapter's stated purpose) — post-process only to the extent needed (strip prompt echo, special tokens, whitespace).

**Mandatory agent action before writing inference code:** inspect the actual Hugging Face repository for `lgtk/qwen25vl-3b-modi-synth-lora` (model card, config files, any example/usage script) and the base `Qwen2.5-VL-3B` model card, and report back:
- expected PEFT/Transformers version compatibility,
- expected prompt format,
- expected image input handling,
- any stated hardware requirements or known quantization guidance.

Do not fabricate any of the above if the repository does not clearly state it — mark it `TO BE CONFIRMED AGAINST THE ACTUAL ENVIRONMENT` and determine it empirically via the smoke test (Phase 3).

---

## 14. Hardware Constraints

```
GPU:   NVIDIA RTX 2050
VRAM:  4 GB
RAM:   8 GB system memory
OS:    Windows
```

This is a **hard constraint**, not a suggestion. A 3B-parameter VLM at full FP16/FP32 precision will very likely not fit in 4GB VRAM alongside CUDA overhead and the image processor's memory needs. Memory-saving practices to apply, in rough order of first thing to try:

1. **4-bit or 8-bit quantization** via `bitsandbytes`, if compatible with the installed Transformers/PEFT/CUDA versions (**VERIFY THIS DURING IMPLEMENTATION** — bitsandbytes has historically had rougher Windows support than Linux; check current status rather than assuming).
2. **`torch_dtype=torch.float16`** (or `bfloat16` if supported) instead of default float32, even before quantization.
3. **`device_map="auto"`** or explicit CPU offload for parts of the model that don't fit, accepting slower inference in exchange for it running at all.
4. **Process one image at a time**, never batch, during both development and the demo.
5. **Free VRAM between test runs** (`torch.cuda.empty_cache()`, restart the Python process if fragmentation becomes an issue during iterative testing).
6. **Downscale input images** to the smallest resolution the model's processor will accept without destroying legible detail — large images consume disproportionate memory during image encoding.
7. **8 GB system RAM** also constrains: avoid loading multiple copies of model weights, avoid keeping large numbers of full-resolution images in memory at once during experiments (process images one at a time, write results to disk incrementally).

If, after applying (1)–(3), the model still does not load or produces `CUDA out of memory` on a single small test image, **stop trying local variations and move to the Colab fallback (Section 15)** rather than spending hours fighting VRAM. Time spent debugging OOM beyond a reasonable first attempt (roughly 1–2 hours, generously) is time better spent executing the fallback.

---

## 15. Local-vs-Colab Fallback

The architecture is designed so that **only `services/transcription/` changes** if local inference is infeasible. Everything else — OpenCV, FastAPI routes, database schema, frontend — is completely unaffected.

```
backend/services/transcription/inference.py
    defines: transcribe(image_path: str, prompt: str) -> TranscriptionResult

backend/services/transcription/local_qwen.py
    implements transcribe(...) by loading Qwen2.5-VL-3B + LoRA in-process
    and calling model.generate(...)

backend/services/transcription/colab_client.py
    implements transcribe(...) by:
      1. base64-encoding (or uploading) the image
      2. POSTing to a Colab-hosted FastAPI/Flask endpoint
         (a tiny separate script run inside a Colab notebook,
          exposed via ngrok or Colab's own tunneling)
      3. parsing the JSON response { "transcription": "..." }
      4. returning it in the same shape local_qwen.py would

config.py: INFERENCE_MODE = "local" | "colab"
    a single switch selects which implementation the API layer calls
```

**Decision procedure:**
1. Attempt local inference smoke test (Phase 3) first — it's free and, if it works, simpler for the demo (no network dependency, no Colab session management during the live demo).
2. If local inference fails to load or reliably OOMs on realistic images, set up the Colab notebook: load the same model+adapter there (Colab free tier typically offers substantially more VRAM), expose a minimal HTTP endpoint, and point `colab_client.py` at it.
3. **Regardless of which path is used, the rest of the system must not know or care.** This is the entire point of the `transcribe()` abstraction — verify this abstraction is respected in code review before Phase 6 is marked complete.
4. Document, honestly, in `RESEARCH_PAPER.md` Section 8 (Model) and Section 20 (Limitations), which path was actually used and why — this is a legitimate and expected finding to report, not something to hide.

**Colab session caveat for the live demo:** Colab sessions are ephemeral and disconnect after inactivity. If Colab fallback is used, the demo plan (Section 21 of `FOR_DEV.md`) must account for keeping the Colab session warm shortly before demoing, or falling back further to pre-recorded/pre-computed transcription results for the live demo while showing the real pipeline code.

---

## 16. Database Architecture

SQLite, accessed through a thin repository layer (`services/archive/repository.py`). Recommended schema (agent may add indices/columns as needed, but should not remove the verification-state separation, which is core to the project's philosophy):

**`manuscripts`**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| title | TEXT | user-provided or filename-derived |
| identifier | TEXT | optional catalog/accession number |
| author | TEXT | optional, often unknown for historical docs |
| date | TEXT | optional, free-text (historical dates are rarely ISO-clean) |
| source | TEXT | optional, e.g. archive/collection name |
| collection | TEXT | optional |
| location | TEXT | optional, physical location of original |
| notes | TEXT | optional free-text |
| original_image_path | TEXT | required, never overwritten |
| restored_image_path | TEXT | nullable until restoration runs |
| preprocessing_config_id | INTEGER FK | which config produced restored_image_path |
| status | TEXT | `uploaded` \| `restored` \| `transcribed` \| `verified` |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**`transcriptions`**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| manuscript_id | INTEGER FK | |
| ai_transcription | TEXT | raw model output, immutable once written |
| verified_transcription | TEXT | nullable until human verifies; this is what search should prioritize once present |
| model_name | TEXT | e.g. "Qwen2.5-VL-3B" |
| model_version | TEXT | e.g. adapter commit hash / revision, base model revision |
| inference_mode | TEXT | `local` \| `colab` — for research/debugging traceability |
| preprocessing_config_id | INTEGER FK | which image variant was actually sent to the model |
| verification_status | TEXT | `pending` \| `verified` |
| created_at | TIMESTAMP | |
| verified_at | TIMESTAMP | nullable |

**`preprocessing_configs`**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | e.g. "full_restoration", "grayscale_only" |
| config_json | TEXT | serialized stage flags/parameters, for exact reproducibility |
| created_at | TIMESTAMP | |

This third table exists specifically so that **every restoration run is reproducible** — a requirement of Section 20's research experiment, not just nice-to-have software design.

**Search:** for MVP, a simple `LIKE`-based search across `title`, `identifier`, and (COALESCE) `verified_transcription`/`ai_transcription` is sufficient. Full-text search (SQLite FTS5) is a reasonable P2 upgrade if time remains, not required.

---

## 17. Human Verification

**Lifecycle of a transcription:**

```
created (ai_transcription set, verified_transcription = NULL,
         verification_status = "pending")
        │
        ▼ (user opens it in the frontend, optionally edits the text)
        │
        ▼ (user clicks "Mark as Verified")
        │
verified (verified_transcription = <possibly-edited text>,
          verification_status = "verified", verified_at = now())
```

**Rules:**
- `ai_transcription` is **never modified** after creation — it is the permanent, honest record of what the model actually produced. This matters both for user trust and for the research experiment (you cannot measure model accuracy against a field the UI silently mutates).
- `verified_transcription` is only ever set through the explicit verification action — never auto-populated, never defaulted to equal `ai_transcription` without the user having seen and confirmed it.
- The frontend must visually distinguish "AI draft, unverified" from "human-verified" everywhere a transcription is shown (library list badges, detail view headers).
- A user can, in principle, re-open a verified transcription and re-edit it — updating `verified_transcription` and `verified_at`, but still never touching `ai_transcription`. This is a reasonable P1 feature if not already trivially supported by the same PATCH endpoint.

---

## 18. Evaluation Architecture

CER/WER computation is a **separate, standalone module** (`experiments/evaluation/`), independent of the running API — it operates on saved model outputs and ground-truth text files, not live requests.

```
experiments/evaluation/
    compute_metrics.py     # given (hypothesis_text, reference_text) -> {cer, wer}
    run_evaluation.py       # loops over experiment conditions, calls compute_metrics,
                              writes results to experiments/results/
```

**Required inputs per evaluated sample:** the model's transcription output (hypothesis) and a real, human-provided ground-truth Devanagari transcription (reference) for the same manuscript image. **If no ground truth is available for a given image, it is excluded from CER/WER tables and this exclusion is explicitly noted** — never substitute an estimate or a "looks about right" placeholder.

See `RESEARCH_PAPER.md` Sections 12–13 for the CER/WER formulas and Section 10 for full experimental design (baseline, independent/dependent variables, controls).

---

## 19. Experiment Directory Structure

```
experiments/
├── preprocessing/
│   ├── run_original.py         # applies "original" config, saves image
│   ├── run_grayscale.py
│   ├── run_denoised.py
│   ├── run_enhanced.py
│   ├── run_binarized.py
│   ├── run_deskewed.py
│   └── run_full_restoration.py
│   (or, better: one run_condition.py script parameterized by config name —
│    agent should prefer this to avoid duplicated code, unless time pressure
│    makes copy-paste scripts faster to get working first)
├── evaluation/
│   ├── compute_metrics.py
│   └── run_evaluation.py
└── results/
    ├── exp_log.csv              # one row per (image, condition, CER, WER, timestamp)
    └── qualitative/              # side-by-side images + transcriptions for the paper
```

Each experiment run should append to `exp_log.csv` and also get a corresponding `EXP-XXX` entry in `RESEARCH_PAPER.md` Section 11 — the CSV is the machine-readable record, the markdown log is the human-readable narrative record. They must stay consistent.

---

## 20. Research Experiment

**What is being tested:** whether, and how much, different image restoration/preprocessing strategies change the transcription accuracy (CER/WER) of Qwen2.5-VL-3B + Modi LoRA on real (ideally degraded/historical-looking) Modi manuscript images.

**Minimum viable experiment for the 20–22 hour budget:** take as many real manuscript images as are actually available (even a handful), run each through the set of preprocessing conditions listed in Section 12, run each resulting image through the model, and — for any image where ground truth exists — compute CER/WER per condition. If ground truth is scarce, a qualitative comparison (does the transcription look more/less accurate, documented with real examples) is an acceptable and honestly-reported fallback, explicitly labeled as qualitative rather than quantitative.

**This is real research at small scale, not a full academic study.** `RESEARCH_PAPER.md` Section 27 (Research Integrity Rules) governs how this must be reported: no invented numbers, no invented sample sizes, explicit limitations.

---

## 21. Testing Strategy

| Level | What | Tooling |
|---|---|---|
| Restoration unit tests | Each stage function produces expected output shape/type on a fixed test image; pipeline runs without error for every defined config | `pytest`, `tests/test_restoration.py` |
| Model smoke test | Model loads (locally or confirms Colab endpoint reachable) and produces a non-empty string output for one fixed test image | `scripts/smoke_test_model.py`, run manually (not in CI — too slow/heavy) |
| Database tests | Create/read/update manuscript and transcription records; verify `ai_transcription` immutability behavior at the repository-function level | `pytest`, `tests/test_database.py`, using a temp SQLite file |
| API tests | Each endpoint returns expected status/shape for valid and invalid input, using FastAPI's `TestClient` | `pytest`, `tests/test_api.py` |
| Frontend tests | Optional/P2 — basic render tests for each page if time remains | — |
| End-to-end smoke test | Full pipeline: upload real test image via the running API → restored image exists → transcription exists and is non-empty → verify → appears in library search | manual script or a single pytest marked `@pytest.mark.e2e`, run last before declaring Phase 6/10 complete |

Run tests after every phase that touches code covered by them — do not wait until the end to discover a regression from three phases ago.

---

## 22. Logging and Debugging

- Use Python's standard `logging` module, configured once in `backend/utils/logging.py`, imported everywhere else (`logger = logging.getLogger(__name__)`).
- **Restoration errors:** log the manuscript id, the stage that failed, and the exception — restoration failures should degrade gracefully (fall back to using the original image) rather than crashing the whole upload request, since the pipeline is explicitly allowed to be partial.
- **Model/inference errors:** log the manuscript id, inference mode (local/colab), and full exception — including CUDA OOM messages verbatim, since these are directly useful for Section 15 decision-making. Never swallow these silently.
- **API errors:** FastAPI's default exception handling plus explicit logging in route-level `try/except` blocks around the restoration/inference calls specifically (these are the two genuinely risky operations in the pipeline).
- Log level: INFO for pipeline milestones (upload received, restoration complete, transcription complete), DEBUG for per-stage detail, ERROR for anything that breaks the happy path.

---

## 23. Error Handling

Defined failure cases and expected behavior:

| Failure | Expected behavior |
|---|---|
| Uploaded file is not a valid image | 400 response, clear error message, no DB record created |
| Uploaded file exceeds a reasonable size limit | 400 response; define a sane limit (e.g. 20MB) in `config.py` |
| A restoration stage throws (e.g. malformed image data mid-pipeline) | Log it, fall back to the original image as the "restored" image, continue the pipeline, flag this in the manuscript record (e.g. `status` note or a `restoration_warning` field) rather than failing the whole request |
| Model fails to load (missing weights, incompatible environment) | `/api/health` reports `model_loaded: false`; upload endpoint returns a clear 503 with an explanatory message rather than a raw stack trace; the image and DB record for the manuscript are still created up through the restoration step so no work is lost |
| CUDA OOM during inference | Caught, logged with full detail, 503 returned; this is exactly the trigger condition for switching `INFERENCE_MODE` to `colab` per Section 15 |
| Colab endpoint unreachable | Caught, logged, 503 returned with a message distinguishing this from a local OOM (different debugging path) |
| Search with no matches | 200 response with an empty list, never an error |
| Verify request for a nonexistent transcription id | 404 |

---

## 24. Performance Strategy

- **Load the model once**, at process startup or lazily on first request, and keep it resident in memory/VRAM for the life of the backend process — never reload per-request. This is the single biggest performance and VRAM-fragmentation risk if done wrong.
- Minimize **downloads**: after the first successful `from_pretrained(...)` call, weights are cached by Hugging Face locally (`~/.cache/huggingface`) — do not re-download on every test run; verify the cache is being hit.
- Minimize **unnecessary computation**: don't run the full restoration pipeline multiple times on the same image during iterative testing — cache/save intermediate results during development.
- Minimize **API calls**: the frontend should not poll; a single request/response per upload and per verify action is sufficient for this scale.
- Minimize **token usage** in generation: cap `max_new_tokens` to something reasonable for a page of manuscript text (avoid runaway generation eating time/memory) — determine a sensible value empirically during the smoke test, **TO BE MEASURED**.
- Minimize **large image memory usage**: downscale before sending to the model if the processor doesn't already enforce a sane maximum resolution; don't keep multiple full-resolution copies of the same image in memory simultaneously.

---

## 25. Definition of Done

The project is **NOT done** merely because:
- the frontend renders three pages, or
- the API returns 200 for a mocked/hardcoded transcription, or
- the restoration pipeline runs without producing a real model call, or
- unit tests pass but no real end-to-end run has ever happened on a real image.

The project **IS done** when ALL of the following are true simultaneously:

- [ ] A real Modi manuscript image can be uploaded through the actual running frontend.
- [ ] The original image is preserved on disk and referenced correctly in the DB.
- [ ] A real OpenCV restoration pipeline runs and produces a real, inspectable restored image (not identical to the original unless a config genuinely specifies no-op).
- [ ] A real call to Qwen2.5-VL-3B + Modi LoRA (local or Colab) produces a real, non-fabricated Devanagari transcription string for that image, and this has been directly observed (not assumed) by the developer at least once.
- [ ] The transcription is editable and can be marked verified through the frontend, and `ai_transcription` vs `verified_transcription` are stored and displayed as genuinely separate fields.
- [ ] The manuscript appears in "My Library," is searchable, and its detail view shows original, restored, AI, and verified text correctly.
- [ ] At least one restoration-vs-transcription comparison has been run with real output and logged in `RESEARCH_PAPER.md` under an `EXP-XXX` entry, with honest CER/WER or an honestly-labeled qualitative comparison if ground truth was unavailable.
- [ ] `RESEARCH_PAPER.md` Sections 0, 7, 8, 9, 11, 14 (or 20) reflect actual project state, not placeholders, by submission time.
- [ ] All four documentation files exist and are internally consistent with what was actually built (update `PROJECT_GUIDE.md` itself if implementation diverges from a documented assumption).

---

## 26. 20–22 Hour Priority Order

**P0 — Critical (the demo does not exist without these):**
- Environment verified (Python, Node, CUDA, GPU visible) — Phase 0
- OpenCV restoration pipeline runs standalone on a real image — Phase 2
- Model smoke test: one real inference call succeeds, local or Colab — Phase 3
- SQLite schema created, basic CRUD works — Phase 5
- FastAPI endpoints: upload → restore → transcribe → return result — Phase 6 (core of Phase 6)
- Minimal frontend: upload + display result (even unstyled) — Phase 7 (core only)
- Verify action works end-to-end — part of Phase 6/7

**P1 — Strongly recommended (expected in a "complete" MVP):**
- Library page with list + search
- Multiple preprocessing configs implemented and selectable
- At least one real CER/WER or qualitative experiment logged
- Basic error handling per Section 23
- README.md written
- Reasonable frontend styling (not elaborate)

**P2 — Useful if time remains:**
- Multiple experiment conditions with a results table/chart
- Line segmentation stage
- SQLite FTS5 search
- Frontend polish matching the reference screenshot's spirit
- Additional unit tests beyond the essentials

**P3 — Future work, do not attempt during MVP hours:**
- Everything in Section 5 (Non-Goals) and Section 30 (Future Roadmap)

**If time runs out, cut in reverse order: P3 → P2 → P1.** Never cut P0. If a P0 item is at risk (most likely candidate: model inference not working locally), invoke the Colab fallback immediately rather than continuing to debug locally — see Section 15's time-boxing guidance.

---

## 27. Development Phases

For every phase: **Objective, Expected files, Dependencies, Input, Output, Validation, Completion criteria, Common failure modes, Fallback.**

### Phase 0 — Environment Verification
- **Objective:** confirm the actual dev machine can do what the plan assumes, before writing a line of app code.
- **Expected files:** none yet (or a scratch `scripts/env_check.py`).
- **Dependencies:** none.
- **Input:** the developer's machine.
- **Output:** a written confirmation (even just terminal output saved) of: Python version, pip works, Node/npm version, `nvidia-smi` output, `torch.cuda.is_available()` result.
- **Validation:** all commands run without error and report sane values.
- **Completion criteria:** GPU is visible to PyTorch, or it is explicitly known and documented that it is not (in which case Colab-only inference is decided *now*, not discovered mid-Phase-3).
- **Common failure modes:** CUDA/PyTorch version mismatch; NVIDIA driver present but PyTorch built without CUDA support.
- **Fallback:** if GPU is not visible at all, skip ahead mentally to "Colab is the primary inference path" and don't burn time on local GPU troubleshooting beyond basic driver checks.

### Phase 1 — Project Skeleton
- **Objective:** create the repository structure (Section 8), initialize git, set up Python venv and Node project shells.
- **Expected files:** directory tree, `.gitignore`, `requirements.txt` (initial), `frontend/package.json` (via `npm create vite@latest` or similar), empty `backend/main.py` with a working `/api/health` route.
- **Dependencies:** Phase 0.
- **Input:** none.
- **Output:** a runnable (even if empty) FastAPI server and a runnable (even if default) React app.
- **Validation:** `uvicorn backend.main:app --reload` serves `/api/health`; `npm run dev` serves the default Vite/CRA page.
- **Completion criteria:** both processes start with zero errors; first git commit made.
- **Common failure modes:** import path issues running uvicorn from the wrong directory; Node version incompatibility.
- **Fallback:** none needed — this phase has no real uncertainty.

### Phase 2 — OpenCV Pipeline
- **Objective:** implement and standalone-test the restoration pipeline (Section 12) against at least one real sample Modi manuscript image.
- **Expected files:** `backend/services/restoration/stages.py`, `pipeline.py`, `scripts/smoke_test_opencv.py`, sample image in `data/raw/`.
- **Dependencies:** Phase 1; a real sample image obtained (see `FOR_DEV.md` Section 10).
- **Input:** one sample manuscript image.
- **Output:** restored images for each defined config, saved to `data/outputs/` for visual inspection.
- **Validation:** visually confirm each stage does something sensible on the sample image (e.g. binarized output is actually binary, deskew actually straightens a skewed sample if one is available).
- **Completion criteria:** `smoke_test_opencv.py` runs end-to-end with no FastAPI/DB dependency and produces inspectable output for all defined configs.
- **Common failure modes:** OpenCV color-space confusion (BGR vs RGB), over-aggressive thresholding destroying faint ink strokes (this is itself a research-relevant observation — log it).
- **Fallback:** if a stage proves unreliable/buggy under time pressure, mark it optional/disabled in configs rather than blocking the phase — note it as a limitation.

### Phase 3 — Model Smoke Test
- **Objective:** the single highest-uncertainty phase — confirm Qwen2.5-VL-3B + Modi LoRA can actually run locally and produce real output.
- **Expected files:** `scripts/smoke_test_model.py`, initial `backend/services/transcription/local_qwen.py` (or `colab_client.py` if pivoting immediately).
- **Dependencies:** Phase 0 (environment known); inspection of the actual HF repos per Section 13.
- **Input:** one small test image (can reuse the Phase 2 sample, original or a restored variant).
- **Output:** one real, observed transcription string, logged verbatim (success case) or one real, observed error (failure case, triggering fallback).
- **Validation:** the output is a non-empty string that is plausibly Devanagari text (visual sanity check), OR a clean decision to move to Colab has been made and documented.
- **Completion criteria:** `transcribe(image_path, prompt) -> str` works via at least one of the two implementations, called directly (not yet through the API).
- **Common failure modes:** CUDA OOM; PEFT/Transformers version incompatibility with the adapter's stated requirements; wrong prompt format producing garbage/echoed-prompt output; processor mismatch.
- **Fallback:** Section 15's Colab path. Time-box local attempts (see Section 14's guidance) and pivot decisively rather than iterating indefinitely.

### Phase 4 — Backend Integration (Restoration + Model, no DB yet)
- **Objective:** wire restoration and transcription together behind a single function callable in-process, without the database or API yet.
- **Expected files:** an integration script or the beginnings of the API route logic, calling `pipeline.run(...)` then `transcribe(...)` in sequence.
- **Dependencies:** Phases 2 and 3 both independently working.
- **Input:** one sample image.
- **Output:** a restored image + a real transcription, produced by one combined call.
- **Validation:** manual inspection of both outputs together.
- **Completion criteria:** the full non-persisted pipeline (image in → transcription out) works reliably at least twice in a row.
- **Common failure modes:** passing the wrong image variant (original vs restored) to the model by mistake; file path bugs.
- **Fallback:** none — this is integration of already-proven pieces.

### Phase 5 — SQLite Archive
- **Objective:** implement schema (Section 16) and repository functions; test CRUD independent of the API.
- **Expected files:** `backend/database/models.py` (or `schema.sql`), `session.py`, `services/archive/repository.py`, `tests/test_database.py`.
- **Dependencies:** Phase 1.
- **Input:** none (can be developed in parallel with Phases 2–4 if agent capacity allows, but is listed after Phase 4 for a single-threaded human developer's sanity).
- **Output:** a working SQLite file with correct schema, passing CRUD tests.
- **Validation:** `pytest tests/test_database.py` passes; manual inspection via a SQLite browser or `sqlite3` CLI shows sane data after a manual insert.
- **Completion criteria:** manuscripts and transcriptions can be created, read, updated (including the verify action), and searched.
- **Common failure modes:** forgetting `updated_at`/`verified_at` triggers/logic; foreign key mismatches.
- **Fallback:** none needed.

### Phase 6 — Full API Pipeline
- **Objective:** connect Phases 4 and 5 behind real FastAPI routes per Section 10/7.
- **Expected files:** `backend/api/manuscripts.py`, `transcriptions.py`, `schemas/*.py`.
- **Dependencies:** Phases 4 and 5 complete.
- **Input:** HTTP requests (test via FastAPI's auto-generated `/docs` UI or `curl`/Postman before the frontend exists).
- **Output:** correct JSON responses for upload, get, search, verify.
- **Validation:** manual testing via `/docs`, plus `tests/test_api.py`.
- **Completion criteria:** the full workflow (Section 7) can be executed purely via HTTP requests, no frontend needed yet.
- **Common failure modes:** multipart file upload handling bugs; response model mismatches (pydantic validation errors on the way out).
- **Fallback:** none — this is wiring of already-proven pieces.

### Phase 7 — React Frontend
- **Objective:** implement Transcribe, Library, About per Section 11, wired to the real API.
- **Expected files:** `frontend/src/pages/*.jsx`, `api/client.js`.
- **Dependencies:** Phase 6 complete and stable.
- **Input:** the running FastAPI backend.
- **Output:** a working UI for the full end-to-end flow.
- **Validation:** manual click-through of the entire Section 7 workflow in a browser.
- **Completion criteria:** a user can go from "select a file" to "see it verified in the library" using only the UI.
- **Common failure modes:** CORS misconfiguration (FastAPI needs CORS middleware enabled for `localhost:5173`/`3000`); forgetting loading states, leaving the UI looking frozen during the (slow) inference call.
- **Fallback:** if time is short, prioritize Transcribe > Library > About in that order — About can be a single static paragraph if necessary.

### Phase 8 — Evaluation
- **Objective:** implement and run the CER/WER (or qualitative) experiment per Sections 18–20.
- **Expected files:** `experiments/evaluation/compute_metrics.py`, `run_evaluation.py`, `experiments/results/exp_log.csv`.
- **Dependencies:** Phase 3 (model working) and Phase 2 (restoration configs working); at least one image with ground truth, if achievable.
- **Input:** one or more manuscript images across preprocessing conditions.
- **Output:** real CER/WER numbers or an honestly-labeled qualitative comparison.
- **Validation:** spot-check the CER/WER computation against a hand-computed example to confirm the formula implementation is correct.
- **Completion criteria:** at least one `EXP-XXX` entry exists in `RESEARCH_PAPER.md` with real data.
- **Common failure modes:** conflating CER and WER; computing metrics on mismatched/misaligned text.
- **Fallback:** no ground truth available → qualitative comparison only, explicitly labeled as such — this is an acceptable, honest outcome, not a failure of the project.

### Phase 9 — Research Artifacts
- **Objective:** consolidate experiment results into `RESEARCH_PAPER.md`'s ablation/robustness/qualitative/failure-case sections.
- **Expected files:** updates to `RESEARCH_PAPER.md`; possibly `experiments/results/qualitative/*.png` comparison images.
- **Dependencies:** Phase 8.
- **Input:** Phase 8's outputs.
- **Output:** a paper notebook that honestly reflects what was actually measured.
- **Validation:** every number in the paper traces to an `EXP-XXX` entry and a file in `experiments/results/`.
- **Completion criteria:** Section 25's research checklist item is satisfied.
- **Common failure modes:** the temptation to round up, generalize beyond the sample size, or omit failure cases — resist all three (Section 27 of `RESEARCH_PAPER.md`).
- **Fallback:** none — honesty here is non-negotiable regardless of time pressure.

### Phase 10 — Final Polish
- **Objective:** README, minor UI cleanup, final Git hygiene, demo rehearsal.
- **Expected files:** `README.md`, minor diffs across the codebase.
- **Dependencies:** all prior phases.
- **Input:** the finished project.
- **Output:** a submission-ready repository.
- **Validation:** Section 25's Definition of Done checklist, checked item by item.
- **Completion criteria:** everything in Section 25 is checked.
- **Common failure modes:** spending polish time on visuals instead of verifying the checklist.
- **Fallback:** if time runs out mid-polish, a correct, ugly, working demo beats a pretty, broken one — stop polishing and verify functionality.

---

## 28. Coding-Agent Rules

- **Inspect first.** Before implementing Phase 3, actually read the model/adapter repositories. Before modifying any existing file, view it.
- **Do not overwrite blindly.** Never regenerate a whole file when a targeted edit will do; never overwrite a file you haven't viewed in the current session.
- **Do not invent.** Model compatibility, benchmark numbers, API behavior, and file existence must be confirmed, not assumed. Use the exact markers from the Anti-Hallucination Rules section of the master brief (`VERIFY THIS DURING IMPLEMENTATION`, `TO BE MEASURED`, `TO BE CONFIRMED AGAINST THE ACTUAL ENVIRONMENT`) wherever something is genuinely unknown.
- **Test after major changes.** Every phase in Section 27 has explicit validation steps — run them before declaring a phase done.
- **Do not add unnecessary dependencies.** Anything beyond Section 9's stack needs a written reason.
- **Do not refactor working code without reason.** Time is scarce; stability beats elegance for this project.
- **Do not start optional (P1/P2) work before P0 work in the current phase is genuinely done and validated.**
- **Keep modules small** and aligned with Section 8/10's separation of concerns.
- **Document assumptions** inline (comments) and in this file if they affect architecture.
- **Preserve experimental reproducibility** — never change a preprocessing config's behavior after it's been used in a logged experiment without giving it a new name/id.
- **Stop and report uncertainty rather than hallucinating.** If the LoRA's prompt format genuinely can't be determined from available sources, say so explicitly and propose the smallest experiment to determine it empirically, rather than guessing silently.

---

## 29. Git Strategy

Simple, student-friendly, milestone-based commits — no elaborate branching strategy needed for a solo 20–22 hour project (a single `main` branch is fine; a `dev` branch is optional if the agent/developer wants a safety net before big changes).

Suggested commit sequence (see `FOR_DEV.md` Section 24 for full Git command reference):

```
chore: initialize LipiLens project
docs: add four core documentation files
feat: add image inspection
feat: add manuscript restoration pipeline
feat: add Modi transcription inference (local)
feat: add Colab fallback for transcription
feat: add SQLite archive schema and repository
feat: add FastAPI manuscript and transcription routes
feat: add verification workflow
feat: add React transcription interface
feat: add React library interface
feat: add evaluation pipeline
docs: add research experiment notes (EXP-001...)
fix: <specific bug>
docs: finalize README
```

Commit after each phase in Section 27 passes its validation step — not before, and not by batching multiple phases into one commit.

---

## 30. Future Roadmap

Explicitly future work — **not MVP scope**, do not implement during the 20–22 hour build:

- Better/larger Modi-specific models, or an eventual custom-trained adapter.
- Larger, curated manuscript datasets with verified ground truth.
- Active learning: prioritizing which manuscripts most need human review based on model confidence.
- Scholar annotation tools (line-level correction, character-level confidence highlighting).
- Confidence estimation surfaced to the user per transcription.
- Line-level and word-level transcription with bounding boxes.
- English (or other language) translation of the Devanagari output.
- Historical named-entity extraction (people, places, dates) from transcribed text.
- Multilingual/multi-script support beyond Modi.
- Larger-scale corpus ingestion tooling (batch upload, archival metadata import standards like Dublin Core).
- Real cloud deployment with proper authentication and multi-user support.
- Integration with archival/library standards (IIIF, METS/ALTO) for interoperability with existing digital preservation infrastructure.

Anything in this section that starts feeling urgent during the MVP build is a sign to re-check Section 5 (Non-Goals) and Section 26 (Priority Order) rather than start building it.
