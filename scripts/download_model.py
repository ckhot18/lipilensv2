#!/usr/bin/env python
"""Resumable model‑weight downloader for LipiLens – with visible progress.

Features
--------
* Prints a one‑line progress update every ~30 s.
* Writes the same line to `D:\hf_cache\download_progress.log`.
* Respects `--no‑xet` and the HF cache environment variables.
* Safe to Ctrl‑C and re‑run (partial files are kept).
"""

import argparse, os, sys, time, pathlib
from pathlib import Path

DEFAULT_CACHE = r"D:\hf_cache"
REPOS = ["Qwen/Qwen2.5-VL-3B-Instruct", "lgtk/qwen25vl-3b-modi-synth-lora"]
LOG = Path(DEFAULT_CACHE) / "download_progress.log"


def log(msg: str):
    """Append msg to log file and print to console."""
    try:
        LOG.open("a", encoding="utf-8").write(msg + "\n")
    except Exception:
        pass
    print(msg)


def progress(downloaded, total):
    """Throttled progress line (≈30 s intervals)."""
    global _t
    now = time.time()
    if now - _t < 30:
        return
    _t = now
    pct = 100.0 * downloaded / total if total else 0
    log(f"Progress: {pct:5.1f}% ({downloaded/1024/1024:6.1f} / {total/1024/1024:6.1f} MB)")


_t = 0
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--no-xet", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    os.environ.setdefault("HF_HOME", DEFAULT_CACHE)
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", DEFAULT_CACHE + "\\hub")
    if args.no_xet:
        os.environ["HF_HUB_DISABLE_XET"] = "1"
        log("XET disabled")
    from huggingface_hub import HfFolder, snapshot_download

    token = HfFolder.get_token()
    log(f"Cache: {os.environ['HF_HOME']} | token: {'yes' if token else 'no'}")

    for repo in REPOS:
        log(f"Downloading {repo}")
        start = time.time()
        dl = {"got": 0, "tot": None}

        def cb(transferred, total_bytes):
            dl["got"] = transferred
            dl["tot"] = total_bytes
            progress(transferred, total_bytes)

        try:
            path = snapshot_download(repo_id=repo, resume_download=True,
                                     progress_callback=cb)
        except Exception as e:
            log(f"FAILED {repo}: {e}")
            return 1

        # final summary
        total_bytes = sum(f.stat().st_size
                          for f in Path(path).rglob("*") if f.is_file())
        elapsed = time.time() - start
        log(f"OK {repo} → {path} ({total_bytes/1024/1024:.1f} MB, {elapsed:.1f}s)")

    log("ALL DONE")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("\nInterrupted – partial files kept")
        sys.exit(1)