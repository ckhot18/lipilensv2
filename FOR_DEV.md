# LipiLens — Developer Manual

**Audience:** you, the student building this, assuming basic programming knowledge but no assumed DevOps/Git/model-serving experience.
**Companion documents:** `PROJECT_GUIDE.md` (architecture — read this if you want to understand *why*), `TO_SETUP_AI.md` (how to brief your AI coding agent), `RESEARCH_PAPER.md` (where experiment results go).

---

## 1. What I am building

A website where I upload a photo of a historical handwritten Modi-script manuscript. The system cleans up the image a bit, then an AI model reads it and writes out what it thinks the text says in Devanagari script. I can then correct any mistakes and click "Verified." Everything gets saved so I can search through all the manuscripts I've processed later. Alongside the software, I'm also running a small experiment: does cleaning up the image (denoising, contrast, etc.) actually help the AI read it better, or does it sometimes hurt?

---

## 2. Before touching the project — checklist

- [ ] I have read `PROJECT_GUIDE.md` Sections 1–8 at least once (architecture overview).
- [ ] I know my available implementation time (~20–22 hours) and I'm not trying to do everything in Section 30 of that file.
- [ ] I have at least one real Modi manuscript image to work with (see Section 10 below for where to find one).
- [ ] I have admin access on my Windows machine (needed for installing software if not already present).
- [ ] I have a GitHub account.
- [ ] I have decided roughly when my 20–22 hours will happen (one sitting vs spread across days) — this affects how aggressively you should commit/push (more often if spread out, so nothing is lost).

---

## 3. Required software — how to check what's already installed

Open **PowerShell** (search "PowerShell" in the Windows start menu) and run each command below. If a command fails with something like "not recognized as an internal or external command," that software isn't installed (or isn't on your PATH) and you need to install it.

```powershell
git --version
python --version
pip --version
node --version
npm --version
nvidia-smi
```

