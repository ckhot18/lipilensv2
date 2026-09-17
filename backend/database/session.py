"""Engine/session management for the SQLite archive.

Repository functions take an injected Session, so tests build their own
engine — this module only serves the application database.
"""

from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend import config as app_config
from backend.database.models import Base


def make_engine(url: str):
    """Create an engine with SQLite thread-safety defaults."""
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine(app_config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create all tables (MVP: create_all; no migration tooling)."""
    if app_config.DATABASE_URL.startswith("sqlite:///"):
        db_file = app_config.DATABASE_URL.replace("sqlite:///", "")
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
