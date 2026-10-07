"""In-process registry of transcription jobs so the UI can watch one run.

Transcription is the only slow act in LipiLens: the model loads on first use
(~60-95 s) and then every text line costs ~25 s on a 4 GB GPU, so a nine-line
page runs for five minutes. A single blocking request gives the browser nothing
to show for all of that, so the work runs on a background thread and this
module keeps the state the frontend polls.

Deliberately in-process and in-memory: the archive row is still written once,
atomically, at the end of a run. Nothing here is a source of truth, so a server
restart loses the live view (not the result) and /progress falls back to the
database.
"""

import threading
import time
from typing import Any, Callable

# Job lifecycle.
QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"

# Stages, in the order a healthy run passes through them. `percent` is the
# fraction of the bar the stage is worth, so the two phases line up:
# loading the model is a known ~90 s, reading is known per line.
STAGE_PERCENT = {
    "queued": 0,
    "loading_model": 5,
    "segmenting": 15,
    "reading": 85,
}
MODEL_READY_PERCENT = 15

STAGE_LABELS = {
    "queued": "Waiting to start",
    "loading_model": "Loading the model onto the GPU",
    "model_ready": "Model ready",
    "segmenting": "Finding the text lines",
    "reading": "Reading the manuscript",
    "done": "Done",
}

# Per-line events all mean "we are in the reading stage"; the bar and the
# label must not change three times within one line.
_STAGE_ALIASES = {
    "line_start": "reading",
    "line_done": "reading",
    "line_failed": "reading",
}

TERMINAL_STATES = frozenset({DONE, FAILED})

# Finished jobs are kept briefly so a late poll still sees the result; they are
# pruned on the way into a new job so the registry cannot grow without bound.
_RETENTION_SECONDS = 1800
_MAX_TRACKED = 64

# perf_counter, not time.time(): on Windows time.time() only ticks every ~15 ms,
# which is coarse enough to report 0 s elapsed and a 0 s ETA on the first line.
_now = time.perf_counter

_lock = threading.Lock()
_jobs: dict[int, "TranscriptionJob"] = {}


def _prune_locked(now: float) -> None:
    stale = [
        mid for mid, job in _jobs.items()
        if job.state in TERMINAL_STATES and job.finished_at
        and now - job.finished_at > _RETENTION_SECONDS
    ]
    for mid in stale:
        del _jobs[mid]
    # Hard cap in case many jobs fail instantly and stay inside the window.
    if len(_jobs) > _MAX_TRACKED:
        ordered = sorted(
            _jobs.items(),
            key=lambda kv: kv[1].started_at or 0.0,
        )
        for mid, _ in ordered[: len(_jobs) - _MAX_TRACKED]:
            _jobs.pop(mid, None)


def start_job(manuscript_id: int) -> "TranscriptionJob":
    """Register a fresh job for this manuscript and return it."""
    now = _now()
    with _lock:
        _prune_locked(now)
        job = TranscriptionJob(manuscript_id=manuscript_id, started_at=now)
        _jobs[manuscript_id] = job
        return job


def get_job(manuscript_id: int) -> "TranscriptionJob | None":
    with _lock:
        return _jobs.get(manuscript_id)


def is_running(manuscript_id: int) -> bool:
    job = get_job(manuscript_id)
    return job is not None and job.state not in TERMINAL_STATES


