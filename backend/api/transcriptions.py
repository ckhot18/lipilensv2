"""Transcription routes: human verification."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.schemas.manuscript import TranscriptionResponse, VerifyRequest
from backend.services.archive import repository as repo

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


@router.put("/{transcription_id}/verify",
            response_model=TranscriptionResponse)
def verify_transcription(transcription_id: int, body: VerifyRequest,
                         session: Session = Depends(get_db)):
    try:
        row = repo.verify_transcription(session, transcription_id,
                                        body.verified_transcription)
    except ValueError:
        raise HTTPException(404, "Transcription not found") from None
    session.commit()
    return TranscriptionResponse.model_validate(row)
