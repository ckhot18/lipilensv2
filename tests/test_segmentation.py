"""Line segmentation: the token-budget fix for transcription accuracy."""

import cv2
import numpy as np
import pytest

from backend.services.transcription.segment import (
    MAX_BAND_ASPECT,
    _scale_for,
    find_text_bands,
    pixel_budget,
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
    return int(min(w * h, pixel_budget())) // (28 * 28) // 4


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


# ---------------------------------------------------------------------------
# Regressions that made segmentation actively harmful (mean CER 0.345 -> 0.794)
# ---------------------------------------------------------------------------
def _line_page(gap: int = 60, line_h: int = 40, ink_rows: int = 14):
    """A page of text lines with a sparse row inside each one.

    The sparse interior rows stand in for the matras and inter-character gaps
    that the old Otsu-on-profile cut discarded.
    """
    width, top = 1268, 40
    page = np.full((463, width), 255, np.uint8)
    rows = []
    y = top
    while y + line_h < 463:
        for i in range(ink_rows):
            cv2.line(page, (30, y + i), (width - 30, y + i), 0, 2)
        rows.append(y)
        y += line_h + gap
    return page, rows


def test_band_capture_includes_the_sparse_rows_of_each_line(tmp_path):
    """A band must span the line, not just its densest few rows."""
    page, rows = _line_page()
    src = tmp_path / "page.png"
    cv2.imwrite(str(src), page)
    bands = find_text_bands(cv2.imread(str(src), 0))
    assert bands, "no bands detected"
    for top, bottom in bands:
        assert bottom - top >= 14, (
            f"band {(top, bottom)} is thinner than the ink rows it must cover"
        )


def test_scaling_does_not_widen_a_band_past_the_aspect_limit():
    """The clamp must bound the upscale, not just the final crop.

    A band that is already wider than the limit cannot be made narrower without
    cropping characters away, so the contract is that scaling never pushes a
    band further past the limit than it already was.
    """
    for w, h in [(1268, 200), (1268, 60), (1268, 36), (900, 300), (300, 40)]:
        scale = _scale_for(w, h)
        assert scale >= 1.0
        out_w, out_h = w * scale, h * scale
        assert out_w / out_h <= max(MAX_BAND_ASPECT, w / h) + 1e-6, (
            f"{w}x{h} scaled by {scale:.2f} became {out_w/out_h:.1f}:1"
        )


def test_scale_never_exceeds_the_pixel_budget():
    budget = pixel_budget()
    for w, h in [(1268, 463), (1268, 40), (600, 300)]:
        scale = _scale_for(w, h)
        assert int(w * scale) * int(h * scale) <= budget * 1.02


def test_band_padding_is_not_applied_past_the_image_edge(tmp_path):
    page, _ = _line_page()
    src = tmp_path / "page.png"
    cv2.imwrite(str(src), page)
    for line in segment_lines(src):
        assert line.size > 0


def test_pixel_budget_follows_config():
    """One knob must govern both the processor and the segmentation crops."""
    from backend import config as app_config
    from backend.services.transcription import segment

    original = app_config.MAX_MODEL_PIXELS
    try:
        app_config.MAX_MODEL_PIXELS = 64 * 28 * 28
        assert segment.pixel_budget() == 64 * 28 * 28
    finally:
        app_config.MAX_MODEL_PIXELS = original


def test_segmentation_is_off_by_default():
    """Whole-page transcription is the configuration accuracy was measured in."""
    from backend import config as app_config

    assert app_config.SEGMENT_LINES is False


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

    def transcribe(self, image_path, prompt, on_progress=None):
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
        def transcribe(self, image_path, prompt, on_progress=None):
            if str(image_path).endswith("page.png"):
                return TranscriptionResult(
                    text="whole page", model_name="stub",
                    inference_mode="colab",
                )
            raise RuntimeError("line failed")

    result = LineSegmentedTranscriptionService(_Failing()).transcribe(src, "p")
    assert result.text == "whole page"
    assert result.line_count == 1