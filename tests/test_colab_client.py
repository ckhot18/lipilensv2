"""Tests for the Colab fallback client (Phase 3).

Uses a local stdlib stub server that mimics the Colab endpoint's contract
(POST /transcribe {image, prompt} -> {transcription}), so the client's
encode-POST-parse path is verified with zero GPU/network dependency.
"""

import base64
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.transcription import colab_client
from backend.services.transcription.inference import get_transcription_service

SAMPLE_IMAGE = PROJECT_ROOT / "data" / "raw" / "sample_modi_page.png"
STUB_TEXT = "stub transcription output"


class _StubHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        assert self.path == "/transcribe", self.path
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length))
        # Contract: base64 image decodes to real bytes, prompt is a string.
        raw = base64.b64decode(payload["image"])
        assert raw[:4] == b"\x89PNG", f"expected PNG bytes, got {raw[:4]!r}"
        assert isinstance(payload["prompt"], str) and payload["prompt"]
        body = json.dumps({"transcription": STUB_TEXT}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # keep test output clean


def _start_stub():
    server = HTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_colab_client_round_trips_through_stub():
    assert SAMPLE_IMAGE.exists()
    server = _start_stub()
    try:
        colab_client.COLAB_ENDPOINT_URL = (
            f"http://127.0.0.1:{server.server_port}"
        )
        svc = colab_client.ColabTranscriptionService()
        result = svc.transcribe(SAMPLE_IMAGE, "test prompt")
        assert result.text == STUB_TEXT
        assert result.inference_mode == "colab"
    finally:
        server.shutdown()


def test_colab_client_requires_endpoint_url():
    colab_client.COLAB_ENDPOINT_URL = ""
    svc = colab_client.ColabTranscriptionService()
    try:
        svc.transcribe(SAMPLE_IMAGE, "test prompt")
        raise AssertionError("expected ValueError for missing endpoint URL")
    except ValueError:
        pass  # expected


def test_dispatcher_selects_colab(monkeypatch):
    import backend.config as app_config

    monkeypatch.setattr(app_config, "INFERENCE_MODE", "colab")
    svc = get_transcription_service()
    assert isinstance(svc, colab_client.ColabTranscriptionService)


def test_dispatcher_selects_local(monkeypatch):
    import backend.config as app_config
    from backend.services.transcription.local_qwen import (
        LocalQwenTranscriptionService,
    )

    monkeypatch.setattr(app_config, "INFERENCE_MODE", "local")
    svc = get_transcription_service()
    assert isinstance(svc, LocalQwenTranscriptionService)


def test_dispatcher_rejects_unknown_mode(monkeypatch):
    import backend.config as app_config

    monkeypatch.setattr(app_config, "INFERENCE_MODE", "tpu")
    try:
        get_transcription_service()
        raise AssertionError("expected ValueError for unknown mode")
    except ValueError:
        pass  # expected
