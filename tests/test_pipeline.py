"""Tests for the Phase-4 integration pipeline (offline — stubbed model)."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest

import backend.services.pipeline as pipe_mod
from backend.services.pipeline import run_full_pipeline
from backend.services.transcription.inference import TranscriptionResult

SAMPLE = PROJECT_ROOT / "data" / "raw" / "mode_trans" / "MT-002.png"


class StubService:
    """Fake transcription service: records what image it was given."""

    def __init__(self):
        self.seen_paths = []
        self.calls = 0

    def transcribe(self, image_path, prompt):
        self.calls += 1
        self.seen_paths.append(str(image_path))
        assert Path(image_path).exists(), "model must receive a real file"
        assert isinstance(prompt, str) and prompt
        return TranscriptionResult(text="stub", model_name="stub",
                                   inference_mode="stub")


@pytest.fixture(autouse=True)
def _fresh_service_cache():
    pipe_mod.clear_service_cache()
    yield
    pipe_mod.clear_service_cache()


def test_pipeline_sends_restored_file_to_model(tmp_path, monkeypatch):
    stub = StubService()
    monkeypatch.setattr(pipe_mod, "get_transcription_service", lambda: stub)
    out = run_full_pipeline(SAMPLE, "enhanced", output_dir=tmp_path)
    assert out.config_name == "enhanced"
    assert out.transcription == "stub"
    assert out.restoration_warning is None
    # The model must receive the RESTORED file, not the original.
    assert stub.seen_paths == [out.restored_image_path]
    assert "enhanced" in out.restored_image_path


def test_pipeline_falls_back_to_original_on_restoration_failure(
        tmp_path, monkeypatch):
    stub = StubService()
    monkeypatch.setattr(pipe_mod, "get_transcription_service", lambda: stub)

    def _boom(image, config):
        raise RuntimeError("simulated stage failure")

    monkeypatch.setattr(pipe_mod, "run_pipeline", _boom)
    out = run_full_pipeline(SAMPLE, "binarized", output_dir=tmp_path)
    assert out.transcription == "stub"  # pipeline survived
    assert out.restoration_warning is not None
    assert "binarized" in out.restoration_warning


def test_pipeline_rejects_unknown_config(tmp_path):
    with pytest.raises(ValueError):
        run_full_pipeline(SAMPLE, "nonexistent_config", output_dir=tmp_path)


def test_service_instance_reused_across_calls(tmp_path, monkeypatch):
    stub = StubService()
    factory_calls = []
    monkeypatch.setattr(
        pipe_mod, "get_transcription_service",
        lambda: factory_calls.append(1) or stub)
    run_full_pipeline(SAMPLE, "grayscale", output_dir=tmp_path)
    run_full_pipeline(SAMPLE, "grayscale", output_dir=tmp_path)
    assert stub.calls == 2  # both transcriptions happened...
    assert len(factory_calls) == 1, "service must be created once and reused"


def test_transcription_cache_skips_second_model_call(tmp_path, monkeypatch):
    stub = StubService()
    monkeypatch.setattr(pipe_mod, "get_transcription_service", lambda: stub)
    cache = tmp_path / "tcache"
    out1 = run_full_pipeline(SAMPLE, "enhanced", output_dir=tmp_path,
                             cache_dir=cache)
    out2 = run_full_pipeline(SAMPLE, "enhanced", output_dir=tmp_path,
                             cache_dir=cache)
    assert stub.calls == 1, "second run must not call the model"
    assert out1.cache_hit is False
    assert out2.cache_hit is True
    assert out2.transcription == out1.transcription == "stub"
    assert out2.image_sha256 == out1.image_sha256


def test_pipeline_output_is_json_safe(tmp_path, monkeypatch):
    import json

    stub = StubService()
    monkeypatch.setattr(pipe_mod, "get_transcription_service", lambda: stub)
    out = run_full_pipeline(SAMPLE, "denoised", output_dir=tmp_path)
    d = out.to_dict()
    json.dumps(d)  # must not raise
    assert d["config_dict"]["name"] == "denoised"
    assert len(d["image_sha256"]) == 64
