"""Manuscript routes: upload -> restore -> transcribe -> retrieve -> search."""

import logging
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend import config as app_config
from backend.database.session import get_db
from backend.schemas.manuscript import (
    ManuscriptDetail,
    ManuscriptSummary,
    TranscriptionResponse,
)
from backend.services import pipeline as pipeline_mod
from backend.services.archive import repository as repo
from backend.services.restoration.pipeline import PRESET_CONFIGS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manuscripts", tags=["Manuscripts"])

SAFE_EXTS = {".png": ".png", ".jpg": ".jpg", ".jpeg": ".jpg",
             ".webp": ".webp", ".bmp": ".bmp", ".tif": ".png",
             ".tiff": ".png"}


def _image_url(disk_path: str | None) -> str | None:
    """Map a data/ disk path to its /files URL (None stays None)."""
    if not disk_path:
        return None
    rel = Path(disk_path)
    try:
        rel = rel.relative_to(app_config.DATA_DIR)
    except ValueError:
        return None
    return "/files/" + rel.as_posix()


def _to_detail(row) -> ManuscriptDetail:
    tr = row.transcriptions[-1] if row.transcriptions else None
    return ManuscriptDetail(
        id=row.id, title=row.title, identifier=row.identifier,
        author=row.author, date=row.date, source=row.source,
        collection=row.collection, location=row.location, notes=row.notes,
        status=row.status,
        original_image_url=_image_url(row.original_image_path),
        restored_image_url=_image_url(row.restored_image_path),
        created_at=row.created_at,
        transcription=TranscriptionResponse.model_validate(tr) if tr else None,
    )


@router.post("", response_model=ManuscriptDetail)
def upload_manuscript(
    file: UploadFile,
    title: str | None = Form(default=None),
    identifier: str | None = Form(default=None),
    config_name: str = Form(default="full_restoration"),
    session: Session = Depends(get_db),
):
    # NOTE: sync def (not async) — FastAPI runs this in a threadpool, so the
    # blocking ~20-70 s pipeline call doesn't stall the event loop.
    # --- validation (API is the source of truth) -------------------------
    if config_name not in PRESET_CONFIGS:
        raise HTTPException(400, f"Unknown config '{config_name}'. "
                                 f"Available: {list(PRESET_CONFIGS)}")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(400, "Uploaded file is not an image")
    raw = file.file.read()
    if len(raw) > app_config.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(400, f"File exceeds "
                                 f"{app_config.MAX_UPLOAD_SIZE_BYTES} bytes")
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "File is not a readable image")
    ext = SAFE_EXTS.get(Path(file.filename or "").suffix.lower(), ".png")

    # --- idempotent re-upload: same bytes + same config -> existing row ----
    import hashlib
    sha = hashlib.sha256(raw).hexdigest()
    existing = repo.find_by_sha_and_config(session, sha, config_name)
    if existing is not None:
        detail = _to_detail(repo.get_manuscript(session, existing.id))
        detail.duplicate = True
        return detail

    # --- persist original (never overwritten) ------------------------------
    ms = repo.create_manuscript(
        session,
        title=title or Path(file.filename or "upload").stem,
        original_image_path="pending",
        image_sha256=sha,
        identifier=identifier,
    )
    session.flush()  # assign id before writing files
    raw_dir = app_config.RAW_DATA_DIR / str(ms.id)
    raw_dir.mkdir(parents=True, exist_ok=True)
    original_path = raw_dir / f"original{ext}"
    original_path.write_bytes(raw)
    ms.original_image_path = str(original_path)
    session.flush()

    # --- restoration config row (reproducibility) ---------------------------
    cfg_row = repo.get_or_create_config(
        session, config_name, PRESET_CONFIGS[config_name].to_dict())

    # --- restore + transcribe (model errors -> 503, work preserved) ---------
    try:
        out = pipeline_mod.run_full_pipeline(
            original_path, config_name,
            output_dir=app_config.PROCESSED_DATA_DIR / str(ms.id))
    except Exception as exc:  # noqa: BLE001
        session.commit()  # keep manuscript + original through restoration
        logger.exception("Transcription failed for manuscript %s", ms.id)
        raise HTTPException(
            503, f"Transcription failed ({type(exc).__name__}); manuscript "
                 f"{ms.id} and its images are preserved") from exc

    repo.mark_restored(session, ms.id, out.restored_image_path, cfg_row.id)
    if out.restoration_warning:
        logger.warning("Manuscript %s: %s", ms.id, out.restoration_warning)
    repo.create_transcription(
        session, ms.id, ai_text=out.transcription,
        model_name=out.model_name, inference_mode=out.inference_mode,
        config_id=cfg_row.id)
    session.commit()
    logger.info("Manuscript %s done via %s (%s)", ms.id, out.inference_mode,
                config_name)
    return _to_detail(repo.get_manuscript(session, ms.id))


@router.get("", response_model=list[ManuscriptSummary])
def list_manuscripts(search: str | None = None,
                     verified: bool | None = None,
                     limit: int = 50, offset: int = 0,
                     session: Session = Depends(get_db)):
    if limit < 1 or limit > 200 or offset < 0:
        raise HTTPException(400, "limit must be 1..200, offset >= 0")
    rows = (repo.search_manuscripts(session, search) if search
            else repo.list_manuscripts(session))
    if verified is True:
        rows = [r for r in rows if r.status == "verified"]
    rows = rows[offset:offset + limit]
    return [ManuscriptSummary(id=r.id, title=r.title,
                              identifier=r.identifier, status=r.status,
                              verified=(r.status == "verified")) for r in rows]


@router.get("/{manuscript_id}", response_model=ManuscriptDetail)
def get_manuscript(manuscript_id: int, session: Session = Depends(get_db)):
    row = repo.get_manuscript(session, manuscript_id)
    if row is None:
        raise HTTPException(404, "Manuscript not found")
    return _to_detail(row)
