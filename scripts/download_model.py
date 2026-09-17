#!/usr/bin/env python
"""Resumable model-weight downloader (run YOURSELF in a terminal, not via agent).

    cd D:\\Projects\\lipilensv2
    .\\.venv\\Scripts\\python.exe scripts\\download_model.py [--no-xet]

- Resumes partial files automatically (safe to Ctrl+C and re-run).
- Uses D:\\hf_cache (C: is too small for ~7 GB of weights).
- Honors a logged-in HF token (run `huggingface_cli login` first for speed).
- --no-xet retries with the XET backend disabled (classic download path).
"""

import argparse
import os
import sys

DEFAULT_CACHE = r"D:\hf_cache"
REPOS = ["Qwen/Qwen2.5-VL-3B-Instruct", "lgtk/qwen25vl-3b-modi-synth-lora"]


def main() -> int:
    args = parse_args()
    if args.no_xet:
        os.environ["HF_HUB_DISABLE_XET"] = "1"
        print("XET backend disabled for this run.")

    os.environ.setdefault("HF_HOME", DEFAULT_CACHE)
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", os.path.join(DEFAULT_CACHE, "hub"))

    from huggingface_hub import HfFolder, snapshot_download

    token = HfFolder.get_token()
    print(f"Cache : {os.environ['HUGGINGFACE_HUB_CACHE']}")
    print(f"Auth  : {'logged in (good)' if token else 'ANONYMOUS (slow tier - consider login)'}")

    for repo in REPOS:
        print(f"\n=== Downloading {repo} ===")
        try:
            path = snapshot_download(repo_id=repo)
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED: {repo}: {exc}")
            print("Tip: Ctrl+C-safe, just re-run. Or retry with --no-xet.")
            return 1
        print(f"OK: {repo} -> {path}")

    print("\nALL DOWNLOADS COMPLETE - tell the agent to run scripts/smoke_test_model.py")
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="Resumable LipiLens weight downloader")
    parser.add_argument("--no-xet", action="store_true",
                        help="Disable XET backend (classic S3-redirect download path)")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
