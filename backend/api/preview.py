"""Restoration preview route: CPU-only, no model, no database row.

Lets the UI show the effect of each pipeline on a freshly uploaded scan in
well under a second, so restoration never blocks on the GPU. Only the
transcription act needs the model.
"""

import hashlib
import logging
import time
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Form, HTTPException, UploadFile

from backend import config as app_config
from backend.schemas.manuscript import RestorationPreview
from backend.services.restoration.pipeline import PRESET_CONFIGS, run_pipeline
from backend.utils.image_io import save_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manuscripts", tags=["Restoration"])

MAX_PREVIEW_BYTES = 20 * 1024 * 1024
PREVIEW_DIR = app_config.PROCESSED_DATA_DIR / "_preview"


def _preview_dir() -> Path:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    return PREVIEW_DIR


@router.post("/preview", response_model=RestorationPreview)
def preview_restoration(
    file: UploadFile,
    config_name: str = Form(default="original"),
):
    if config_name not in PRESET_CONFIGS:
        raise HTTPException(400, f"Unknown config '{config_name}'. "
                                 f"Available: {list(PRESET_CONFIGS)}")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(400, "Uploaded file is not an image")

    raw = file.file.read()
    if len(raw) > MAX_PREVIEW_BYTES:
        raise HTTPException(400, "File exceeds "
                                 f"{MAX_PREVIEW_BYTES} bytes")

    sha = hashlib.sha256(raw + config_name.encode()).hexdigest()[:24]
    out_dir = _preview_dir()
    original_path = out_dir / f"{sha}_original.png"
    restored_path = out_dir / f"{sha}_restored.png"

    started = time.perf_counter()
    cached = restored_path.exists()
    stages: list[str] = []

    if not cached:
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(400, "File is not a readable image")
        save_image(img, original_path)
        result = run_pipeline(img, PRESET_CONFIGS[config_name],
                              save_intermediates=True)
        save_image(result.final_image, restored_path)
        stages = result.stage_names
        logger.info("Preview %s config=%s %d stages in %.0f ms",
                    sha[:8], config_name, len(stages),
                    (time.perf_counter() - started) * 1000)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return RestorationPreview(
        config_name=config_name,
        original_url=_url(original_path),
        restored_url=_url(restored_path),
        elapsed_ms=elapsed_ms,
        cached=cached,
        stages=stages,
    )


def _url(path: Path) -> str | None:
    try:
        rel = path.relative_to(app_config.DATA_DIR)
    except ValueError:
        return None
    return "/files/" + rel.as_posix()
