"""Database tests (Phase 5) — temp SQLite file, no app DB touched."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from sqlalchemy.orm import Session

from backend.database.models import Base
from backend.database.session import make_engine
from backend.services.archive import repository as repo
from backend.services.restoration.pipeline import PRESET_CONFIGS


@pytest.fixture()
def session(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_full_lifecycle(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/life.db")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        cfg = repo.get_or_create_config(
            session, "enhanced", PRESET_CONFIGS["enhanced"].to_dict())
        ms = repo.create_manuscript(
            session, title="MT-002", original_image_path="a.png",
            image_sha256="abc123", identifier="10.jpg")
        assert ms.status == "uploaded"

        repo.mark_restored(session, ms.id, "a_enhanced.png", cfg.id)
        assert repo.get_manuscript(session, ms.id).status == "restored"

        tr = repo.create_transcription(
            session, ms.id, ai_text="hyp text", model_name="m",
            inference_mode="colab", config_id=cfg.id)
        assert tr.verification_status == "pending"
        assert tr.verified_transcription is None
        assert repo.get_manuscript(session, ms.id).status == "transcribed"

        repo.verify_transcription(session, tr.id, "fixed text")
        got = repo.get_manuscript(session, ms.id)
        assert got.status == "verified"
        assert got.transcriptions[0].verified_transcription == "fixed text"
        assert got.transcriptions[0].verified_at is not None
        # AI draft untouched by verification.
        assert got.transcriptions[0].ai_transcription == "hyp text"
        session.commit()


def test_ai_transcription_immutable_at_sql_level(session):
    cfg = repo.get_or_create_config(session, "original",
                                    PRESET_CONFIGS["original"].to_dict())
    ms = repo.create_manuscript(session, "t", "o.png")
    tr = repo.create_transcription(session, ms.id, "draft", "m", "colab",
                                   cfg.id)
    before = tr.ai_transcription
    repo.verify_transcription(session, tr.id, "corrected")
    session.expire_all()
    assert session.get(type(tr), tr.id).ai_transcription == before


def test_reverify_updates_verified_text_only(session):
    ms = repo.create_manuscript(session, "t", "o.png")
    tr = repo.create_transcription(session, ms.id, "draft", "m", "colab")
    repo.verify_transcription(session, tr.id, "v1")
    repo.verify_transcription(session, tr.id, "v2")
    session.expire_all()
    got = session.get(type(tr), tr.id)
    assert got.verified_transcription == "v2"
    assert got.ai_transcription == "draft"


def test_search_matches_title_and_text(session):
    m1 = repo.create_manuscript(session, "Shivaji letter", "a.png")
    repo.create_transcription(session, m1.id, "राजमान्य रघोजी", "m", "colab")
    m2 = repo.create_manuscript(session, "Ledger page", "b.png",
                                identifier="ACC-42")
    repo.create_transcription(session, m2.id, "unrelated words here", "m",
                              "colab")
    assert [m.id for m in repo.search_manuscripts(session, "Shivaji")] == [m1.id]
    assert [m.id for m in repo.search_manuscripts(session, "ACC-42")] == [m2.id]
    assert [m.id for m in repo.search_manuscripts(session, "रघोजी")] == [m1.id]
    assert repo.search_manuscripts(session, "no-such-thing") == []


def test_search_prefers_verified_once_present(session):
    ms = repo.create_manuscript(session, "t", "o.png")
    tr = repo.create_transcription(session, ms.id, " gibberish xyz", "m",
                                   "colab")
    assert repo.search_manuscripts(session, "corrected") == []
    repo.verify_transcription(session, tr.id, "corrected reading")
    assert [m.id for m in repo.search_manuscripts(session, "corrected")] == \
        [ms.id]


def test_missing_ids_raise(session):
    with pytest.raises(ValueError):
        repo.mark_restored(session, 999, "x.png", 1)
    with pytest.raises(ValueError):
        repo.create_transcription(session, 999, "t", "m", "colab")
    with pytest.raises(ValueError):
        repo.verify_transcription(session, 999, "t")
    assert repo.get_manuscript(session, 999) is None


def test_list_and_verified_filter(session):
    m1 = repo.create_manuscript(session, "a", "a.png")
    repo.create_manuscript(session, "b", "b.png")
    assert len(repo.list_manuscripts(session)) == 2
    assert repo.list_manuscripts(session, verified_only=True) == []
    tr = repo.create_transcription(session, m1.id, "t", "m", "colab")
    repo.verify_transcription(session, tr.id, "v")
    assert [m.id for m in
            repo.list_manuscripts(session, verified_only=True)] == [m1.id]


def test_config_reuse_returns_same_row(session):
    d = PRESET_CONFIGS["binarized"].to_dict()
    a = repo.get_or_create_config(session, "binarized", d)
    b = repo.get_or_create_config(session, "binarized", d)
    assert a.id == b.id
