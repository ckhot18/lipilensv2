"""Archive repository — all SQL/ORM lives here (PROJECT_GUIDE.md Sec. 16).

Every function takes an injected sqlalchemy Session (testable with a temp
SQLite file; Phase 6 passes the request session via get_db).

Core invariants (enforced here, not in routes):
- ai_transcription is NEVER modified after creation.
- verified_transcription is set ONLY through verify_transcription().
- status transitions: uploaded -> restored -> transcribed -> verified.
"""

import json
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from backend.database.models import (
    Manuscript,
    PreprocessingConfigRow,
    Transcription,
)


# ---------------------------------------------------------------------------
# Preprocessing configs
# ---------------------------------------------------------------------------
def get_or_create_config(session: Session, name: str,
                         config_dict: dict[str, Any]) -> PreprocessingConfigRow:
    """Return the row for a named config, creating it on first use."""
    row = session.scalars(
        select(PreprocessingConfigRow).where(PreprocessingConfigRow.name == name)
    ).first()
    if row is None:
        row = PreprocessingConfigRow(
            name=name,
            config_json=json.dumps(config_dict, sort_keys=True),
        )
        session.add(row)
        session.flush()
    return row


# ---------------------------------------------------------------------------
# Manuscripts
# ---------------------------------------------------------------------------
def create_manuscript(
    session: Session,
    title: str,
    original_image_path: str,
    image_sha256: str | None = None,
    **meta: Any,
) -> Manuscript:
    """Create a manuscript row (status='uploaded'). No file I/O here."""
    allowed = {"identifier", "author", "date", "source", "collection",
               "location", "notes"}
    extra = {k: v for k, v in meta.items() if k in allowed}
    row = Manuscript(title=title, original_image_path=original_image_path,
                     image_sha256=image_sha256, status="uploaded", **extra)
    session.add(row)
    session.flush()
    return row


def get_manuscript(session: Session, manuscript_id: int) -> Manuscript | None:
    # refresh() (not just selectinload) so a Manuscript loaded earlier in the
    # same session never serves a stale transcription list — the upload route
    # (Phase 6) reads the manuscript right after creating its transcription.
    row = session.get(Manuscript, manuscript_id)
    if row is not None:
        session.refresh(row, attribute_names=["transcriptions"])
    return row


def find_by_sha_and_config(session: Session, image_sha256: str,
                           config_name: str) -> Manuscript | None:
    """Idempotency lookup: same image bytes + same config -> existing row."""
    return session.scalars(
        select(Manuscript)
        .join(PreprocessingConfigRow,
              Manuscript.preprocessing_config_id == PreprocessingConfigRow.id)
        .where(Manuscript.image_sha256 == image_sha256,
               PreprocessingConfigRow.name == config_name)
        .order_by(Manuscript.id.desc())
    ).first()


def mark_restored(session: Session, manuscript_id: int, restored_path: str,
                  config_id: int) -> Manuscript:
    row = get_manuscript(session, manuscript_id)
    if row is None:
        raise ValueError(f"Manuscript {manuscript_id} not found")
    row.restored_image_path = restored_path
    row.preprocessing_config_id = config_id
    row.status = "restored"
    session.flush()
    return row


def list_manuscripts(session: Session,
                     verified_only: bool = False) -> list[Manuscript]:
    stmt = (select(Manuscript)
            .options(selectinload(Manuscript.transcriptions))
            .order_by(Manuscript.id.desc()))
    if verified_only:
        stmt = stmt.where(Manuscript.status == "verified")
    return list(session.scalars(stmt).all())


def search_manuscripts(session: Session, query: str) -> list[Manuscript]:
    """LIKE search over title/identifier/AI+verified text (MVP scope)."""
    like = f"%{query}%"
    stmt = (
        select(Manuscript)
        .outerjoin(Transcription,
                   Transcription.manuscript_id == Manuscript.id)
        .options(selectinload(Manuscript.transcriptions))
        .where(or_(
            Manuscript.title.like(like),
            Manuscript.identifier.like(like),
            Transcription.ai_transcription.like(like),
            Transcription.verified_transcription.like(like),
        ))
        .order_by(Manuscript.id.desc())
    )
    # A manuscript with several matching transcriptions appears once.
    seen: dict[int, Manuscript] = {}
    for row in session.scalars(stmt).all():
        seen.setdefault(row.id, row)
    return list(seen.values())


# ---------------------------------------------------------------------------
# Transcriptions
# ---------------------------------------------------------------------------
def create_transcription(
    session: Session,
    manuscript_id: int,
    ai_text: str,
    model_name: str,
    inference_mode: str,
    config_id: int | None = None,
    model_version: str | None = None,
) -> Transcription:
    row = Transcription(
        manuscript_id=manuscript_id,
        ai_transcription=ai_text,
        verified_transcription=None,
        model_name=model_name,
        model_version=model_version,
        inference_mode=inference_mode,
        preprocessing_config_id=config_id,
        verification_status="pending",
    )
    session.add(row)
    manuscript = get_manuscript(session, manuscript_id)
    if manuscript is None:
        raise ValueError(f"Manuscript {manuscript_id} not found")
    manuscript.status = "transcribed"
    session.flush()
    return row


def verify_transcription(session: Session, transcription_id: int,
                         verified_text: str) -> Transcription:
    """Human verification: sets verified text + timestamps.

    ai_transcription is deliberately NOT in the UPDATE — it stays as the
    permanent record of what the model produced.
    """
    from datetime import datetime, timezone

    row = session.get(Transcription, transcription_id)
    if row is None:
        raise ValueError(f"Transcription {transcription_id} not found")
    row.verified_transcription = verified_text
    row.verification_status = "verified"
    row.verified_at = datetime.now(timezone.utc)
    manuscript = get_manuscript(session, row.manuscript_id)
    if manuscript is not None:
        manuscript.status = "verified"
    session.flush()
    return row