class TranscriptionJob:
    """Mutable progress record for one transcription run.

    Mutated only by the worker thread; every read goes through `snapshot()`,
    which copies under the lock so a poll can never observe a half-updated
    set of fields.
    """

    def __init__(self, manuscript_id: int, started_at: float | None = None):
        self.manuscript_id = manuscript_id
        self.state = QUEUED
        self.stage = "queued"
        self.message = STAGE_LABELS["queued"]
        self.lines_total = 0
        self.lines_done = 0
        self.partial_text = ""
        self.last_line = ""
        self.error = ""
        self.started_at = started_at or _now()
        self.finished_at: float | None = None
        # Timing for the ETA. Only *completed* lines are measured: averaging
        # cumulative reading time would keep growing the estimate while a line
        # is in flight, so the number would count up instead of down.
        self._open_line_at: float | None = None
        self._line_intervals: list[float] = []

    # -- worker-side updates -------------------------------------------------
    def apply(self, event: dict[str, Any]) -> None:
        """Fold one progress event from the service layer into the job."""
        stage = event.get("stage")
        if not stage:
            return

        with _lock:
            self.state = RUNNING
            self.stage = _STAGE_ALIASES.get(stage, stage)
            if stage == "line_start":
                self._open_line_at = _now()
            elif stage in ("line_done", "line_failed") and (
                    self._open_line_at is not None):
                self._line_intervals.append(_now() - self._open_line_at)
                self._open_line_at = None
            if event.get("lines_total") is not None:
                self.lines_total = int(event["lines_total"])
            if event.get("index") is not None:
                self.lines_done = int(event["index"])
            if stage == "line_done":
                text = (event.get("text") or "").strip()
                if text:
                    self.last_line = text
                    # `partial` is authoritative: it is the exact string the
                    # worker will eventually store, so the UI can show it.
                    self.partial_text = event.get("partial") or self.partial_text
                self.message = (
                    f"Read {self.lines_done} of {self.lines_total} lines"
                    if self.lines_total
                    else f"Read {self.lines_done} lines"
                )
            elif stage == "line_failed":
                self.message = (
                    f"Line {self.lines_done} of {self.lines_total} could not be "
                    "read; continuing"
                )
            elif stage == "line_start":
                self.message = (
                    f"Reading line {self.lines_done + 1} of {self.lines_total}"
                    if self.lines_total
                    else "Reading a line"
                )
            else:
                self.message = event.get("message") or STAGE_LABELS.get(
                    stage, stage.replace("_", " ").capitalize()
                )

    def finish(self, partial_text: str = "") -> None:
        with _lock:
            if partial_text:
                self.partial_text = partial_text
            self.state = DONE
            self.stage = "done"
            self.message = STAGE_LABELS["done"]
            self.lines_done = self.lines_total or self.lines_done
            self.finished_at = _now()

    def fail(self, message: str) -> None:
        with _lock:
            self.state = FAILED
            self.message = message
            self.error = message
            self.finished_at = _now()

    # -- reader side ---------------------------------------------------------
    def percent(self) -> int:
        if self.state == DONE:
            return 100
        if self.state == QUEUED:
            return 0
        if self.stage in ("model_ready", "segmenting"):
            return MODEL_READY_PERCENT
        if self.stage == "reading" and self.lines_total:
            floor = MODEL_READY_PERCENT
            return int(floor + STAGE_PERCENT["reading"] * self.lines_done
                       / self.lines_total)
        return STAGE_PERCENT.get(self.stage, 5)

    def snapshot(self) -> dict[str, Any]:
        with _lock:
            end = self.finished_at or _now()
            elapsed = max(0.0, end - self.started_at)
            per_line = (
                sum(self._line_intervals) / len(self._line_intervals)
                if self._line_intervals else None
            )
            remaining = max(0, self.lines_total - self.lines_done)
            eta = per_line * remaining if per_line and remaining else 0.0
            return {
                "manuscript_id": self.manuscript_id,
                "state": self.state,
                "stage": self.stage,
                "message": self.message,
                "percent": self.percent(),
                "lines_total": self.lines_total,
                "lines_done": self.lines_done,
                "partial_text": self.partial_text,
                "last_line": self.last_line,
                "error": self.error,
                "elapsed_s": round(elapsed, 1),
                "eta_s": round(eta, 1),
                "done": self.state in TERMINAL_STATES,
            }


def make_callback(job: TranscriptionJob) -> Callable[[dict[str, Any]], None]:
    """Bind a job to a service-layer progress callback."""
    return job.apply


def idle_snapshot(manuscript_id: int, text: str | None = None) -> dict[str]:
    """Snapshot for a manuscript that has no live job.

    After a server restart the registry is empty but the archive row may
    already hold a transcription, so the endpoint derives the truth from the
    database and reports it in the same shape the poller already understands.
    """
    job = TranscriptionJob(manuscript_id=manuscript_id)
    if text:
        job.partial_text = text
        job.state = DONE
        job.stage = "done"
        job.message = STAGE_LABELS["done"]
        job.finished_at = job.started_at
        return job.snapshot()
    job.message = "No transcription in progress"
    return job.snapshot()