**Expected output examples:**
- `git --version` → `git version 2.4x.x`
- `python --version` → `Python 3.1x.x` (3.10 or 3.11 recommended for best PyTorch/Transformers compatibility — **verify current recommended version against the Transformers install docs during setup**, don't assume)
- `node --version` → `v18.x.x` or `v20.x.x`
- `nvidia-smi` → a table showing your GPU (RTX 2050), driver version, and CUDA version supported by the driver

**If something is missing:**
- Git: https://git-scm.com/download/win
- Python: https://www.python.org/downloads/ (check "Add Python to PATH" during install!)
- Node.js (includes npm): https://nodejs.org/ (LTS version)
- NVIDIA driver: https://www.nvidia.com/Download/index.aspx (search for RTX 2050)
- VS Code (recommended editor): https://code.visualstudio.com/

You do not need to separately "install CUDA" as a toolkit for this project in most cases — PyTorch ships its own CUDA runtime bundled with the pip package, as long as your NVIDIA driver is recent enough. **Confirm this is still true for the PyTorch version you install** — check the install command generator at https://pytorch.org/get-started/locally/ rather than guessing a version.

---

## 4. Creating the project folder

Open PowerShell and run (replace `D:\Projects` with wherever you actually want to keep your projects — this is just an example path, substitute your own):

```powershell
cd D:\Projects
mkdir lipilens
cd lipilens
```

You are now inside your project folder. Every command in the rest of this document assumes you are here unless stated otherwise.

---

## 5. Creating the Python virtual environment

A virtual environment keeps this project's Python packages separate from everything else on your system.

**Create it:**
```powershell
python -m venv .venv
```

**Activate it (do this every time you open a new terminal to work on this project):**
```powershell
.venv\Scripts\Activate.ps1
```

If you get an error about "running scripts is disabled on this system," run this once (as your normal user, not admin), then try activating again:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Confirm it worked:** your PowerShell prompt should now show `(.venv)` at the start of the line.

**Confirm the correct Python is being used:**
```powershell
where.exe python
```
The first path listed should point *inside* your `.venv` folder (e.g. `D:\Projects\lipilens\.venv\Scripts\python.exe`), not your system Python.

**Deactivate (when you're done working, optional):**
```powershell
deactivate
```

---

## 6. Installing dependencies

With the venv activated:

```powershell
pip install --upgrade pip
pip install fastapi uvicorn[standard] python-multipart pydantic
pip install opencv-python numpy pillow
pip install sqlalchemy
pip install pytest
```

Then, for the model stack — **install PyTorch using the official command generator for your system** (don't just `pip install torch`, which may give you a CPU-only build):
1. Go to https://pytorch.org/get-started/locally/
2. Select: Stable, Windows, Pip, Python, and the CUDA version matching what `nvidia-smi` reported.
3. Copy and run the exact command it gives you.

Then:
```powershell
pip install transformers accelerate peft
pip install bitsandbytes
```

Finally, save everything you've installed so it's reproducible:
```powershell
pip freeze > requirements.txt
```

**Why each group exists:**
- `fastapi`, `uvicorn`, `python-multipart`, `pydantic` — the backend API and file upload handling.
- `opencv-python`, `numpy`, `pillow` — image restoration.
- `sqlalchemy` — database layer (or skip this and use Python's built-in `sqlite3` module directly if you prefer less abstraction — either is fine).
- `pytest` — testing.
- `torch` — the deep learning framework the model runs on.
- `transformers`, `accelerate`, `peft` — loading the Qwen2.5-VL base model and applying the Modi LoRA adapter.
- `bitsandbytes` — quantization, needed to fit the model in 4GB VRAM. **This package has had rockier Windows support historically than Linux — if installation or usage fails on Windows, this is expected and is exactly the trigger to consider the Colab fallback (see Section 17 below and `PROJECT_GUIDE.md` Section 15). Don't panic, don't spend hours fighting it.**

---

## 7. Verifying PyTorch + GPU

With the venv activated, run:

```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no GPU visible')"
```

**Expected output (success case):**
```
2.x.x+cu1xx
True
NVIDIA GeForce RTX 2050
```

**If `torch.cuda.is_available()` prints `False`:**
1. Re-check `nvidia-smi` works at all (driver issue if not).
2. Re-check you installed the CUDA-enabled PyTorch build (Section 6), not the default CPU-only `pip install torch`.
3. Try: `pip uninstall torch torchvision torchaudio` then reinstall using the exact command from pytorch.org's selector for your CUDA version.
4. If still `False` after one focused attempt, **stop troubleshooting and treat local GPU inference as unavailable** — plan around the Colab fallback from the start rather than losing hours here. This is a legitimate, documented outcome, not a failure.

---

## 8. Creating the initial Git repository

```powershell
git init
git status
```
`git status` shows you what files exist and are (not yet) tracked. It's safe to run any time — it never changes anything, it just reports.

```powershell
git add .
git commit -m "chore: initialize LipiLens project"
```
- `git add .` stages every current file (marks them "ready to be committed") — but check `git status` first and make sure `.gitignore` (next section) is in place *before* this, so you don't stage things like your venv or model caches.
- `git commit -m "..."` saves a permanent snapshot of the staged files with that message.

---

## 9. Creating `.gitignore`

Create a file named exactly `.gitignore` in your project root with this content:

```
# Python
.venv/
__pycache__/
*.pyc

# Node
frontend/node_modules/
frontend/dist/

# Model caches and weights — these are huge and should never be committed
**/models/
*.bin
*.safetensors
.cache/
huggingface_cache/

# Environment/secrets
.env
*.env.local

# Generated data (keep folder structure, ignore contents)
data/raw/*
!data/raw/.gitkeep
data/processed/*
!data/processed/.gitkeep
data/outputs/*
!data/outputs/.gitkeep

# Database
*.db
*.sqlite
*.sqlite3

# OS junk
.DS_Store
Thumbs.db
```

**Why this matters:** model weight files can be multiple gigabytes — committing them would make your repository unusable and likely exceed GitHub's file size limits. Secrets (API keys, if you ever add any) must never be committed, because they'd be visible in your public repo's history forever, even if you delete them later.

---

## 10. Adding the dataset

- **Raw manuscript images** go in `data/raw/` — never edit or overwrite these once added. They're your ground truth for "what did the original actually look like."
- **Evaluation ground truth** (real Devanagari transcriptions you or someone else typed out by hand for a manuscript, used to compute CER/WER) goes in `data/evaluation/`.
- **Processed/restored images** go in `data/processed/` — these are always *derived*, never edited directly; if you need to change a restoration setting, re-run the pipeline, don't hand-edit the output image.

**Where to find real sample Modi manuscript images:** search digital archives such as institutional/university digital manuscript collections, or public heritage archive sites that host Modi script material. Because I can't verify link availability for you in this document, when you actually do this search, confirm licensing/usage terms for anything you use, and if you cannot find real historical samples in time, a small number of manually-written or printed Modi-script test images (even created by yourself, if you can produce readable Modi characters, or sourced from a font/character reference) are an acceptable substitute for pipeline development — just document honestly in `RESEARCH_PAPER.md` if your evaluation set isn't drawn from genuinely historical, degraded documents, since that affects what your degradation-robustness experiment can actually claim.

**Why originals must never be overwritten:** if you restore-in-place and the restoration turns out to be wrong or destructive (e.g., thresholding erases faint ink), you've permanently lost the source. The whole point of a "preservation" pipeline is that the original is sacred.

---

## 11. Creating the React app

From your project root:

```powershell
cd frontend
```

If `frontend/` doesn't exist yet as a real app (just an empty folder from your skeleton), create it:

```powershell
cd ..
npm create vite@latest frontend -- --template react
cd frontend
npm install
```

This scaffolds a React app using Vite (a fast, simple build tool — good fit for a time-constrained project, avoids Create React App's slower setup).

---

## 12. Starting the backend

From the project root, with your venv activated:

```powershell
uvicorn backend.main:app --reload --port 8000
```

`uvicorn` is the server that actually runs your FastAPI app. `--reload` makes it auto-restart when you save a code change (great for development, never use it for a real production deployment — not relevant here, but good to know why). `--port 8000` is just the port number the server listens on — you'll hit it at `http://localhost:8000`.

Open `http://localhost:8000/docs` in a browser to see FastAPI's automatic interactive API documentation — extremely useful for testing endpoints before the frontend exists.

---

## 13. Starting the frontend

In a **separate** PowerShell window/tab (keep the backend one running):

```powershell
cd D:\Projects\lipilens\frontend
npm run dev
```

This starts the frontend dev server, usually at `http://localhost:5173`. "Localhost" just means "this same computer" — the URL `http://localhost:5173` is a web address that only works from the machine running the server; it's how you preview your own site before it's deployed anywhere.

---

## 14. How frontend and backend communicate

The React app (running on port 5173) sends HTTP requests (like a browser visiting a webpage, but done in code via `fetch`) to the FastAPI backend (running on port 8000). For example, clicking "Upload" in the browser triggers a JavaScript `fetch('http://localhost:8000/api/manuscripts', { method: 'POST', body: formData })` call, and the backend responds with JSON data that React then displays.

**CORS note:** by default, browsers block a page on port 5173 from talking to a server on port 8000 unless that server explicitly allows it. You (or your AI agent) need to add FastAPI's `CORSMiddleware` in `backend/main.py` allowing `http://localhost:5173` as an origin, or you'll see confusing "CORS error" messages in the browser console. This is normal and expected the first time you wire frontend to backend — not a sign something is fundamentally broken.

---

## 15. How to test OpenCV independently

You don't need the backend server or frontend running at all for this.

```powershell
python scripts/smoke_test_opencv.py
```

This script (built during Phase 2) should load a sample image from `data/raw/`, run it through each restoration config, and save the results to `data/outputs/`.

**To compare original vs restored:** just open both image files (e.g. in Windows Photos, or VS Code's built-in image viewer) side by side. Look for: is text more legible? Did thresholding accidentally erase faint strokes? Did deskewing actually straighten the page?

---

## 16. How to test Qwen independently

This is the most important and highest-risk step in the whole project. Do this *before* wiring anything else together.

```powershell
python scripts/smoke_test_model.py
```

**What to expect on first run:** the script will download the base Qwen2.5-VL-3B model weights (multiple gigabytes) and the LoRA adapter from Hugging Face. This can take a while depending on your internet connection — this is normal, it only happens once (files get cached locally, typically under `%USERPROFILE%\.cache\huggingface`).

**Cache behavior:** subsequent runs should be fast to *load* (no re-download) but will still take real time to actually load the model into memory and run inference — that's normal, not a bug.

**How to check VRAM usage while it's running:** open a second PowerShell window and run:
```powershell
nvidia-smi
```
Look at the "Memory-Usage" column for your GPU. Run this a couple of times while the model is loading/inferring to watch it climb. If you have `nvidia-smi` output showing you're near the full 4096 MiB, you're right at the edge.

**Likely OOM behavior:** if the model doesn't fit, you'll see a Python error containing `CUDA out of memory` (sometimes abbreviated `CUDA error: out of memory`). This is not a crash of your computer or a sign anything is broken — it's the GPU driver correctly reporting there isn't enough VRAM for the requested allocation.

**How to stop a running script:** `Ctrl+C` in the PowerShell window it's running in. If it seems stuck/unresponsive, close that PowerShell window entirely — this fully kills the Python process and frees VRAM.

**Fallback to Colab:** see Section 17 immediately below.

---

## 17. What to do if Qwen does not fit on 4GB VRAM

**Do not panic. Do not randomly reinstall CUDA. Do not randomly download other models "just in case."** Follow this decision tree:

1. **Confirm you're using a reduced-precision load.** Are you loading with `torch_dtype=torch.float16` (or bfloat16) rather than default float32? If not, fix that first — it's the single cheapest win.
2. **Confirm quantization is actually active.** Is `bitsandbytes` successfully loading the model in 4-bit/8-bit? Check for any warning/error at load time indicating it silently fell back to full precision.
3. **Try a smaller test image.** Large input images can spike memory during image encoding even if the model itself would otherwise fit — try the smallest legible test image you have.
4. **If it still OOMs after (1)–(3), stop.** You've made one reasonable, focused attempt (budget roughly 1–2 hours for this, not more). Move to Colab.

**Moving to Colab:**
1. Go to https://colab.research.google.com/ and create a new notebook.
2. In Colab's menu: Runtime → Change runtime type → select a GPU (T4 is typically available on the free tier).
3. In the first cell, install the same packages you installed locally (`transformers`, `peft`, `accelerate`, `torch` — Colab usually has torch preinstalled, check its version first).
4. Load the model + LoRA adapter exactly as you did locally (same code, since Colab likely has considerably more VRAM available and shouldn't need quantization, though you can keep it for consistency).
5. Wrap inference in a minimal web server (a small FastAPI or Flask app run inside the Colab cell) and expose it publicly using a tunneling tool (e.g. `ngrok`, or Colab's newer built-in options — check current recommended approach at the time you do this, tooling here changes).
6. Point `backend/services/transcription/colab_client.py` at the resulting public URL, set `INFERENCE_MODE = "colab"` in `config.py`.
7. Test the same smoke test script — it should now succeed by calling out to Colab instead of loading the model in-process.

This is a legitimate, expected engineering decision for this hardware — document it plainly in `RESEARCH_PAPER.md`, don't treat it as something to hide or apologize for.

---

## 18. Running the complete pipeline

Once Phases 2–6 (per `PROJECT_GUIDE.md` Section 27) are done, the full flow is:

1. Start backend (Section 12) and frontend (Section 13).
2. Open `http://localhost:5173`, go to "Transcribe."
3. Upload a manuscript image.
4. Wait for processing (restoration + model inference — can take real time, especially first request after a fresh server start due to model loading).
5. Review the AI transcription, correct any errors in the text box.
6. Click "Mark as Verified."
7. Go to "My Library," confirm the manuscript appears with a "Verified" badge.
8. Use the search box to find it by title or text content.

---

## 19. Database

**To inspect the SQLite database directly:** with the venv activated (or system-wide if you have it),
```powershell
python -m sqlite3 backend/lipilens.db
```
(Adjust the path to wherever your DB file actually is — check `backend/config.py`.) Inside the sqlite3 prompt:
```sql
.tables
.schema manuscripts
SELECT * FROM manuscripts;
.quit
```

If `sqlite3` isn't available as a command, you can also just use a free GUI tool like "DB Browser for SQLite" (https://sqlitebrowser.org/) — often easier for a beginner.

**To reset the development database:** simply delete the `.db` file and restart the backend if your code recreates the schema on startup (recommended — have your startup code call a `create_all_tables()` function that's safe to run against an empty file).

**To back up:** just copy the `.db` file somewhere — it's a single file, that's the whole database.

**To add test records without going through the UI:** write a small `scripts/seed_test_data.py` that calls your repository functions directly to insert a fake manuscript/transcription — useful for testing the Library page before the full pipeline is wired up.

---

## 20. Experiments

To run a preprocessing experiment condition:
```powershell
python experiments/preprocessing/run_condition.py --config grayscale_only --image data/raw/sample1.jpg
```
(Adjust to match however the script is actually implemented — the point is each run should be a simple, parameterized command, not something requiring code edits per run.)

To run evaluation across all conditions with available ground truth:
```powershell
python experiments/evaluation/run_evaluation.py
```
This should read from `data/evaluation/`, produce/update `experiments/results/exp_log.csv`, and print a summary table to the terminal.

---

## 21. CER/WER — beginner explanation

**CER (Character Error Rate)** answers: "out of all the characters in the correct answer, how many did the model get wrong (inserted, deleted, or substituted)?" Lower is better. 0% would mean a perfect match.

**WER (Word Error Rate)** is the same idea but counting whole words instead of individual characters.

**What you need to compute them:** for a given manuscript image, you need (a) the model's transcription output (the "hypothesis"), and (b) a real, correct transcription typed by a human who can actually read that manuscript (the "reference" / ground truth). You compare the two using an edit-distance algorithm (standard libraries exist for this — check what's actually available/installed rather than hand-rolling it, e.g. a package like `jiwer` is a common choice, but **verify it's actually installed/appropriate during implementation**).

---

## 22. Ground truth — why it matters

Without a real, human-verified correct transcription to compare against, you cannot compute a real accuracy number — you can only eyeball "this looks about right." Eyeballing is acceptable as a documented fallback (Section 17 of `RESEARCH_PAPER.md`'s qualitative analysis), but it is not the same claim as "the CER was X%," and the two must never be conflated in your writing.

---

## 23. Generating experiment results

Results (CSV rows, any generated comparison images) go in `experiments/results/`. Each experiment run should also get a corresponding written entry in `RESEARCH_PAPER.md` under "Experiment Log" (`EXP-001`, `EXP-002`, ...) — the CSV is the raw data, the markdown entry is the narrative explaining what you did and what you observed. Keep both.

---

## 24. Git everyday workflow

Run these from your project root, with your venv activated (Git itself doesn't care about the venv, but you'll typically be working in that terminal anyway).

**`git status`** — shows what's changed since your last commit. Safe to run constantly; changes nothing.

**`git add <file>`** (or `git add .` for everything) — stages changes, meaning "include this in my next commit."

**`git commit -m "message"`** — actually saves a snapshot of everything staged, with a description. Think of a commit as a checkpoint/save-point you can always return to.

**`git log`** — shows your commit history (press `q` to exit the scrollable view).

**`git diff`** — shows the exact line-by-line changes you've made but haven't committed yet. Useful before committing, to sanity-check what you're about to save.

**`git restore <file>`** — throws away uncommitted changes to a specific file, reverting it back to how it was at your last commit. Useful if you (or the AI agent) made a change that broke something and you just want to undo it.

**`git branch`** — lists your branches (for this project, you'll likely just have `main`).

**`git switch <branch>`** — switches to a different branch (only relevant if you decide to use one, e.g. a `dev` branch before risky changes).

**"What if I accidentally changed something?"** → `git diff` to see exactly what, then `git restore <file>` if you want to undo it (only works for uncommitted changes — see next point for committed ones).

**"What if the AI broke something and I already committed it?"** → `git log` to find the last good commit hash, then `git restore --source=<commit-hash> -- <file>` to pull just that file back from an earlier commit, or `git reset --hard <commit-hash>` to roll the *entire* project back to that point (this discards everything after it — be sure before using `--hard`).

**"What if I want to go back?"** → same as above; commits are exactly your safety net, which is why committing at every phase milestone (Section 29 of `PROJECT_GUIDE.md`) matters so much for a project built partly by an AI agent.

**"What does commit actually mean?"** → a permanent, named snapshot of your entire project's files at that moment, that you can always compare against or return to. It does not upload anything anywhere by itself — that's what `push` does (next section).

---

## 25. GitHub repository

**Creating the repository:**
1. Go to https://github.com/new
2. Name it `lipilens` (or whatever you like), choose Public or Private, do **not** initialize with a README/gitignore/license (you already have these locally) to avoid merge conflicts on first push.
3. Click "Create repository." GitHub will show you commands — use the "push an existing repository" ones, which look like:

```powershell
git remote add origin https://github.com/<your-username>/lipilens.git
git branch -M main
git push -u origin main
```

- `git remote add origin <url>` tells your local repo where its GitHub counterpart lives, nicknamed "origin."
- `git branch -M main` ensures your default branch is named `main`.
- `git push -u origin main` uploads your commits to GitHub, and `-u` remembers this pairing so future pushes can just be `git push`.

**Future pushes**, after making more commits:
```powershell
git push
```

**Checking your remote is set correctly:**
```powershell
git remote -v
```

**README.md:** write this last (Phase 10), once you know what the project actually does and looks like — a short public-facing summary, how to run it, a screenshot if you have one, and a link/reference to `PROJECT_GUIDE.md` and `RESEARCH_PAPER.md` for anyone wanting the full detail.

---

## 26. Working with Antigravity

See `TO_SETUP_AI.md` for the full operating manual. In short: give it one phase at a time from `PROJECT_GUIDE.md` Section 27, let it inspect the repo first, review what it produces before moving to the next phase, and commit at each milestone.

---

## 27. How to recover when the agent gets stuck

1. **Read the actual error message/traceback in full** — don't just tell the agent "it's broken," paste (or reference) the real error.
2. **Ask it to reproduce the failure in isolation** — e.g. "run just the smoke test script and show me the exact output" rather than re-running the whole pipeline.
3. **If it starts proposing large rewrites for a small bug, stop it.** Ask for the smallest possible fix instead (see `TO_SETUP_AI.md` Section 13's emergency debugging protocol).
4. **If it seems to be guessing about model/library behavior, ask it to inspect the actual installed package/docs/repo instead of continuing.**
5. **If you're several exchanges in with no progress, use `git diff` to see everything it's changed, and consider `git restore` on the messiest files to reset to a known-good state before trying a more targeted approach.**
6. **Worst case: `git reset --hard` to your last good commit and re-approach the problem with a narrower prompt.** This is exactly why frequent commits matter.

---

## 28. 20–22 hour project workflow

A reasonable allocation (adjust to your actual pace — the point is order and time-boxing, not exact minutes):

| Hours | Phase(s) |
|---|---|
| 0–1 | Phase 0: environment verification |
| 1–2.5 | Phase 1: project skeleton |
| 2.5–4.5 | Phase 2: OpenCV pipeline |
| 4.5–8 | Phase 3: model smoke test (the highest-risk phase — protect this time, don't let earlier phases run long and eat into it) |
| 8–9 | Phase 4: backend integration |
| 9–10.5 | Phase 5: SQLite archive |
| 10.5–13 | Phase 6: full API pipeline |
| 13–16.5 | Phase 7: React frontend |
| 16.5–18.5 | Phase 8: evaluation experiment |
| 18.5–19.5 | Phase 9: research artifacts written up |
| 19.5–22 | Phase 10: final polish, README, demo rehearsal, Definition of Done checklist |

If Phase 3 runs long (very plausible given the hardware constraint), pull time from Phase 7 (frontend polish) and Phase 9 (deeper research write-up) rather than skipping Phase 3's validation — a working model call is P0; a beautiful UI is not.

---

## 29. Final demo preparation

**What to actually demonstrate, in order:**
1. Briefly explain the problem (Modi script, why it's hard, why this matters) — 30 seconds, don't over-explain.
2. Show the architecture diagram (from `PROJECT_GUIDE.md` Section 6) for 15–30 seconds — "here's how the pieces fit together."
3. Live: upload a real manuscript image through the actual running app.
4. Show the restored image next to the original — point out one concrete thing restoration changed.
5. Show the AI transcription appearing (be honest about how long inference takes — if it's slow, say so and explain why, don't fake speed).
6. Make a small correction to the text, click "Mark as Verified."
7. Go to the Library, show the manuscript there with its verified badge, run a search.
8. Briefly show one result from the research experiment (e.g. a chart or table comparing CER across preprocessing conditions) — this is what separates a coding project from a project with a research contribution.
9. Mention limitations honestly (small dataset, hardware constraints, possibly the Colab fallback) — this reads as rigor, not weakness.

**If using the Colab fallback:** open and warm up the Colab session 10–15 minutes before demoing (free-tier sessions can be slow to allocate a GPU and can disconnect after idling). Have a backup plan (e.g. a short screen recording of a successful run) in case the live network call fails during the actual demo.

---

## 30. Final submission checklist

- [ ] **Code:** repository is pushed to GitHub, `main` branch is up to date, no uncommitted work sitting only on your local machine.
- [ ] **README.md:** exists, explains what the project is, how to run it, links to the other docs.
- [ ] **PROJECT_GUIDE.md, FOR_DEV.md, TO_SETUP_AI.md, RESEARCH_PAPER.md:** all present, and `RESEARCH_PAPER.md` in particular reflects what was *actually* measured, not placeholders.
- [ ] **Screenshots:** a few real screenshots of the running app (Transcribe screen with a real result, Library screen) saved somewhere sensible (e.g. `docs/`) for use in the README/demo/paper.
- [ ] **Experiments:** at least one real `EXP-XXX` entry with real data (or an honestly-labeled qualitative comparison if ground truth wasn't available).
- [ ] **GitHub:** repository is accessible (check sharing/visibility settings if required to be shared with an instructor).
- [ ] **Architecture diagram:** present in `PROJECT_GUIDE.md` (already is) and optionally exported as an image for the README/paper.
- [ ] **Demo flow:** rehearsed at least once end-to-end before the real presentation, including timing.
- [ ] **Results:** whatever real CER/WER or qualitative results exist are clearly presented, with sample size stated plainly.
- [ ] **Limitations:** stated honestly and specifically (not a vague "there is room for improvement") in both the About page (briefly) and `RESEARCH_PAPER.md` (in detail).
- [ ] **`.gitignore` verified:** no venv, no model weight files, no `.db` file with potentially large test data, no secrets, actually committed to the repo (double-check with `git status` right before final push that nothing huge or sensitive is staged).
