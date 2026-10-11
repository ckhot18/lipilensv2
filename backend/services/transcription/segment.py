"""Text-line segmentation and upscaling for vision-language transcription.

Splitting a page into text lines was introduced to raise the visual-token
budget: a page spends its whole pixel allowance on hundreds of characters, so
one line gets many more tokens per character. Measured against expert
references it made accuracy *worse* (mean CER 0.345 -> 0.794 on
single-column MoDeTrans pages), for two reasons this module now guards against:

1. Thresholding the ink profile with Otsu keeps only the densest core of each
   line. Modi matras, ascenders and the anusvāra live above and below that
   core, so they were cropped away — and the adapter's dominant error is
   already deletions (46%). Bands are now padded to recover the full extent.
2. Upscaling a thin band to a target height produced 23:1-40:1 slivers at the
   pixel budget, far outside anything Qwen2.5-VL saw in training. Upscaling is
   now bounded by the band aspect ratio as well as the budget.

Segmentation is therefore OFF by default (see backend/config.py); this module
is still used when SEGMENT_LINES=1.

Pure OpenCV/numpy: no GPU, no new dependency.
"""

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

MIN_BAND_PX = 10
BAND_GAP_MERGE_PX = 8
MIN_INK_COLUMNS = 12
MAX_LINES = 24
MAX_UPSCALE = 3.0
MIN_UPSCALE = 1.0
TARGET_BAND_HEIGHT = 220
PAD_X = 12
PAD_Y = 10

# A row counts as "on the line" when it holds at least this fraction of the
# page's peak ink. Low enough to keep matras and ascenders, high enough to stay
# clear of the inter-line gutter.
LINE_INK_RATIO = 0.18
# Vertical padding around a detected band, as a fraction of the band's own
# height, to put back the ascenders/matras the profile threshold discards.
BAND_HEIGHT_PAD_RATIO = 0.35
# A text line is naturally wide (a MoDeTrans line is ~20:1). Beyond this the
# crop is mostly whitespace or a fragment, and upscaling it produces a sliver
# the vision encoder cannot use.
MAX_BAND_ASPECT = 32.0


def pixel_budget() -> int:
    """Pixel budget from config, so one knob controls model and segmentation."""
    try:
        from backend import config as app_config

        return int(app_config.MAX_MODEL_PIXELS)
    except Exception:  # noqa: BLE001 - standalone use must still work
        return 1280 * 28 * 28


def _ink_mask(gray: np.ndarray) -> np.ndarray:
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return bw


def find_text_bands(gray: np.ndarray) -> list[tuple[int, int]]:
    """Return (top, bottom) row ranges of each horizontal run of text.

    A row joins a line when its ink count reaches LINE_INK_RATIO of the page
    peak. Otsu on the profile (the previous rule) puts the cut so high that
    only the dense core of each line survives and the matras above and below it
    are cut away.
    """
    bw = _ink_mask(gray)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((1, 9), np.uint8))
    profile = (bw > 0).sum(axis=1).astype(np.uint8)

    peak = int(profile.max())
    if peak == 0:
        return []
    cut = max(1, int(peak * LINE_INK_RATIO))
    # Bridge the sparse rows *within* a line (between characters and matras)
    # without bridging the clear gutter between two lines.
    active = (profile >= cut).astype(np.uint8)
    bridge = max(3, int(peak * 0.02))
    active = cv2.morphologyEx(
        active.reshape(-1, 1), cv2.MORPH_CLOSE, np.ones((bridge, 1), np.uint8)
    ).ravel()
    active = active > 0

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
            merged.append((band[0], band[1]))
    return merged


def _scale_for(band_w: int, band_h: int) -> float:
    """Upscale factor for a band, bounded by budget, height and aspect ratio."""
    px = band_w * band_h
    by_budget = (pixel_budget() / px) ** 0.5 if px else 1.0
    by_height = TARGET_BAND_HEIGHT / band_h if band_h else 1.0
    # Upscaling cannot fix a band that is already too wide and flat: it would
    # only stretch it further into a sliver.
    by_aspect = MAX_BAND_ASPECT * band_h / band_w if band_w else 1.0
    scale = min(by_budget, by_height, by_aspect)
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
        band_h = bottom - top
        # Recover the ink the profile threshold dropped above and below the
        # core: matras, ascenders and the anusvara.
        pad = max(PAD_Y, int(round(band_h * BAND_HEIGHT_PAD_RATIO)))
        top_p = max(0, top - pad)
        bottom_p = min(height, bottom + pad)
        cols = np.where((gray[top_p:bottom_p] < 200).any(axis=0))[0]
        if len(cols) < MIN_INK_COLUMNS:
            continue
        left = max(0, int(cols.min()) - PAD_X)
        right = min(width, int(cols.max()) + PAD_X)
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