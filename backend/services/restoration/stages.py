"""
Individual OpenCV restoration stages.

Each stage is a pure function: takes a numpy image array (and optional params),
returns a numpy image array. No FastAPI, database, or model dependencies.

Colour convention: images flow through the pipeline as BGR (OpenCV default)
until grayscale conversion, after which they are single-channel uint8.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage result wrapper
# ---------------------------------------------------------------------------
@dataclass
class StageResult:
    """Result from a single restoration stage."""
    name: str
    image: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Stage 1 — Image validation / inspection
# ---------------------------------------------------------------------------
def validate_image(image: np.ndarray) -> StageResult:
    """Confirm the image is readable and report basic stats."""
    if image is None or image.size == 0:
        raise ValueError("Image is empty or could not be read.")

    h, w = image.shape[:2]
    channels = image.shape[2] if image.ndim == 3 else 1
    dtype = str(image.dtype)

    meta = {
        "height": h,
        "width": w,
        "channels": channels,
        "dtype": dtype,
        "mean_intensity": float(np.mean(image)),
    }
    logger.info("validate_image: %dx%d, %d ch, dtype=%s, mean=%.1f",
                w, h, channels, dtype, meta["mean_intensity"])
    return StageResult(name="validated", image=image.copy(), metadata=meta)


# ---------------------------------------------------------------------------
# Stage 2 — Grayscale conversion
# ---------------------------------------------------------------------------
def convert_grayscale(image: np.ndarray) -> StageResult:
    """Convert BGR image to single-channel grayscale."""
    if image.ndim == 2:
        gray = image
    elif image.ndim == 3 and image.shape[2] == 1:
        gray = image[:, :, 0]
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    logger.info("convert_grayscale: output shape %s", gray.shape)
    return StageResult(name="grayscale", image=gray)


# ---------------------------------------------------------------------------
# Stage 3 — Denoising
# ---------------------------------------------------------------------------
def denoise(image: np.ndarray, h: int = 10,
            template_window: int = 7,
            search_window: int = 21) -> StageResult:
    """Reduce scan/camera noise using Non-Local Means Denoising.

    Parameters
    ----------
    h : filter strength — higher removes more noise but may blur detail.
    template_window : size of template patch (must be odd).
    search_window : size of search area (must be odd).
    """
    if image.ndim != 2:
        raise ValueError("denoise expects a single-channel (grayscale) image.")

    denoised = cv2.fastNlMeansDenoising(
        image, None, h=h,
        templateWindowSize=template_window,
        searchWindowSize=search_window,
    )
    logger.info("denoise: h=%d, templateWindow=%d, searchWindow=%d",
                h, template_window, search_window)
    return StageResult(
        name="denoised", image=denoised,
        metadata={"h": h, "template_window": template_window,
                  "search_window": search_window},
    )


# ---------------------------------------------------------------------------
# Stage 4 — Contrast enhancement / CLAHE
# ---------------------------------------------------------------------------
def enhance_contrast(image: np.ndarray, clip_limit: float = 2.0,
                     tile_grid_size: tuple[int, int] = (8, 8)) -> StageResult:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).

    Improves legibility of faded ink while avoiding over-amplification
    of noise in uniform background areas.
    """
    if image.ndim != 2:
        raise ValueError("enhance_contrast expects a single-channel image.")

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    enhanced = clahe.apply(image)
    logger.info("enhance_contrast: clipLimit=%.1f, tileGrid=%s",
                clip_limit, tile_grid_size)
    return StageResult(
        name="enhanced", image=enhanced,
        metadata={"clip_limit": clip_limit,
                  "tile_grid_size": list(tile_grid_size)},
    )


# ---------------------------------------------------------------------------
# Stage 5 — Adaptive thresholding (local binarization)
# ---------------------------------------------------------------------------
def adaptive_threshold(image: np.ndarray, block_size: int = 31,
                       c: int = 10) -> StageResult:
    """Local binarization for uneven lighting conditions.

    Parameters
    ----------
    block_size : neighbourhood size for threshold calculation (must be odd).
    c : constant subtracted from the mean (controls ink vs background boundary).
    """
    if image.ndim != 2:
        raise ValueError("adaptive_threshold expects a single-channel image.")

    binary = cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, block_size, c,
    )
    logger.info("adaptive_threshold: blockSize=%d, C=%d", block_size, c)
    return StageResult(
        name="adaptive_binarized", image=binary,
        metadata={"block_size": block_size, "c": c},
    )


