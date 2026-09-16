"""
Ordered restoration pipeline runner.

Drives a configurable sequence of restoration stages (defined in stages.py)
based on a PreprocessingConfig.  No FastAPI, database, or model dependencies.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from backend.services.restoration.stages import (
    StageResult,
    validate_image,
    convert_grayscale,
    denoise,
    enhance_contrast,
    adaptive_threshold,
    otsu_threshold,
    cleanup_borders,
    deskew,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Preprocessing configuration
# ---------------------------------------------------------------------------
@dataclass
class PreprocessingConfig:
    """Controls which restoration stages run and with what parameters."""

    name: str

    # Stage flags
    grayscale: bool = False
    denoise: bool = False
    enhance_contrast: bool = False
    binarize: bool = False
    binarize_method: str = "otsu"          # "otsu" | "adaptive"
    cleanup_borders: bool = False
    deskew: bool = False

    # Stage parameters (use defaults from stages.py when None)
    denoise_h: int = 10
    clahe_clip_limit: float = 2.0
    clahe_tile_grid: tuple[int, int] = (8, 8)
    adaptive_block_size: int = 31
    adaptive_c: int = 10
    border_pct: float = 0.02

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to JSON-safe dict for DB storage."""
        return {
            "name": self.name,
            "grayscale": self.grayscale,
            "denoise": self.denoise,
            "enhance_contrast": self.enhance_contrast,
            "binarize": self.binarize,
            "binarize_method": self.binarize_method,
            "cleanup_borders": self.cleanup_borders,
            "deskew": self.deskew,
            "denoise_h": self.denoise_h,
            "clahe_clip_limit": self.clahe_clip_limit,
            "clahe_tile_grid": list(self.clahe_tile_grid),
            "adaptive_block_size": self.adaptive_block_size,
            "adaptive_c": self.adaptive_c,
            "border_pct": self.border_pct,
        }


# ---------------------------------------------------------------------------
# Predefined experiment configs (Section 12 of PROJECT_GUIDE.md)
# ---------------------------------------------------------------------------
PRESET_CONFIGS: dict[str, PreprocessingConfig] = {
    "original": PreprocessingConfig(
        name="original",
    ),
    "grayscale": PreprocessingConfig(
        name="grayscale",
        grayscale=True,
    ),
    "denoised": PreprocessingConfig(
        name="denoised",
        grayscale=True,
        denoise=True,
    ),
    "enhanced": PreprocessingConfig(
        name="enhanced",
        grayscale=True,
        denoise=True,
        enhance_contrast=True,
    ),
    "binarized": PreprocessingConfig(
        name="binarized",
        grayscale=True,
        denoise=True,
        enhance_contrast=True,
        binarize=True,
        binarize_method="otsu",
    ),
    "deskewed": PreprocessingConfig(
        name="deskewed",
        grayscale=True,
        deskew=True,
    ),
    "full_restoration": PreprocessingConfig(
        name="full_restoration",
        grayscale=True,
        denoise=True,
        enhance_contrast=True,
        binarize=True,
        binarize_method="otsu",
        cleanup_borders=True,
        deskew=True,
    ),
}


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------
@dataclass
class PipelineResult:
    """Result from a full pipeline run."""
    config: PreprocessingConfig
    final_image: np.ndarray
    intermediates: list[StageResult] = field(default_factory=list)

    @property
    def stage_names(self) -> list[str]:
        return [s.name for s in self.intermediates]


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------
def run_pipeline(
    image: np.ndarray,
    config: PreprocessingConfig,
    save_intermediates: bool = True,
) -> PipelineResult:
    """Run the restoration pipeline on an image according to a config.

    Parameters
    ----------
    image : input image (BGR, as read by cv2.imread).
    config : which stages to run and with what parameters.
    save_intermediates : if True, every stage's output is kept in the result.

    Returns
    -------
    PipelineResult with final image and optionally all intermediate outputs.
    """
    intermediates: list[StageResult] = []
    current = image

    def _record(result: StageResult) -> np.ndarray:
        if save_intermediates:
            intermediates.append(result)
        return result.image

    # Stage 1 — always validate
    result = validate_image(current)
    current = _record(result)

    # "original" config: no processing at all
    if config.name == "original" and not any([
        config.grayscale, config.denoise, config.enhance_contrast,
        config.binarize, config.cleanup_borders, config.deskew,
    ]):
        logger.info("Pipeline '%s': no-op (original), returning as-is", config.name)
        return PipelineResult(config=config, final_image=current,
                              intermediates=intermediates)

    # Stage 2 — grayscale (mandatory if any restoration stage is enabled)
    if config.grayscale:
        result = convert_grayscale(current)
        current = _record(result)

    # Stage 3 — denoising
    if config.denoise:
        result = denoise(current, h=config.denoise_h)
        current = _record(result)

    # Stage 4 — contrast enhancement / CLAHE
    if config.enhance_contrast:
        result = enhance_contrast(
            current,
            clip_limit=config.clahe_clip_limit,
            tile_grid_size=config.clahe_tile_grid,
        )
        current = _record(result)

    # Stage 5/6 — binarization (pick one method per config)
    if config.binarize:
        if config.binarize_method == "adaptive":
            result = adaptive_threshold(
                current,
                block_size=config.adaptive_block_size,
                c=config.adaptive_c,
            )
        else:
            result = otsu_threshold(current)
        current = _record(result)

    # Stage 9 — border/background cleanup
    if config.cleanup_borders:
        result = cleanup_borders(current, border_pct=config.border_pct)
        current = _record(result)

    # Stage 10 — deskewing
    if config.deskew:
        result = deskew(current)
        current = _record(result)

    logger.info("Pipeline '%s' complete: %d stages run → %s",
                config.name, len(intermediates), [s.name for s in intermediates])

    return PipelineResult(
        config=config,
        final_image=current,
        intermediates=intermediates,
    )


# ---------------------------------------------------------------------------
# File-based convenience functions
# ---------------------------------------------------------------------------
def run_pipeline_on_file(
    input_path: str | Path,
    config: PreprocessingConfig,
    output_path: str | Path | None = None,
    save_intermediates: bool = True,
) -> PipelineResult:
    """Load an image from disk, run the pipeline, optionally save the result.

    Parameters
    ----------
    input_path : path to the input image file.
    config : pipeline configuration.
    output_path : if provided, the final image is written here.
    save_intermediates : keep intermediate stage images in the result.

    Returns
    -------
    PipelineResult
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cv2.imread failed to read: {input_path}")

    result = run_pipeline(image, config, save_intermediates=save_intermediates)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), result.final_image)
        logger.info("Saved restored image to %s", output_path)

    return result


def save_intermediates(
    result: PipelineResult,
    output_dir: str | Path,
    prefix: str = "",
) -> list[Path]:
    """Save all intermediate stage images to a directory.

    Returns list of file paths written.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    for i, stage in enumerate(result.intermediates):
        fname = f"{prefix}{i:02d}_{stage.name}.png"
        fpath = output_dir / fname
        cv2.imwrite(str(fpath), stage.image)
        paths.append(fpath)

    logger.info("Saved %d intermediate images to %s", len(paths), output_dir)
    return paths
