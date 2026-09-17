"""Unit tests for the OpenCV restoration pipeline (Phase 2).

Run with:  pytest tests/test_restoration.py -v
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.restoration import stages
from backend.services.restoration.pipeline import (
    PRESET_CONFIGS,
    PreprocessingConfig,
    run_pipeline,
)

SAMPLE_IMAGE = PROJECT_ROOT / "data" / "raw" / "sample_modi_page.png"


@pytest.fixture(scope="module")
def sample_bgr() -> np.ndarray:
    assert SAMPLE_IMAGE.exists(), f"Sample image missing: {SAMPLE_IMAGE}"
    img = cv2.imread(str(SAMPLE_IMAGE), cv2.IMREAD_COLOR)
    assert img is not None
    return img


@pytest.fixture(scope="module")
def sample_gray(sample_bgr) -> np.ndarray:
    return stages.convert_grayscale(sample_bgr).image


# --- Stage 1: validation ----------------------------------------------------
def test_validate_image_reports_stats(sample_bgr):
    result = stages.validate_image(sample_bgr)
    assert result.image.shape == sample_bgr.shape
    assert result.metadata["height"] > 0
    assert result.metadata["width"] > 0
    assert result.metadata["channels"] == 3


def test_validate_image_rejects_empty():
    with pytest.raises(ValueError):
        stages.validate_image(np.array([], dtype=np.uint8))


# --- Stage 2: grayscale ------------------------------------------------------
def test_grayscale_output_is_single_channel(sample_bgr):
    result = stages.convert_grayscale(sample_bgr)
    assert result.image.ndim == 2
    assert result.image.dtype == np.uint8


def test_grayscale_idempotent_on_gray(sample_gray):
    result = stages.convert_grayscale(sample_gray)
    assert result.image.ndim == 2
    np.testing.assert_array_equal(result.image, sample_gray)


# --- Stage 3: denoise ---------------------------------------------------------
def test_denoise_preserves_shape_and_dtype(sample_gray):
    result = stages.denoise(sample_gray)
    assert result.image.shape == sample_gray.shape
    assert result.image.dtype == np.uint8


def test_denoise_rejects_color(sample_bgr):
    with pytest.raises(ValueError):
        stages.denoise(sample_bgr)


# --- Stage 4: CLAHE ------------------------------------------------------------
def test_enhance_contrast_preserves_shape(sample_gray):
    result = stages.enhance_contrast(sample_gray)
    assert result.image.shape == sample_gray.shape
    assert result.image.dtype == np.uint8


def test_enhance_contrast_rejects_color(sample_bgr):
    with pytest.raises(ValueError):
        stages.enhance_contrast(sample_bgr)


# --- Stages 5/6: binarization --------------------------------------------------
def test_otsu_output_is_truly_binary(sample_gray):
    result = stages.otsu_threshold(sample_gray)
    unique = np.unique(result.image)
    assert set(unique.tolist()).issubset({0, 255}), f"Non-binary values: {unique[:10]}"
    assert "otsu_threshold" in result.metadata


def test_adaptive_output_is_truly_binary(sample_gray):
    result = stages.adaptive_threshold(sample_gray)
    unique = np.unique(result.image)
    assert set(unique.tolist()).issubset({0, 255})


# --- Stage 9: border cleanup ----------------------------------------------------
def test_cleanup_borders_paints_edges_white(sample_gray):
    result = stages.cleanup_borders(sample_gray, border_pct=0.02)
    h, w = sample_gray.shape
    bh = max(1, int(h * 0.02))
    assert np.all(result.image[:bh, :] == 255)
    assert np.all(result.image[-bh:, :] == 255)


# --- Stage 10: deskew ------------------------------------------------------------
def test_deskew_preserves_shape(sample_gray):
    result = stages.deskew(sample_gray)
    assert result.image.shape == sample_gray.shape
    assert "skew_angle" in result.metadata
    assert abs(result.metadata["skew_angle"]) <= 15.0


# --- Pipeline -------------------------------------------------------------------
EXPECTED_STAGES = {
    "original": ["validated"],
    "grayscale": ["validated", "grayscale"],
    "denoised": ["validated", "grayscale", "denoised"],
    "enhanced": ["validated", "grayscale", "denoised", "enhanced"],
    "binarized": ["validated", "grayscale", "denoised", "enhanced", "otsu_binarized"],
    "deskewed": ["validated", "grayscale", "deskewed"],
    "full_restoration": [
        "validated", "grayscale", "denoised", "enhanced",
        "deskewed", "otsu_binarized", "borders_cleaned",
    ],
}


def test_all_preset_configs_run(sample_bgr):
    for name, config in PRESET_CONFIGS.items():
        result = run_pipeline(sample_bgr, config)
        assert result.stage_names == EXPECTED_STAGES[name], f"config '{name}'"
        assert result.final_image.size > 0


def test_original_config_returns_equivalent_image(sample_bgr):
    result = run_pipeline(sample_bgr, PRESET_CONFIGS["original"])
    np.testing.assert_array_equal(result.final_image, sample_bgr)


def test_adaptive_binarize_path_runs(sample_bgr):
    config = PreprocessingConfig(
        name="adaptive_test", grayscale=True, binarize=True,
        binarize_method="adaptive",
    )
    result = run_pipeline(sample_bgr, config)
    assert result.stage_names[-1] == "adaptive_binarized"
    assert set(np.unique(result.final_image).tolist()).issubset({0, 255})


def test_config_serializes_to_json_safe_dict():
    for config in PRESET_CONFIGS.values():
        d = config.to_dict()
        import json

        json.dumps(d)  # must not raise


def test_config_round_trips_through_dict():
    from backend.services.restoration.pipeline import list_configs

    for name, config in PRESET_CONFIGS.items():
        restored = PreprocessingConfig.from_dict(config.to_dict())
        assert restored == config, f"config '{name}'"
    # Registry used by Phase 5/6: stable names, JSON-safe values.
    registry = list_configs()
    assert set(registry) == set(PRESET_CONFIGS)
    import json

    json.dumps(registry)  # must not raise


def test_full_restoration_output_is_binary(sample_bgr):
    # Deskew runs before binarization, so no resampling happens after
    # thresholding and the final image must be strictly binary.
    result = run_pipeline(sample_bgr, PRESET_CONFIGS["full_restoration"])
    assert result.stage_names.index("deskewed") < \
        result.stage_names.index("otsu_binarized")
    assert set(np.unique(result.final_image).tolist()).issubset({0, 255})
