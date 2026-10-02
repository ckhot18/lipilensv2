"""Line segmentation: the token-budget fix for transcription accuracy."""

import cv2
import numpy as np
import pytest

from backend.services.transcription.segment import (
    MAX_MODEL_PIXELS,
    find_text_bands,
    segment_lines,
    write_lines,
)
from backend.services.transcription.inference import (
    LineSegmentedTranscriptionService,
    TranscriptionResult,
)


def _synthetic_page(lines: int = 4, width: int = 1268, height: int = 463):
    page = np.full((height, width), 255, np.uint8)
    band = height // (lines + 1)
    for i in range(lines):
        top = (i + 1) * band - band // 3
        cv2.line(page, (20, top), (width - 20, top), 0, 3)
        for x in range(30, width - 30, 26):
            cv2.line(page, (x, top), (x, top - band // 2), 0, 3)
    return page


def _merged_tokens(w: int, h: int) -> int:
    return int(min(w * h, MAX_MODEL_PIXELS)) // (28 * 28) // 4


def test_finds_one_band_per_text_line(tmp_path):
    page = _synthetic_page(lines=4)
    path = tmp_path / "page.png"
    cv2.imwrite(str(path), page)
    assert len(find_text_bands(cv2.imread(str(path), 0))) == 4


def test_finds_single_band_for_one_line(tmp_path):
    page = _synthetic_page(lines=1)
    path = tmp_path / "page.png"
    cv2.imwrite(str(path), page)
    assert len(find_text_bands(cv2.imread(str(path), 0))) == 1


def test_blank_image_falls_back_to_whole_page(tmp_path):
    path = tmp_path / "blank.png"
    cv2.imwrite(str(path), np.full((200, 200), 255, np.uint8))
    lines = segment_lines(path)
    assert len(lines) == 1
    assert lines[0].shape == (200, 200)


def test_missing_file_returns_nothing():
    assert segment_lines("does-not-exist.png") == []


def test_segmentation_multiplies_tokens_available():
    """The whole point: more visual tokens for the same characters."""
    page = _synthetic_page(lines=6)
    path = "synthetic_page.png"
    cv2.imwrite(path, page)
    try:
        whole = _merged_tokens(page.shape[1], page.shape[0])
        lines = segment_lines(path)
        per_line = sum(_merged_tokens(l.shape[1], l.shape[0]) for l in lines)
        assert len(lines) == 6
        assert per_line > whole * 2
    finally:
        import os

        if os.path.exists(path):
            os.remove(path)


def test_write_lines_creates_one_file_per_line(tmp_path):
    page = _synthetic_page(lines=3)
    src = tmp_path / "page.png"
    cv2.imwrite(str(src), page)
    paths = write_lines(segment_lines(src), tmp_path / "lines")
    assert len(paths) == 3
    assert all(p.exists() for p in paths)


class _StubService:
    """Records every image it is handed and returns a fixed token."""

    def __init__(self):
        self.calls = 0

    def transcribe(self, image_path, prompt):
        self.calls += 1
        img = cv2.imread(str(image_path), 0)
        assert img is not None and img.size > 0
        return TranscriptionResult(
            text=f"line{self.calls}",
            model_name="stub",
            inference_mode="colab",
        )


def test_wrapper_transcribes_each_line_and_joins(tmp_path):
    page = _synthetic_page(lines=3)
    src = tmp_path / "page.png"
    cv2.imwrite(str(src), page)

    inner = _StubService()
    result = LineSegmentedTranscriptionService(inner).transcribe(src, "p")

    assert inner.calls == 3
    assert result.text == "line1\nline2\nline3"
    assert result.line_count == 3
    assert "line segmentation" in result.model_name


def test_wrapper_passes_through_single_line_pages(tmp_path):
    page = _synthetic_page(lines=1)
    src = tmp_path / "page.png"
    cv2.imwrite(str(src), page)

    inner = _StubService()
    result = LineSegmentedTranscriptionService(inner).transcribe(src, "p")

    assert inner.calls == 1
    assert result.line_count == 1


def test_wrapper_skips_blank_lines(tmp_path):
    page = _synthetic_page(lines=2)
    src = tmp_path / "page.png"
    cv2.imwrite(str(src), page)

    inner = _StubService()
    result = LineSegmentedTranscriptionService(inner).transcribe(src, "p")
    assert "\n" in result.text or result.text.startswith("line")
    assert inner.calls >= 1


def test_wrapper_falls_back_when_every_line_fails(tmp_path):
    page = _synthetic_page(lines=3)
    src = tmp_path / "page.png"
    cv2.imwrite(str(src), page)

    class _Failing(_StubService):
        def transcribe(self, image_path, prompt):
            if str(image_path).endswith("page.png"):
                return TranscriptionResult(
                    text="whole page", model_name="stub",
                    inference_mode="colab",
                )
            raise RuntimeError("line failed")

    result = LineSegmentedTranscriptionService(_Failing()).transcribe(src, "p")
    assert result.text == "whole page"
    assert result.line_count == 1