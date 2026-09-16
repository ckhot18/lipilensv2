# Antigravity Setup and Operating Manual

**Audience:** you, before and while using an AI coding agent (Antigravity, Claude Code, or similar) on this project.
**Goal:** maximum useful work per token, maximum useful work per unit compute, minimal repetition, minimal agent wandering, minimal context waste, minimal setup time, maximum reliability.
**Companion documents:** `PROJECT_GUIDE.md` (what the agent should build), `FOR_DEV.md` (what you personally do), `RESEARCH_PAPER.md` (where results go).

---

## 1. Purpose

An autonomous coding agent is extremely useful for a time-constrained project like this — but only if it's operated deliberately. Left unsupervised with a vague instruction, an agent will happily burn your token/compute budget re-reading the whole repository, re-explaining itself at length, building things out of priority order, or quietly inventing plausible-sounding details about the Qwen/LoRA model instead of checking. This file exists to prevent all of that.

---

## 2. What Antigravity should know before coding

Before any implementation work begins, the agent should have read (or be pointed at, and actually read — don't assume it inferred content from filenames):

- **`PROJECT_GUIDE.md`** — the architecture and phase plan. This is the primary spec.
- **`FOR_DEV.md`** — so the agent understands what *you* are expected to do manually (e.g. don't have the agent try to run PowerShell commands that require your interactive confirmation, or try to manage Colab sessions autonomously without your involvement).
- **`RESEARCH_PAPER.md`** — so the agent understands the research angle exists and matters, not just the software.
- **`TO_SETUP_AI.md`** (this file) — so it understands the operating rules you're holding it to.
- **`README.md`** — once it exists, as a sanity check on public-facing framing.

---

## 3. Repository state before handing to AI

Concrete checklist — complete Phase 0 and Phase 1 (Section 27 of `PROJECT_GUIDE.md`) **yourself, or with light agent assistance**, before handing off substantial autonomous work, so the agent starts from a working baseline it can verify against, not an empty void:

- [ ] Git exists (`git init` done, at least one commit).
- [ ] Python virtual environment exists and is activated.
- [ ] Core dependencies installed (`requirements.txt` has real content, even if minimal).
- [ ] CUDA/GPU visibility verified once manually (Section 7 of `FOR_DEV.md`) — the agent should not have to rediscover this from scratch, but should still confirm it during Phase 0 inspection.
- [ ] Node is installed, `npm --version` works.
- [ ] React skeleton exists (`frontend/` has a running Vite app, even the default template).
- [ ] At least one real sample dataset image exists in `data/raw/`.
- [ ] All four documentation files exist in the repo root.
- [ ] `.gitignore` exists and covers venv/model weights/secrets/db files.
- [ ] Initial commit made.

---

## 4. AI should inspect before acting

**Exact first prompt to use** when starting a session (adapt paths/tool names to your actual agent interface):

> "Before writing any code, inspect this repository: list the directory structure, open and read `PROJECT_GUIDE.md` in full, check what's already implemented in `backend/` and `frontend/`, run `pip list` (or check `requirements.txt`) to see what's installed, check whether a GPU is visible via `torch.cuda.is_available()`, and check `data/raw/` for available sample images. Report back a summary of current state — what exists, what's missing, and any discrepancies between `PROJECT_GUIDE.md`'s assumptions and what you actually find. Do not start implementing anything yet."

The agent should:
- inspect the repository (structure, existing files),
- inspect the environment (Python packages, GPU visibility),
- inspect the dataset (what sample images actually exist),
- inspect any model configuration already present,
- **report status back to you**,
- **not immediately start coding.**

Only after you've reviewed that report and confirmed it matches reality should you move to phase-by-phase implementation.

---

## 5. Agent operating principles

The agent should, throughout the project:

- Read `PROJECT_GUIDE.md` as the spec of record, referring back to specific sections rather than re-deriving architecture decisions from scratch each session.
- Work phase by phase (Section 27 of `PROJECT_GUIDE.md`), not attempt the whole project in one pass.
- Avoid creating unnecessary files (no speculative "might need this later" scaffolding beyond what the current phase requires).
- Avoid unnecessary dependencies (Section 9 of `PROJECT_GUIDE.md`'s stack is the ceiling, not a starting suggestion to expand from).
- Avoid large downloads it hasn't confirmed are actually needed (e.g. don't casually re-trigger a multi-GB model download to "test something" without checking the cache first).
- Avoid repeated model loading in the same debugging session — load once, test the loaded object repeatedly, don't restart the whole process per test.
- Avoid consuming massive context unnecessarily — don't have it re-read the entire codebase every turn; point it at specific files/diffs.
- Test incrementally, using each phase's validation steps from `PROJECT_GUIDE.md` Section 27.
- Keep changes localized to the current phase's scope.
- Make commits at milestones (end of each phase, once validated).
- **Never fabricate results** — this applies to code comments, chat responses, and especially anything destined for `RESEARCH_PAPER.md`.

---

## 6. Task decomposition

**Why "build the entire project" is a bad instruction:** it forces the agent to make dozens of unreviewed decisions at once, makes it far more likely to skip validation steps, makes failures hard to localize ("something somewhere is broken"), and burns a huge amount of context/compute on a single pass with no checkpoint for you to catch problems early — especially risky given Phase 3 (model loading) is genuinely uncertain and needs your attention before the agent builds five more phases on top of an unverified assumption.

**Instead, use:**
> "Implement Phase 1 from `PROJECT_GUIDE.md` Section 27. Stop after completing it and its validation step, and report back before continuing."

Then, after reviewing:
> "Phase 1 looks good and is committed. Implement Phase 2."

Repeat per phase. For the highest-risk phase (Phase 3, model smoke test), consider even finer decomposition:
> "Just inspect the `lgtk/qwen25vl-3b-modi-synth-lora` and base `Qwen2.5-VL-3B` model cards/repos and report back what you find about prompt format, expected image handling, and hardware requirements. Do not write inference code yet."

---

## 7. Prompt templates

**Repository inspection:**
> "Inspect [specific directory/file]. Report what exists, what's missing relative to `PROJECT_GUIDE.md` Section [X], and any discrepancies. Do not modify anything yet."

**Phase implementation:**
> "Implement Phase [N] from `PROJECT_GUIDE.md` Section 27: [paste that phase's objective line]. Follow the architecture in Section [relevant section]. Run the phase's validation step when done and report the actual output. Stop after this phase — do not start Phase [N+1]."

**Debugging:**
> "This command failed: [command]. Full error output: [paste actual traceback, not a paraphrase]. Reproduce this in isolation, identify the root cause, and propose the smallest possible fix. Do not rewrite unrelated code."

**Code review:**
> "Review [specific file/module] against `PROJECT_GUIDE.md` Section [relevant architecture section]. Flag anything that violates the separation of concerns described there (e.g. business logic in route handlers, direct DB access outside the repository layer). Do not fix anything yet — just report findings."

**Test generation:**
> "Write tests for [specific module] per `PROJECT_GUIDE.md` Section 21. Focus on [specific behavior]. Use `pytest`. Run them after writing and report actual pass/fail output."

**Performance optimization:**
> "[Specific measured problem, e.g. 'model loading takes 45 seconds per request instead of happening once at startup']. Identify why, per Section 24's performance strategy, and fix only that specific issue."

**Research experiment:**
> "Implement the experiment described in `PROJECT_GUIDE.md` Section 20 / `RESEARCH_PAPER.md` Section 11's template, for condition [X] on image [Y]. Run it for real, report the actual output (transcription text and/or CER/WER), and draft the corresponding `EXP-XXX` entry using real numbers only — do not fill in placeholder or estimated values."

**Documentation:**
> "Update `RESEARCH_PAPER.md` Section [X] with the real results from the experiment run in [file/log reference]. Do not add any numbers or claims not present in that source data."

**Git commit:**
> "Stage and commit the current changes with a message following the style in `PROJECT_GUIDE.md` Section 29. Show me `git status` and `git diff --stat` first so I can confirm what's being committed before you commit."

**Final audit:** see Section 17 below.

---

## 8. How to prevent token waste

- Don't paste huge raw logs into the conversation when a summary or the relevant few lines will do — but when debugging (Section 13), do paste the *actual* error text, not a paraphrase (paraphrasing errors loses exactly the detail needed to diagnose them).
- Don't ask the agent to re-explain things you already understand — reference `PROJECT_GUIDE.md` section numbers instead of having it restate architecture.
- Don't ask it to explain every line of generated code unless you're genuinely trying to learn that part — ask for explanations only where you actually need them.
- Keep instructions scoped to one phase/task at a time (Section 6).
- Reference files by path instead of pasting their contents into your prompt — a capable agent can open the file itself.
- Have the agent inspect files itself rather than you copy-pasting content to it.
- Use small, well-bounded tasks rather than open-ended ones.
- Avoid repeated full-project analysis — once Section 4's initial inspection is done and reported, subsequent sessions can reference that report rather than re-inspecting everything from scratch (though a quick re-check after a long gap between sessions is reasonable).
- Don't regenerate already-working code "just to see if it's better" — if it passes its validation step, leave it alone (Section 28 of `PROJECT_GUIDE.md`).

---

## 9. How to prevent compute waste

Especially relevant for Qwen inference, which is genuinely expensive on this hardware:

- Do not repeatedly load the model within a single debugging session — load once, keep the process alive, test the already-loaded model object repeatedly.
- Use one-image smoke tests, not batch runs, while still debugging basic functionality.
- Use small test images during initial debugging; save full-resolution/larger images for the actual experiment runs once the pipeline is confirmed working.
- Avoid repeated downloads — check the Hugging Face cache directory exists and is being hit before assuming a "re-download" is necessary.
- Measure VRAM (`nvidia-smi`) before declaring a configuration works or doesn't — don't guess.
- Stop failing local approaches quickly (Section 17 of `FOR_DEV.md`'s time-boxing) rather than iterating indefinitely on local quantization tweaks.
- Use Colab when the local-vs-Colab decision (`PROJECT_GUIDE.md` Section 15) has genuinely been triggered — don't keep attempting local runs "one more time" past that point.
- Don't run the full experiment suite (Section 20) before the core pipeline (Phases 2–6) is stable — running expensive experiments against a pipeline that's about to change wastes compute on results you'll have to redo.

---

## 10. Context management

When you need the agent's help, prefer giving it the smallest sufficient context:

- **Reference `PROJECT_GUIDE.md` by section number** ("per Section 12") rather than pasting the section's content into your message — the agent can open the file.
- **Reference specific file paths** rather than describing code in prose.
- **Paste error logs directly**, but trim genuinely irrelevant preceding output if the log is very long — keep the actual traceback intact.
- **Use `git diff`** to show the agent exactly what changed in a recent session, rather than re-describing it.
- **Use test outputs** (pass/fail, actual assertion failures) rather than your own summary of "the tests are failing" — let the agent see the real signal.
- **Do not dump the entire repository into context "to be safe."** A well-scoped task needs only the files relevant to that task; a capable agent with file access tools should inspect what it needs rather than receiving everything preemptively.

---

## 11. AI handoff protocol

```
ME prepares (Section 3 checklist)
        ↓
AI inspects (Section 4's first prompt)
        ↓
AI reports status
        ↓
ME reviews and approves the current phase's plan
        ↓
AI implements that phase only
        ↓
AI tests (runs that phase's validation step from PROJECT_GUIDE.md Section 27)
        ↓
AI reports actual results (not "should work" — actual command output)
        ↓
ME reviews, and either approves or sends it back with specific feedback
        ↓
Commit (Section 7's "Git commit" prompt)
        ↓
Next phase
```

Do not skip the "ME reviews" step, especially around Phase 3 (model integration) — this is where fabrication risk and genuine technical uncertainty are both highest, and it's the step where your judgment as the person who understands your actual hardware/constraints matters most.

---

## 12. What AI should never do

- Fabricate metrics, benchmark numbers, or experiment results.
- Fabricate or invent research citations for `RESEARCH_PAPER.md` — every entry in the Related Work table must correspond to a paper the agent (or you) actually found and can point to.
- Invent model APIs or method signatures for the Qwen/PEFT/Transformers stack instead of checking actual installed package versions/documentation.
- Claim GPU compatibility or successful inference without having actually run and observed it.
- Delete data, especially anything under `data/raw/`.
- Overwrite raw/original images under any circumstance — restoration output always goes to `data/processed/`, never back over `data/raw/`.
- Silently change the architecture described in `PROJECT_GUIDE.md` (e.g. swapping SQLite for something else, changing the service separation) without flagging it to you explicitly first and, if you agree, updating `PROJECT_GUIDE.md` itself to reflect the change.
- Install large/heavy packages without a stated reason tied back to Section 9 of `PROJECT_GUIDE.md`.
- Create unnecessary services/infrastructure beyond what's described in the architecture.
- Implement P2/P3 features (Section 26 of `PROJECT_GUIDE.md`) before P0/P1 work for the current phase is done and validated.

---

## 13. Emergency debugging protocol

When the agent (or you) hits an error:

1. **Reproduce** — run the exact failing command again and capture the exact output.
2. **Read the full traceback** — not just the last line; the root cause is often several frames up.
3. **Identify the root cause** — distinguish "this specific line has a bug" from "this reveals a wrong assumption about how a library/model works."
4. **Inspect relevant files** — open the actual file/function involved, don't reason about it from memory of what you assume it contains.
5. **Make the smallest fix** that addresses the root cause — resist the urge to refactor surrounding code at the same time.
6. **Rerun the test/validation step** that originally caught (or would have caught) the issue.
7. **Verify no regression** — rerun other relevant tests/validation steps for that phase, not just the one that failed.
8. **Document if important** — if the bug revealed a wrong assumption worth remembering (e.g. "the LoRA actually expects prompt format X, not Y"), note it in `PROJECT_GUIDE.md` Section 13 or wherever the relevant assumption lives, so future sessions don't re-discover it the hard way.

---

## 14. Model-specific AI workflow

- **Qwen2.5-VL-3B:** confirm exact model identifier/revision used; note it in `RESEARCH_PAPER.md` Section 8 for reproducibility.
- **LoRA adapter:** confirm `lgtk/qwen25vl-3b-modi-synth-lora` loads cleanly via PEFT against the base model; if there's a version/compatibility mismatch, the agent should report the exact error rather than silently trying unrelated workarounds.
- **Transformers:** pin a specific installed version in `requirements.txt` once things work — don't let it float and silently upgrade mid-project.
- **PEFT:** same — confirm compatibility with both the installed Transformers version and the adapter's stated requirements (if any are documented in its repo).
- **bitsandbytes:** treat as the first thing to suspect if quantized loading fails on Windows; this is a known rougher-support area historically — **verify current status rather than assuming either way.**
- **CUDA / VRAM:** always check `nvidia-smi` before and during a test run when debugging memory issues; don't reason about VRAM usage purely from code inspection.
- **CPU offload:** a legitimate intermediate option between "fits fully in VRAM" and "must go to Colab" — the agent should consider `device_map="auto"` with partial CPU offload as a real fallback step, not skip straight from "OOM" to "abandon local entirely," though it shouldn't be over-invested in either if Colab proves simpler.
- **Colab fallback:** the agent can help you write the Colab notebook code and the `colab_client.py` HTTP client, but actually running/managing the Colab session is your manual responsibility (Section 17 of `FOR_DEV.md`) — the agent isn't operating Colab for you.

---

## 15. Recommended Antigravity task sequence

1. Repository inspection (Section 4).
2. Phase 0 confirmation (environment — likely already done manually per Section 3, but re-confirm).
3. Phase 1: project skeleton.
4. Phase 2: OpenCV pipeline.
5. Phase 3: model repository inspection, then model smoke test — the critical phase, decomposed finely (Section 6).
6. Decision point: local vs Colab (your call, informed by the agent's Phase 3 report).
7. Phase 4: backend integration.
8. Phase 5: SQLite archive.
9. Phase 6: full API pipeline.
10. Phase 7: React frontend.
11. Phase 8: evaluation experiment.
12. Phase 9: research artifacts write-up.
13. Phase 10: final polish.
14. Final audit (Section 17).

---

## 16. How I should interact with the agent

**BAD:**
> "make the whole thing better"

**GOOD:**
> "Open `backend/services/restoration/pipeline.py` and inspect the current restoration implementation. Compare it against `PROJECT_GUIDE.md` Section 12. Fix only the identified issue, then run `scripts/smoke_test_opencv.py` and show me the output."

The difference: the good instruction names an exact file, names an exact reference section to check against, bounds the fix to "only the identified issue," and specifies exactly how to validate the result. Apply this pattern to every instruction you give, especially once you're past the initial phase-by-phase scaffolding and into refinement/debugging territory where vague instructions are most tempting and most costly.

---

## 17. Final AI audit prompt

Use this once, shortly before submission (Phase 10), after the Definition of Done checklist (`PROJECT_GUIDE.md` Section 25) has already been informally reviewed by you:

> "Audit the LipiLens repository against `PROJECT_GUIDE.md` in full. Specifically check and report on each of the following, citing the actual files/evidence for each claim (do not just assert things are fine):
> 1. **Architecture** — does the actual code match the architecture described in Sections 6–19? Flag any drift.
> 2. **Code quality** — are route handlers thin (Section 10)? Is service separation respected (Section 8)?
> 3. **Security** — any obvious issues (e.g. accepting arbitrary file uploads without validation, secrets committed to git)?
> 4. **Dependencies** — does `requirements.txt`/`package.json` match what's actually used and needed? Anything unused that should be removed?
> 5. **Tests** — do the tests described in Section 21 exist and actually pass right now? Run them and report real output.
> 6. **UI** — does the frontend implement the three pages per Section 11? Any broken flows?
> 7. **API** — do all endpoints in Section 10 exist and behave as documented? Test them and report real output.
> 8. **Model** — is the inference path (local or Colab) actually working right now, confirmed by an actual test call, not assumed?
> 9. **Database** — does the schema match Section 16? Is `ai_transcription` genuinely immutable in the code path?
> 10. **Research reproducibility** — does every claim in `RESEARCH_PAPER.md` trace to a real file in `experiments/results/`? Flag anything that looks unsupported.
> 11. **README** — accurate and complete?
> 12. **Git state** — is everything committed and pushed? Does `git status` show a clean working tree? Does `.gitignore` correctly exclude venv/weights/secrets/db files — confirm none of those are actually present in `git log`'s history.
>
> Report findings as a checklist with pass/fail/needs-attention for each item. Do not fix anything yet — just report, so I can decide what (if anything) still needs attention with the remaining time."
