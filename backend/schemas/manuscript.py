"""Manuscript request/response models."""

from datetime import datetime

from pydantic import BaseModel, Field


class ManuscriptSummary(BaseModel):
    id: int
    title: str
    identifier: str | None = None
    status: str
    verified: bool = False
    thumbnail_url: str | None = None

    model_config = {"from_attributes": True}


class TranscriptionResponse(BaseModel):
    id: int
    manuscript_id: int
    ai_transcription: str
    verified_transcription: str | None = None
    verification_status: str
    model_name: str
    inference_mode: str
    created_at: datetime
    verified_at: datetime | None = None

    model_config = {"from_attributes": True}


class ManuscriptDetail(BaseModel):
    id: int
    title: str
    identifier: str | None = None
    author: str | None = None
    date: str | None = None
    source: str | None = None
    collection: str | None = None
    location: str | None = None
    notes: str | None = None
    status: str
    original_image_url: str | None = None
    restored_image_url: str | None = None
    created_at: datetime
    transcription: TranscriptionResponse | None = None
    # True when an identical (image, config) upload already existed and the
    # existing record was returned instead of creating a duplicate row.
    duplicate: bool = False

    model_config = {"from_attributes": True}


class VerifyRequest(BaseModel):
    verified_transcription: str = Field(min_length=1, max_length=5000)
