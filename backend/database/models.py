"""SQLAlchemy schema for the LipiLens archive (PROJECT_GUIDE.md Sec. 16).

Three tables:
- manuscripts: one row per uploaded page; original image path is immutable.
- transcriptions: AI draft (immutable once written) + human-verified text.
- preprocessing_configs: named restoration configs with exact JSON params,
  so every restoration run is reproducible.

Only services/archive/repository.py may use these models — never routes.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PreprocessingConfigRow(Base):
    __tablename__ = "preprocessing_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Manuscript(Base):
    __tablename__ = "manuscripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    identifier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    author: Mapped[str | None] = mapped_column(String(256), nullable=True)
    date: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(256), nullable=True)
    collection: Mapped[str | None] = mapped_column(String(256), nullable=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    image_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    restored_image_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    preprocessing_config_id: Mapped[int | None] = mapped_column(
        ForeignKey("preprocessing_configs.id"), nullable=True
    )
    # uploaded | restored | transcribed | verified
    status: Mapped[str] = mapped_column(String(16), default="uploaded",
                                        nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(),
        nullable=False,
    )

    config: Mapped[PreprocessingConfigRow | None] = relationship(lazy="joined")
    transcriptions: Mapped[list["Transcription"]] = relationship(
        back_populates="manuscript", cascade="all, delete-orphan",
        order_by="Transcription.id",
    )


class Transcription(Base):
    __tablename__ = "transcriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manuscript_id: Mapped[int] = mapped_column(
        ForeignKey("manuscripts.id"), nullable=False, index=True
    )
    # Immutable once written — repository never UPDATEs this column.
    ai_transcription: Mapped[str] = mapped_column(Text, nullable=False)
    verified_transcription: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    model_name: Mapped[str] = mapped_column(String(256), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # local | colab
    inference_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    preprocessing_config_id: Mapped[int | None] = mapped_column(
        ForeignKey("preprocessing_configs.id"), nullable=True
    )
    # pending | verified
    verification_status: Mapped[str] = mapped_column(
        String(16), default="pending", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    manuscript: Mapped[Manuscript] = relationship(back_populates="transcriptions")
