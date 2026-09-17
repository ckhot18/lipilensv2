"""Image I/O helpers for LipiLens.

Thin wrappers around cv2.imread / cv2.imwrite with consistent error
handling, so routes and scripts share the same behaviour.
"""

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def load_image(path: str | Path) -> np.ndarray:
    """Load an image from disk as BGR (OpenCV default).

    Raises FileNotFoundError if the path does not exist,
    ValueError if the file is not a readable image.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"File is not a readable image: {path}")
    return image


def save_image(image: np.ndarray, path: str | Path) -> Path:
    """Save an image to disk, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(path), image)
    if not ok:
        raise IOError(f"cv2.imwrite failed for: {path}")
    logger.info("Saved image to %s", path)
    return path