# ---------------------------------------------------------------------------
# Stage 6 — Otsu thresholding (global binarization)
# ---------------------------------------------------------------------------
def otsu_threshold(image: np.ndarray) -> StageResult:
    """Global binarization using Otsu's method.

    Best suited for images with relatively even lighting and a clear
    bimodal histogram (ink vs background).
    """
    if image.ndim != 2:
        raise ValueError("otsu_threshold expects a single-channel image.")

    thresh_val, binary = cv2.threshold(
        image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    logger.info("otsu_threshold: computed threshold=%d", int(thresh_val))
    return StageResult(
        name="otsu_binarized", image=binary,
        metadata={"otsu_threshold": int(thresh_val)},
    )


# ---------------------------------------------------------------------------
# Stage 9 — Border / background cleanup
# ---------------------------------------------------------------------------
def cleanup_borders(image: np.ndarray, border_pct: float = 0.02) -> StageResult:
    """Remove dark scanner borders/margins by painting edges white.

    Parameters
    ----------
    border_pct : fraction of image dimension to treat as border (0.0–0.1).
    """
    if image.ndim != 2:
        raise ValueError("cleanup_borders expects a single-channel image.")

    h, w = image.shape
    bh = max(1, int(h * border_pct))
    bw = max(1, int(w * border_pct))

    cleaned = image.copy()
    cleaned[:bh, :] = 255    # top
    cleaned[-bh:, :] = 255   # bottom
    cleaned[:, :bw] = 255    # left
    cleaned[:, -bw:] = 255   # right

    logger.info("cleanup_borders: border_pct=%.3f (h=%d, w=%d px)",
                border_pct, bh, bw)
    return StageResult(
        name="borders_cleaned", image=cleaned,
        metadata={"border_pct": border_pct, "border_h_px": bh, "border_w_px": bw},
    )


# ---------------------------------------------------------------------------
# Stage 10 — Deskewing
# ---------------------------------------------------------------------------
def deskew(image: np.ndarray, max_angle: float = 15.0) -> StageResult:
    """Correct rotation from imperfect photography/scanning.

    Uses Hough line detection to estimate the dominant skew angle,
    then rotates the image to correct it. Limits correction to
    ±max_angle degrees to avoid wild rotations on noisy images.
    """
    if image.ndim != 2:
        raise ValueError("deskew expects a single-channel image.")

    # Work on a binarized copy for line detection
    _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Detect lines via Hough transform
    lines = cv2.HoughLinesP(
        thresh, 1, np.pi / 180,
        threshold=100, minLineLength=image.shape[1] // 4, maxLineGap=10,
    )

    if lines is None or len(lines) == 0:
        logger.info("deskew: no lines detected, skipping rotation")
        return StageResult(
            name="deskewed", image=image.copy(),
            metadata={"skew_angle": 0.0, "lines_detected": 0},
        )

    # Compute angles of detected lines
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line.flatten()[:4]
        dx = x2 - x1
        dy = y2 - y1
        if abs(dx) > 0:
            angle = np.degrees(np.arctan2(dy, dx))
            # Only consider near-horizontal lines (within ±max_angle of 0°)
            if abs(angle) <= max_angle:
                angles.append(angle)

    if not angles:
        logger.info("deskew: no near-horizontal lines found, skipping rotation")
        return StageResult(
            name="deskewed", image=image.copy(),
            metadata={"skew_angle": 0.0, "lines_detected": len(lines)},
        )

    # Median angle is more robust to outliers than mean
    skew_angle = float(np.median(angles))

    # Rotate the image to correct the skew
    h, w = image.shape
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
    deskewed = cv2.warpAffine(
        image, rotation_matrix, (w, h),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE,
    )

    logger.info("deskew: corrected %.2f° (from %d lines, %d near-horizontal)",
                skew_angle, len(lines), len(angles))
    return StageResult(
        name="deskewed", image=deskewed,
        metadata={"skew_angle": skew_angle, "lines_detected": len(lines),
                  "near_horizontal_lines": len(angles)},
    )
