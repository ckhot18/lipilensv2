#!/usr/bin/env python
"""Fetch MoDeTrans samples with ground truth into data/ (reusable).

Usage:
    python scripts/fetch_modetrans.py --count 7 --min-len 60 --max-len 220 \\
        --skip 1.jpg 10.jpg 1000.jpg --start-id 4

Writes data/raw/mode_trans/MT-*.png, data/evaluation/MT-*_ref.txt and updates
data/raw/mode_trans/MANIFEST.json (never overwrites existing IDs).
"""

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "mode_trans"
EVAL_DIR = PROJECT_ROOT / "data" / "evaluation"
MANIFEST = RAW_DIR / "MANIFEST.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch MoDeTrans samples")
    parser.add_argument("--count", type=int, default=7)
    parser.add_argument("--min-len", type=int, default=60)
    parser.add_argument("--max-len", type=int, default=220)
    parser.add_argument("--skip", nargs="*", default=[])
    parser.add_argument("--start-id", type=int, default=4)
    args = parser.parse_args()

    from datasets import load_dataset

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    used_src = {m["src"] for m in manifest} | set(args.skip)

    ds = load_dataset("historyHulk/MoDeTrans", split="train", streaming=True)
    picked = []
    next_id = args.start_id

    # Simple single-pass scan (streaming datasets are forward-only).
    seen = 0
    for row in ds:
        fname = row.get("filename") or f"row-{seen}"
        text = (row.get("text") or "").strip()
        seen += 1
        if fname in used_src:
            continue
        if not (args.min_len <= len(text) <= args.max_len):
            continue
        mid = f"MT-{next_id:03d}"
        next_id += 1
        img = row.get("image")
        if img is None:
            continue
        img.convert("RGB").save(RAW_DIR / f"{mid}.png")
        (EVAL_DIR / f"{mid}_ref.txt").write_text(text, encoding="utf-8")
        manifest.append({"id": mid, "src": fname, "ref_chars": len(text)})
        used_src.add(fname)
        picked.append((mid, fname, len(text)))
        print(f"{mid} <- {fname} ({len(text)} chars)", flush=True)
        if len(picked) >= args.count:
            break

    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(f"scanned={seen} picked={len(picked)}")


if __name__ == "__main__":
    main()
