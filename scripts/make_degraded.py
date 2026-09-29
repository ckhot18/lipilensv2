#!/usr/bin/env python
"""Generate deterministic synthetic degradations for the H2 robustness test.

Degradations (documented parameters, seeded RNG):
  blur  — GaussianBlur 5x5 (defocus simulation)
  noise — additive Gaussian sigma=12, seed 42 (sensor/scan noise)
  fade  — img*0.55 + 45 (faded ink / washed-out photo)

Usage: python scripts/make_degraded.py
Output: data/raw/degraded/{MID}_{degr}.png  (gitignored scratch)
"""

import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SAMPLES = ["MT-048", "MT-002", "MT-014", "MT-020", "MT-011", "MT-003"]
OUT_DIR = PROJECT_ROOT / "data" / "raw" / "degraded"


def degrade_blur(img: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(img, (5, 5), 0)


def degrade_noise(img: np.ndarray) -> np.ndarray:
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 12, img.shape)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def degrade_fade(img: np.ndarray) -> np.ndarray:
    return np.clip(img.astype(np.float32) * 0.55 + 45, 0, 255).astype(np.uint8)


DEGRADATIONS = {"blur": degrade_blur, "noise": degrade_noise,
                "fade": degrade_fade}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for mid in SAMPLES:
        src = PROJECT_ROOT / "data" / "raw" / "mode_trans" / f"{mid}.png"
        img = cv2.imread(str(src), cv2.IMREAD_COLOR)
        assert img is not None, f"missing {src}"
        for name, fn in DEGRADATIONS.items():
            out = OUT_DIR / f"{mid}_{name}.png"
            cv2.imwrite(str(out), fn(img))
            print(f"{mid}_{name} saved")


if __name__ == "__main__":
    main()
