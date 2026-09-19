#!/usr/bin/env python
"""Seed the demo library with real manuscripts (run once per demo DB).

Inserts manuscripts with their REAL model transcriptions (original
condition) as AI drafts (pending review) — verification happens live.
Idempotent unless --reset is given (which wipes manuscripts first).

Usage:
    python scripts/seed_library.py [--reset]
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo library")
    parser.add_argument("--reset", action="store_true",
                        help="Delete existing manuscripts first")
    args = parser.parse_args()

    init_db()
    session = SessionLocal()
    try:
        if args.reset:
            for ms in session.query(Manuscript).all():
                for d in (app_config.RAW_DATA_DIR / str(ms.id),
                          app_config.PROCESSED_DATA_DIR / str(ms.id)):
                    shutil.rmtree(d, ignore_errors=True)
            session.query(Transcription).delete()
            session.query(Manuscript).delete()
            session.commit()
            print("cleared existing manuscripts")

        cfg = repo.get_or_create_config(
            session, "original", PRESET_CONFIGS["original"].to_dict())
        done = 0
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
            done += 1
        session.commit()
        print(f"seeded {done} manuscripts (all pending review)")
    finally:
        session.close()


if __name__ == "__main__":
    main()
