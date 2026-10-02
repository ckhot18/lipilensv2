"""Text-line segmentation and upscaling for vision-language transcription.

A manuscript page holds hundreds of characters but only ~128 merged visual
tokens after Qwen's ``max_pixels`` downscale — under one token per character,
which is why whole-page transcription collapses. Splitting the page into text
lines and upscaling each one spends the same pixel budget on far fewer
characters, multiplying the tokens available per character.

Pure OpenCV/numpy: no GPU, no new dependency.
"""

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Matches the processor budget in local_qwen.py / the Colab server. Raising it
# is half the win; line splitting is the other half.
MAX_MODEL_PIXELS = 1280 * 28 * 28

MIN_BAND_PX = 10
BAND_GAP_MERGE_PX = 8
MIN_INK_COLUMNS = 12
MAX_LINES = 24
MAX_UPSCALE = 6.0
MIN_UPSCALE = 1.0
TARGET_BAND_HEIGHT = 220
PAD_X = 12
PAD_Y = 10


def _ink_mask(gray: np.ndarray) -> np.ndarray:
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return bw


def find_text_bands(gray: np.ndarray) -> list[tuple[int, int]]:
    """Return (top, bottom) row ranges of each horizontal run of text.

    The inter-line gaps are the valleys of the horizontal ink profile. A fixed
    fraction of the peak never separates them (a dense page peaks near 1.0 while
    its valleys sit at 0.1), so the cut is placed with Otsu on the profile.
    """
    bw = _ink_mask(gray)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((1, 9), np.uint8))
    profile = (bw > 0).sum(axis=1).astype(np.uint8)

    cut, _ = cv2.threshold(profile.reshape(-1, 1), 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cut = max(1, min(int(cut), max(1, int(profile.max()) - 1)))
    active = profile >= cut

    raw: list[tuple[int, int]] = []
    start = None
    for i, on in enumerate(active):
        if on and start is None:
            start = i
        elif not on and start is not None:
            if i - start >= MIN_BAND_PX:
                raw.append((start, i))
            start = None
    if start is not None and len(active) - start >= MIN_BAND_PX:
        raw.append((start, len(active)))

    merged: list[tuple[int, int]] = []
    for band in raw:
        if merged and band[0] - merged[-1][1] <= BAND_GAP_MERGE_PX:
            merged[-1] = (merged[-1][0], band[1])
        else:
            merged.append(list(band))  # type: ignore[arg-type]
    return [tuple(b) for b in merged]  # type: ignore[misc]


def _scale_for(band_w: int, band_h: int) -> float:
    px = band_w * band_h
    by_budget = (MAX_MODEL_PIXELS / px) ** 0.5 if px else 1.0
    by_height = TARGET_BAND_HEIGHT / band_h if band_h else 1.0
    scale = min(by_budget, by_height)
    return max(MIN_UPSCALE, min(MAX_UPSCALE, scale))


def segment_lines(image_path: str | Path) -> list[np.ndarray]:
    """Split a page into upscaled text-line images, ready for the model."""
    gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        logger.warning("segment_lines: unreadable image %s", image_path)
        return []

    bands = find_text_bands(gray)
    height, width = gray.shape
    if not bands or len(bands) > MAX_LINES:
        logger.info("segment_lines: %d bands (out of range) - using whole page",
                    len(bands))
        return [gray]

    lines: list[np.ndarray] = []
    for top, bottom in bands:
        cols = np.where((gray[top:bottom] < 200).any(axis=0))[0]
        if len(cols) < MIN_INK_COLUMNS:
            continue
        left = max(0, int(cols.min()) - PAD_X)
        right = min(width, int(cols.max()) + PAD_X)
        top_p = max(0, top - PAD_Y)
        bottom_p = min(height, bottom + PAD_Y)
        crop = gray[top_p:bottom_p, left:right]
        if crop.size == 0:
            continue
        scale = _scale_for(crop.shape[1], crop.shape[0])
        if scale > 1.01:
            crop = cv2.resize(
                crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
            )
        lines.append(crop)

    if not lines:
        return [gray]

    logger.info("segment_lines: %d bands -> %d lines (page %dx%d)",
                len(bands), len(lines), width, height)
    return lines


def write_lines(lines: list[np.ndarray], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, line in enumerate(lines):
        path = out_dir / f"line_{i:02d}.png"
        cv2.imwrite(str(path), line)
        paths.append(path)
    return paths