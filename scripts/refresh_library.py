#!/usr/bin/env python
"""Refresh the demo library: prune orphans, reseed 12 manuscripts, verify 4.

Usage:
    python scripts/refresh_library.py [--dry-run]
"""

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.models import Manuscript, Transcription
from backend.database.session import SessionLocal, init_db
from backend.services.archive import repository as repo
from backend.services.restoration.pipeline import PRESET_CONFIGS
from backend import config as app_config

# Reuse constants from seed_library.py
SEED_IDS = ["MT-002", "MT-003", "MT-007", "MT-010", "MT-011", "MT-014",
            "MT-015", "MT-019", "MT-038", "MT-044", "MT-048", "MT-050"]
HYP_TAG = {}
for i in range(1, 4):
    HYP_TAG[f"MT-{i:03d}"] = "EXP-002"
for i in range(4, 21):
    HYP_TAG[f"MT-{i:03d}"] = "EXP-004"
for i in range(21, 51):
    HYP_TAG[f"MT-{i:03d}"] = "EXP-006"

MODEL_NAME = "Qwen2.5-VL-3B + lgtk/qwen25vl-3b-modi-synth-lora"

# Which 4 to verify — spread across the set (indices 1, 4, 7, 10 -> MT-003, MT-011, MT-019, MT-044)
VERIFY_INDICES = [1, 4, 7, 10]


def delete_orphan_manuscripts(session, dry_run: bool) -> list[int]:
    """Delete manuscripts with zero transcriptions and their data dirs."""
    deleted_ids = []
    orphans = session.query(Manuscript).outerjoin(
        Transcription, Transcription.manuscript_id == Manuscript.id
    ).group_by(Manuscript.id).having(
        Transcription.id.is_(None)
    ).all()

    for ms in orphans:
        deleted_ids.append(ms.id)
        if not dry_run:
            for d in (app_config.RAW_DATA_DIR / str(ms.id),
                      app_config.PROCESSED_DATA_DIR / str(ms.id)):
                shutil.rmtree(d, ignore_errors=True)
            session.delete(ms)

    if not dry_run:
        session.commit()

    return deleted_ids


def delete_existing_seeded_manuscripts(session, dry_run: bool) -> list[int]:
    """Delete existing manuscripts that match SEED_IDS (by identifier) to avoid duplicates."""
    deleted_ids = []
    # Find ALL manuscripts whose identifier matches one of the SEED_IDS
    for mid in SEED_IDS:
        identifier = f"{mid}.png"
        manuscripts = session.query(Manuscript).filter(Manuscript.identifier == identifier).all()
        for ms in manuscripts:
            deleted_ids.append(ms.id)
            if not dry_run:
                for d in (app_config.RAW_DATA_DIR / str(ms.id),
                          app_config.PROCESSED_DATA_DIR / str(ms.id)):
                    shutil.rmtree(d, ignore_errors=True)
                session.delete(ms)

    if not dry_run:
        session.commit()

    return deleted_ids


def seed_manuscripts(session, dry_run: bool) -> list[tuple[int, str]]:
    """Seed the 12 manuscripts using existing logic. Returns list of (id, seed_id)."""
    cfg = repo.get_or_create_config(
        session, "original", PRESET_CONFIGS["original"].to_dict())
    seeded = []

    for mid in SEED_IDS:
        src_img = (PROJECT_ROOT / "data" / "raw" / "mode_trans" /
                   f"{mid}.png")
        hyp_file = (PROJECT_ROOT / "experiments" / "results" /
                    f"{HYP_TAG[mid]}_{mid}_hyp.txt")
        if not src_img.exists() or not hyp_file.exists():
            print(f"SKIP {mid} (missing files)")
            continue

        ms = repo.create_manuscript(
            session, title=f"Manuscript {mid}",
            original_image_path="pending", identifier=f"{mid}.png")
        session.flush()

        raw_dir = app_config.RAW_DATA_DIR / str(ms.id)
        proc_dir = app_config.PROCESSED_DATA_DIR / str(ms.id)
        if not dry_run:
            raw_dir.mkdir(parents=True, exist_ok=True)
            proc_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(src_img, raw_dir / "original.png")
            # Original condition = verified no-op: restored is the same image.
            shutil.copy(src_img, proc_dir / "original_original.png")
            ms.original_image_path = str(raw_dir / "original.png")
            session.flush()
            repo.mark_restored(
                session, ms.id, str(proc_dir / "original_original.png"),
                cfg.id)
            repo.create_transcription(
                session, ms.id,
                ai_text=hyp_file.read_text(encoding="utf-8").strip(),
                model_name=MODEL_NAME, inference_mode="colab",
                config_id=cfg.id)
        seeded.append((ms.id, mid))

    if not dry_run:
        session.commit()

    return seeded


def verify_manuscripts(session, seeded: list[tuple[int, str]], dry_run: bool) -> int:
    """Verify 4 manuscripts using evaluation reference texts."""
    verified_count = 0

    for idx in VERIFY_INDICES:
        if idx >= len(seeded):
            continue
        ms_id, mid = seeded[idx]
        ref_file = PROJECT_ROOT / "data" / "evaluation" / f"{mid}_ref.txt"
        if not ref_file.exists():
            print(f"SKIP verification for {mid} (no reference file)")
            continue

        verified_text = ref_file.read_text(encoding="utf-8").strip()

        if not dry_run:
            # Find the transcription for this manuscript
            tr = session.query(Transcription).filter(
                Transcription.manuscript_id == ms_id
            ).first()

            if tr is None:
                print(f"SKIP verification for {mid} (no transcription)")
                continue

            repo.verify_transcription(session, tr.id, verified_text)
            verified_count += 1
        else:
            # In dry-run, just verify the reference file exists
            verified_count += 1

    if not dry_run:
        session.commit()

    return verified_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh demo library")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done without changing anything")
    args = parser.parse_args()

    if args.dry_run:
        print("=== DRY RUN ===")

    init_db()
    session = SessionLocal()
    try:
        # Step 1: Delete orphans (no transcription)
        deleted_orphans = delete_orphan_manuscripts(session, args.dry_run)
        print(f"Would delete {len(deleted_orphans)} orphan manuscripts: {deleted_orphans}")

        # Step 1b: Delete existing seeded manuscripts to avoid duplicates
        deleted_seeded = delete_existing_seeded_manuscripts(session, args.dry_run)
        print(f"Would delete {len(deleted_seeded)} existing seeded manuscripts: {deleted_seeded}")

        # Step 2: Seed manuscripts
        seeded = seed_manuscripts(session, args.dry_run)
        print(f"Would seed {len(seeded)} manuscripts: {[mid for _, mid in seeded]}")

        # Step 3: Verify 4 manuscripts
        verified_count = verify_manuscripts(session, seeded, args.dry_run)
        print(f"Would verify {verified_count} manuscripts (indices {VERIFY_INDICES})")

        if args.dry_run:
            print("=== DRY RUN COMPLETE (no changes made) ===")
        else:
            print("=== REFRESH COMPLETE ===")
    finally:
        session.close()


if __name__ == "__main__":
    main()