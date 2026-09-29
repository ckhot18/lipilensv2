#!/usr/bin/env python
"""Fetch demo images for live demonstrations (NOT research data).

Downloads N real MoDeTrans pages + their expert readings into demo_images/
for uploading during demos. Nothing here touches the database, the
MANIFEST, or the experiment logs — these files are demo props only.

Usage: python scripts/fetch_demo.py --count 25
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUT_DIR = PROJECT_ROOT / "demo_images"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch demo images")
    parser.add_argument("--count", type=int, default=25)
    args = parser.parse_args()

    from datasets import load_dataset

    manifest = json.loads(
        (PROJECT_ROOT / "data" / "raw" / "mode_trans" / "MANIFEST.json")
        .read_text())
    used = {m["src"] for m in manifest}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sources = []
    next_id = 1
    for row in load_dataset("historyHulk/MoDeTrans", split="train",
                            streaming=True):
        fname = row.get("filename") or ""
        text = (row.get("text") or "").strip()
        if fname in used or not (60 <= len(text) <= 300):
            continue
        did = f"D-{next_id:02d}"
        next_id += 1
        img = row.get("image")
        if img is None:
            continue
        img.convert("RGB").save(OUT_DIR / f"{did}.png")
        (OUT_DIR / f"{did}_ref.txt").write_text(text, encoding="utf-8")
        sources.append({"id": did, "src": fname, "ref_chars": len(text)})
        used.add(fname)
        print(f"{did} <- {fname} ({len(text)} chars)", flush=True)
        if len(sources) >= args.count:
            break

    (OUT_DIR / "SOURCES.json").write_text(json.dumps(sources, indent=2))
    print(f"saved {len(sources)} demo images to demo_images/")


if __name__ == "__main__":
    main()
