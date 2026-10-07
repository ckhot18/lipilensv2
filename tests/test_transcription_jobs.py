"""Tests for the background transcription job and its progress contract.

The UI's only defence against a blank five-minute wait is that
POST /transcribe returns at once and GET /progress reports something true while
the model works, so that pairing is what these tests pin down.
"""

import io
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.api import manuscripts as manuscripts_route
from backend.database.models import Base
from backend.database.session import get_db, make_engine
from backend.main import app
from backend.services import pipeline as pipeline_mod
from backend.services.pipeline import TranscribeOutput
from backend.services.restoration.pipeline import PRESET_CONFIGS
from backend.services.transcription import progress as progress_mod


def _png_bytes(label: str = "page") -> bytes:
    img = np.full((60, 80, 3), 200, dtype=np.uint8)
    cv2.putText(img, label, (5, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (0, 0, 0), 2)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


@pytest.fixture(autouse=True)
def _clean_registry():
    """The job registry is module-level; keep tests independent of each other."""
    with progress_mod._lock:
        progress_mod._jobs.clear()
    yield
    with progress_mod._lock:
        progress_mod._jobs.clear()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path}/jobs.db")
    Base.metadata.create_all(engine)

    def _get_test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db
    # The worker opens its own session, which must be the temp DB too.
    monkeypatch.setattr(
        manuscripts_route, "_new_session",
        lambda: Session(engine),
    )
    # Restoration only: the upload must not try to run the model itself.
    monkeypatch.setattr(
        manuscripts_route.pipeline_mod, "restore_only",
        _fake_restore(tmp_path),
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _fake_restore(tmp_path):
    def _restore(image_path, config_name="full_restoration", output_dir=None,
                 **kwargs):
        out = Path(output_dir or tmp_path)
        out.mkdir(parents=True, exist_ok=True)
        path = out / "restored.png"
        path.write_bytes(_png_bytes("restored"))
        return _Restored(path)

    return _restore


class _Restored:
    def __init__(self, path: Path):
        self.restored_image_path = str(path)
        self.restoration_warning = None


def _stub_transcribe(lines=("पहली ओळ", "दुसरी ओळ", "तिसरी ओळ"),
                     per_line_delay=0.0, fail=False):
    """Stand-in for pipeline.transcribe_only that reports progress like the
    real service does, so the endpoint can be tested without a GPU."""
    def _run(restored_image_path, image_bytes, config_dict, prompt="",
              cache_dir=None, on_progress=None):
        if fail:
            raise RuntimeError("CUDA out of memory")

        def emit(**event):
            if on_progress is not None:
                on_progress(event)

        emit(stage="loading_model")
        emit(stage="model_ready")
        emit(stage="segmenting", lines_total=len(lines))
        collected = []
        for i, text in enumerate(lines, start=1):
            emit(stage="line_start", index=i - 1, lines_total=len(lines))
            if per_line_delay:
                time.sleep(per_line_delay)
            collected.append(text)
            emit(stage="line_done", index=i, lines_total=len(lines),
                 text=text, partial="\n".join(collected))
        return TranscribeOutput(
            transcription="\n".join(collected),
            model_name="stub", inference_mode="stub",
            transcribe_seconds=0.0, cache_hit=False,
        )

    return _run


def _upload_restored(client, label="page", **kwargs):
    files = {"file": ("page.png", io.BytesIO(_png_bytes(label)),
                      "image/png")}
    kwargs.setdefault("transcribe", "false")
    r = client.post("/api/manuscripts", files=files, data=kwargs)
    assert r.status_code == 200, r.text
    return r.json()


def _await_progress(client, manuscript_id, timeout=10.0):
    """Poll /progress the way the browser does until the job settles."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = client.get(f"/api/manuscripts/{manuscript_id}/progress")
        assert r.status_code == 200, r.text
        last = r.json()
        if last["done"]:
            return last
        time.sleep(0.05)
    raise AssertionError(f"job never settled; last={last}")


# ---------------------------------------------------------------------------
# Progress registry (unit)
# ---------------------------------------------------------------------------
def test_progress_reports_line_by_line_and_settles_at_100():
    job = progress_mod.start_job(7)
    job.apply({"stage": "loading_model"})
    assert job.snapshot()["state"] == "running"

    job.apply({"stage": "model_ready"})
    assert job.snapshot()["percent"] == 15

    job.apply({"stage": "segmenting", "lines_total": 4})
    job.apply({"stage": "line_start", "index": 0, "lines_total": 4})
    assert job.snapshot()["percent"] == 15  # nothing read yet

    job.apply({"stage": "line_done", "index": 1, "lines_total": 4,
               "text": "एक", "partial": "एक"})
    snap = job.snapshot()
    assert snap["lines_done"] == 1
    assert snap["lines_total"] == 4
    assert snap["partial_text"] == "एक"
    assert snap["percent"] == int(15 + 85 * 1 / 4)

    job.finish("एक\nदो")
    snap = job.snapshot()
    assert snap["state"] == "done"
    assert snap["percent"] == 100
    assert snap["done"] is True
    assert snap["partial_text"] == "एक\nदो"


def test_progress_failure_keeps_the_error_and_is_terminal():
    job = progress_mod.start_job(8)
    job.apply({"stage": "line_done", "index": 1, "lines_total": 2,
               "text": "एक", "partial": "एक"})
    job.fail("RuntimeError: CUDA out of memory")
    snap = job.snapshot()
    assert snap["state"] == "failed"
    assert snap["done"] is True
    assert "CUDA out of memory" in snap["error"]
    # A failed run must not claim to have finished the whole page.
    assert snap["percent"] < 100


def test_eta_only_appears_once_a_line_has_been_read():
    job = progress_mod.start_job(9)
    job.apply({"stage": "segmenting", "lines_total": 4})
    assert job.snapshot()["eta_s"] == 0.0
    job.apply({"stage": "line_done", "index": 1, "lines_total": 4,
               "text": "एक", "partial": "एक"})
    assert job.snapshot()["eta_s"] == 0.0  # unknown cost of an unread line


def _job_reading(seconds_per_line, total):
    """A job whose `seconds_per_line` lines have completed, out of `total`."""
    job = progress_mod.start_job(13)
    job.apply({"stage": "segmenting", "lines_total": total})
    for i, secs in enumerate(seconds_per_line, start=1):
        job.apply({"stage": "line_start", "index": i - 1})
        job._open_line_at -= secs
        job.apply({"stage": "line_done", "index": i, "lines_total": total,
                   "text": f"line{i}", "partial": f"line{i}"})
    return job


def test_eta_ignores_the_model_load():
    """A 60 s cold load must not be charged to the first line."""
    job = _job_reading([10], total=4)
    job.started_at -= 60.0
    # 3 unread lines at the measured 10 s each.
    assert job.snapshot()["eta_s"] == 30.0


def test_eta_counts_down_instead_of_up_while_a_line_is_read():
    job = _job_reading([10, 10], total=4)
    before = job.snapshot()["eta_s"]
    assert before == 20.0

    # A third line opens and time passes; the estimate must not creep up.
    job.apply({"stage": "line_start", "index": 2, "lines_total": 4})
    job._open_line_at -= 25.0
    assert job.snapshot()["eta_s"] == before


def test_eta_is_zero_when_everything_is_read():
    job = _job_reading([10, 10], total=2)
    assert job.snapshot()["eta_s"] == 0.0


def test_elapsed_still_covers_the_model_load():
    job = progress_mod.start_job(12)
    job.started_at -= 60.0
    assert job.snapshot()["elapsed_s"] >= 59


def test_idle_snapshot_reports_a_stored_transcription_as_done():
    snap = progress_mod.idle_snapshot(3, "साठवलेले मजकूर")
    assert snap["state"] == "done"
    assert snap["done"] is True
    assert snap["percent"] == 100
    assert snap["partial_text"] == "साठवलेले मजकूर"


def test_idle_snapshot_without_text_is_not_done():
    snap = progress_mod.idle_snapshot(3)
    assert snap["state"] == "queued"
    assert snap["done"] is False


def test_progress_names_the_line_being_read():
    """The headline must read as prose, not echo the internal stage name."""
    job = progress_mod.start_job(10)
    job.apply({"stage": "segmenting", "lines_total": 3})
    job.apply({"stage": "line_start", "index": 0, "lines_total": 3})
    assert job.snapshot()["message"] == "Reading line 1 of 3"
    job.apply({"stage": "line_done", "index": 1, "lines_total": 3,
               "text": "एक", "partial": "एक"})
    assert job.snapshot()["message"] == "Read 1 of 3 lines"
    job.apply({"stage": "line_start", "index": 1, "lines_total": 3})
    assert job.snapshot()["message"] == "Reading line 2 of 3"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
def test_transcribe_returns_202_before_the_model_finishes(client, monkeypatch):
    monkeypatch.setattr(manuscripts_route.pipeline_mod, "transcribe_only",
                        _stub_transcribe(per_line_delay=0.4))
    ms = _upload_restored(client)

    started = time.perf_counter()
    r = client.post(f"/api/manuscripts/{ms['id']}/transcribe")
    elapsed = time.perf_counter() - started

    assert r.status_code == 202, r.text
    # The whole point: the request must not wait on the model.
    assert elapsed < 2.0
    assert r.json()["transcription"] is None

    final = _await_progress(client, ms["id"])
    assert final["state"] == "done"
    assert final["percent"] == 100
    assert final["lines_total"] == 3


def test_progress_streams_partial_text_while_reading(client, monkeypatch):
    monkeypatch.setattr(manuscripts_route.pipeline_mod, "transcribe_only",
                        _stub_transcribe(per_line_delay=0.3))
    ms = _upload_restored(client)
    client.post(f"/api/manuscripts/{ms['id']}/transcribe")

    seen = []
    deadline = time.time() + 10
    while time.time() < deadline:
        snap = client.get(f"/api/manuscripts/{ms['id']}/progress").json()
        if snap["partial_text"]:
            seen.append(snap["partial_text"])
        if snap["done"]:
            break
        time.sleep(0.05)

    # Partial text must grow, not appear only at the end.
    assert seen, "progress never reported any partial text"
    assert seen == sorted(seen, key=len), f"partial text regressed: {seen}"
    assert seen[-1].count("\n") == 2


def test_completed_job_lands_the_transcription_in_the_archive(client,
                                                              monkeypatch):
    monkeypatch.setattr(manuscripts_route.pipeline_mod, "transcribe_only",
                        _stub_transcribe())
    ms = _upload_restored(client)
    client.post(f"/api/manuscripts/{ms['id']}/transcribe")
    _await_progress(client, ms["id"])

    detail = client.get(f"/api/manuscripts/{ms['id']}").json()
    assert detail["status"] == "transcribed"
    assert detail["transcription"]["ai_transcription"] == "पहली ओळ\nदुसरी ओळ\nतिसरी ओळ"


def test_failed_job_reports_the_error_and_keeps_the_manuscript(client,
                                                               monkeypatch):
    monkeypatch.setattr(manuscripts_route.pipeline_mod, "transcribe_only",
                        _stub_transcribe(fail=True))
    ms = _upload_restored(client, title="Doomed page")
    client.post(f"/api/manuscripts/{ms['id']}/transcribe")

    snap = _await_progress(client, ms["id"])
    assert snap["state"] == "failed"
    assert "CUDA out of memory" in snap["error"]
    # Restoration output must survive a failed read.
    detail = client.get(f"/api/manuscripts/{ms['id']}").json()
    assert detail["status"] == "restored"
    assert detail["transcription"] is None
    assert detail["restored_image_url"]


def test_second_request_joins_the_running_job(client, monkeypatch):
    calls = []
    stub = _stub_transcribe(per_line_delay=0.4)

    def counting(*args, **kwargs):
        calls.append(1)
        return stub(*args, **kwargs)

    monkeypatch.setattr(manuscripts_route.pipeline_mod, "transcribe_only",
                        counting)
    ms = _upload_restored(client)

    client.post(f"/api/manuscripts/{ms['id']}/transcribe")
    time.sleep(0.2)
    again = client.post(f"/api/manuscripts/{ms['id']}/transcribe")
    assert again.status_code == 202
    _await_progress(client, ms["id"])

    # One model run, not two: loading twice would not fit in 4 GB.
    assert len(calls) == 1


def test_re_reading_a_finished_page_returns_the_stored_text(client,
                                                            monkeypatch):
    monkeypatch.setattr(manuscripts_route.pipeline_mod, "transcribe_only",
                        _stub_transcribe())
    ms = _upload_restored(client)
    client.post(f"/api/manuscripts/{ms['id']}/transcribe")
    _await_progress(client, ms["id"])

    again = client.post(f"/api/manuscripts/{ms['id']}/transcribe")
    assert again.status_code == 202
    assert again.json()["transcription"]["ai_transcription"] == (
        "पहली ओळ\nदुसरी ओळ\nतिसरी ओळ"
    )


def test_progress_falls_back_to_the_archive_when_no_job_is_tracked(client):
    ms = _upload_restored(client)
    snap = client.get(f"/api/manuscripts/{ms['id']}/progress").json()
    assert snap["done"] is False
    assert snap["state"] == "queued"
    assert snap["partial_text"] == ""


def test_progress_404s_for_an_unknown_manuscript(client):
    assert client.get("/api/manuscripts/9999/progress").status_code == 404


def test_transcribe_still_409s_without_a_restored_image(client, monkeypatch):
    monkeypatch.setattr(manuscripts_route.pipeline_mod, "restore_only",
                        _raise_no_restore())
    files = {"file": ("page.png", io.BytesIO(_png_bytes("x")), "image/png")}
    r = client.post("/api/manuscripts", files=files,
                    data={"transcribe": "false"})
    assert r.status_code == 200
    # No restored image: the two-act flow cannot start.
    r = client.post(f"/api/manuscripts/{r.json()['id']}/transcribe")
    assert r.status_code == 409


def _raise_no_restore():
    class _NoRestore:
        restored_image_path = None
        restoration_warning = None
    return lambda *a, **k: _NoRestore()


def test_health_still_reports_ok_while_a_job_runs(client, monkeypatch):
    monkeypatch.setattr(manuscripts_route.pipeline_mod, "transcribe_only",
                        _stub_transcribe(per_line_delay=0.3))
    ms = _upload_restored(client)
    client.post(f"/api/manuscripts/{ms['id']}/transcribe")

    body = client.get("/api/health").json()
    assert body["status"] in ("ok", "degraded")
    assert body["inference_mode"] == "local"
    _await_progress(client, ms["id"])


def test_preset_config_is_resolved_for_the_worker(client, monkeypatch):
    """The worker must read the manuscript's own config, not a hard-coded one."""
    seen = {}
    stub = _stub_transcribe()

    def spy(restored_image_path, image_bytes, config_dict, prompt="",
            cache_dir=None, on_progress=None):
        seen["config_dict"] = config_dict
        return stub(restored_image_path, image_bytes, config_dict, prompt,
                    cache_dir, on_progress)

    monkeypatch.setattr(manuscripts_route.pipeline_mod, "transcribe_only",
                        spy)
    ms = _upload_restored(client, config_name="binarized")
    client.post(f"/api/manuscripts/{ms['id']}/transcribe")
    _await_progress(client, ms["id"])

    assert seen["config_dict"] == PRESET_CONFIGS["binarized"].to_dict()