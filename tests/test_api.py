"""API tests (Phase 6) — temp DB + stubbed transcription, real HTTP stack."""

import io
import sys
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
from backend.services.pipeline import PipelineOutput
from backend.services.restoration.pipeline import PRESET_CONFIGS


def _png_bytes(label: str = "test") -> bytes:
    img = np.full((60, 80, 3), 200, dtype=np.uint8)
    cv2.putText(img, label, (5, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (0, 0, 0), 2)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path}/api.db")
    Base.metadata.create_all(engine)

    def _get_test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db

    def _fake_pipeline(image_path, config_name="full_restoration",
                       output_dir=None, prompt="", cache_dir=None):
        out_path = Path(output_dir or tmp_path)
        out_path.mkdir(parents=True, exist_ok=True)
        fake_restored = out_path / "restored.png"
        fake_restored.write_bytes(_png_bytes())
        return PipelineOutput(
            config_name=config_name, config_dict={"name": config_name},
            source_image=str(image_path), image_sha256="abc",
            restored_image_path=str(fake_restored),
            transcription="stub transcription", model_name="stub",
            inference_mode="stub", prompt=prompt,
            restore_seconds=0.1, transcribe_seconds=0.2)

    monkeypatch.setattr(manuscripts_route.pipeline_mod, "run_full_pipeline",
                        _fake_pipeline)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _upload(client, img_label: str = "test", **kwargs):
    files = {"file": ("page.png", io.BytesIO(_png_bytes(img_label)),
                      "image/png")}
    return client.post("/api/manuscripts", files=files, data=kwargs)


def test_upload_happy_path(client):
    r = _upload(client, title="Test page", config_name="enhanced")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"] == "Test page"
    assert body["status"] == "transcribed"
    assert body["original_image_url"].endswith("original.png")
    assert body["restored_image_url"].endswith("restored.png")
    assert body["transcription"]["ai_transcription"] == "stub transcription"
    assert body["transcription"]["verification_status"] == "pending"


def test_upload_rejects_non_image(client):
    r = client.post("/api/manuscripts",
                    files={"file": ("x.txt", io.BytesIO(b"hello"),
                                    "text/plain")})
    assert r.status_code == 400


def test_upload_rejects_bad_config(client):
    r = _upload(client, config_name="nope")
    assert r.status_code == 400


def test_get_search_verify_flow(client):
    up = _upload(client, title="Shivaji letter").json()
    mid, tid = up["id"], up["transcription"]["id"]

    got = client.get(f"/api/manuscripts/{mid}")
    assert got.status_code == 200
    assert got.json()["transcription"]["ai_transcription"] == \
        "stub transcription"

    assert client.get("/api/manuscripts/9999").status_code == 404

    found = client.get("/api/manuscripts", params={"search": "Shivaji"})
    assert [m["id"] for m in found.json()] == [mid]
    assert client.get("/api/manuscripts",
                      params={"search": "nothing-here"}).json() == []

    v = client.put(f"/api/transcriptions/{tid}/verify",
                   json={"verified_transcription": "corrected"})
    assert v.status_code == 200
    assert v.json()["verified_transcription"] == "corrected"
    assert v.json()["verification_status"] == "verified"

    # AI draft immutable through the API too.
    again = client.get(f"/api/manuscripts/{mid}").json()
    assert again["status"] == "verified"
    assert again["transcription"]["ai_transcription"] == "stub transcription"

    assert client.put("/api/transcriptions/9999/verify",
                      json={"verified_transcription": "x"}).status_code == 404


def test_verify_rejects_empty_text(client):
    tid = _upload(client).json()["transcription"]["id"]
    assert client.put(f"/api/transcriptions/{tid}/verify",
                      json={"verified_transcription": ""}).status_code == 422


def test_transcription_failure_preserves_manuscript(client, monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("model down")

    monkeypatch.setattr(manuscripts_route.pipeline_mod, "run_full_pipeline",
                        _boom)
    r = _upload(client, title="Doomed page")
    assert r.status_code == 503
    # Manuscript + original image survived (restoration stage completed).
    found = client.get("/api/manuscripts", params={"search": "Doomed"})
    assert len(found.json()) == 1


def test_duplicate_upload_returns_existing(client):
    first = _upload(client, title="Original").json()
    assert first["duplicate"] is False
    second = _upload(client, title="Original").json()
    assert second["id"] == first["id"]
    assert second["duplicate"] is True
    # Same bytes but different config is a genuinely new record.
    third = _upload(client, title="Original",
                    config_name="enhanced").json()
    assert third["id"] != first["id"]
    assert third["duplicate"] is False


def test_pagination(client):
    for i in range(3):
        _upload(client, img_label=f"page-{i}", title=f"Page {i}")
    all_rows = client.get("/api/manuscripts").json()
    assert len(all_rows) == 3
    assert len(client.get("/api/manuscripts",
                          params={"limit": 2}).json()) == 2
    assert len(client.get("/api/manuscripts",
                          params={"limit": 2, "offset": 2}).json()) == 1
    assert client.get("/api/manuscripts",
                      params={"limit": 0}).status_code == 400
    assert client.get("/api/manuscripts",
                      params={"limit": 500}).status_code == 400


def test_health_reports_inference_mode(client, monkeypatch):
    import requests

    def _fake_get(*args, **kwargs):
        class _R:
            status_code = 200

            def json(self):
                return {"status": "ok", "model_loaded": True}

        return _R()

    monkeypatch.setattr(requests, "get", _fake_get)
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    from backend import config as app_config
    assert body["inference_mode"] == app_config.INFERENCE_MODE
    if app_config.INFERENCE_MODE == "colab":
        assert body["colab_reachable"] is True
        assert body["colab_model_loaded"] is True
