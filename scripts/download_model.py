#!/usr/bin/env python
"""Resumable model downloader for LipiLens.

    python scripts/download_model.py                 # pinned base model + LoRA
    python scripts/download_model.py --repo org/name  # other repo (repeatable)

Weights land in the Hugging Face cache the backend reads from.  Finished files
are never fetched again and a half-finished file resumes chunk-by-chunk via the
Xet transport (``--no-xet`` falls back to plain HTTP, which restarts an
interrupted file).  A live byte/file bar is drawn on stderr and a heartbeat line
is written to stdout and ``<cache>/download_progress.log`` every 30 s.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import (  # noqa: E402
    BASE_MODEL_NAME,
    BASE_MODEL_REVISION,
    LORA_ADAPTER_NAME,
    LORA_REVISION,
)

DEFAULT_CACHE_BASE = Path(r"D:\hf_cache")
LOG_NAME = "download_progress.log"
DEFAULT_REPOS = [
    f"{BASE_MODEL_NAME}@{BASE_MODEL_REVISION}",
    f"{LORA_ADAPTER_NAME}@{LORA_REVISION}",
]

BYTES_BAR_FORMAT = "{desc:<24}{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} {rate_fmt} {elapsed}<{remaining}"
FILES_BAR_FORMAT = "{desc:<24}{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} {elapsed}<{remaining}"

STATE = {
    "label": "",
    "bytes_done": 0.0,
    "bytes_total": 0,
    "pending": 0,
    "files_done": 0,
    "files_total": 0,
    "bytes_bar": None,
    "bar_cls": None,
    "log": None,
    "hb_clock": 0.0,
    "hb_done": 0.0,
}


def _size(num: float) -> str:
    num = float(num)
    if abs(num) >= 1e9:
        return f"{num / 1e9:.2f} GB"
    if abs(num) >= 1e6:
        return f"{num / 1e6:.1f} MB"
    if abs(num) >= 1e3:
        return f"{num / 1e3:.1f} kB"
    return f"{num:.0f} B"


def _dur(seconds: float | None) -> str:
    if seconds is None or seconds != seconds or seconds < 0:
        return "--:--:--"
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def log(msg: str, *, bar_safe: bool = False) -> None:
    bar_cls = STATE["bar_cls"]
    if bar_safe and bar_cls is not None and sys.stdout.isatty():
        bar_cls.write(msg)
    else:
        print(msg, flush=True)
    if STATE["log"]:
        try:
            with Path(STATE["log"]).open("a", encoding="utf-8") as handle:
                handle.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
        except OSError:
            pass


def _heartbeat_message() -> str:
    done, total = STATE["bytes_done"], STATE["bytes_total"]
    now = time.monotonic()
    span = max(now - STATE["hb_clock"], 1e-9)
    speed = max(done - STATE["hb_done"], 0.0) / span
    STATE["hb_clock"], STATE["hb_done"] = now, done
    pct = (100.0 * done / total) if total else 100.0
    eta = (total - done) / speed if speed > 0 and total > done else None
    return (
        f"[{time.strftime('%H:%M:%S')}] {STATE['label']}: {pct:5.1f}%  "
        f"{_size(done)} / {_size(total)}  {_size(speed)}/s  "
        f"ETA {_dur(eta)}  files {STATE['files_done']}/{STATE['files_total']}"
    )


class _Heartbeat(threading.Thread):
    def __init__(self, interval: float):
        super().__init__(name="download-heartbeat", daemon=True)
        self.interval = max(float(interval), 0.25)
        self._halt = threading.Event()
        STATE["hb_clock"] = time.monotonic()
        STATE["hb_done"] = STATE["bytes_done"]

    def run(self) -> None:
        while not self._halt.wait(self.interval):
            try:
                log(_heartbeat_message(), bar_safe=True)
            except Exception:
                pass

    def stop(self) -> None:
        self._halt.set()
        self.join(timeout=2.0)


def _make_bar_class():
    from huggingface_hub.utils.tqdm import tqdm as hf_tqdm

    class Bar(hf_tqdm):
        def __init__(self, *args, **kwargs):
            desc = str(kwargs.get("desc") or "")
            lowered = desc.lower()
            if desc.startswith("Fetching") or (kwargs.get("unit") == "it" and "file" in lowered):
                kind = "files"
            elif "byte" in lowered or "transfer" in lowered:
                kind = "transfer"
            elif "reconstruct" in lowered or kwargs.get("unit") == "B":
                kind = "reconstruct"
            else:
                kind = "other"
            self._kind = kind
            if kind == "transfer":
                kwargs["bar_format"] = BYTES_BAR_FORMAT
                kwargs["desc"] = STATE["label"] or "download"
                kwargs.setdefault("position", 0)
                kwargs.setdefault("leave", False)
                if not STATE["pending"]:
                    kwargs["disable"] = True
                STATE["bytes_bar"] = self
            elif kind == "files":
                kwargs["bar_format"] = FILES_BAR_FORMAT
                kwargs["desc"] = "files"
                kwargs.setdefault("position", 1)
                kwargs.setdefault("leave", False)
                if not STATE["pending"]:
                    kwargs["disable"] = True
            else:
                kwargs["disable"] = True
            kwargs.setdefault("mininterval", 0.2)
            kwargs.setdefault("disable", None)
            super().__init__(*args, **kwargs)

        def update(self, n=1):
            step = n or 0
            if self._kind == "transfer":
                STATE["bytes_done"] = max(0.0, STATE["bytes_done"] + step)
            elif self._kind == "files":
                STATE["files_done"] += max(0, int(step))
            return super().update(n)

    return Bar


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="download_model.py",
        description="Download the LipiLens model weights into the local Hugging Face cache.",
    )
    parser.add_argument(
        "--repo",
        action="append",
        metavar="REPO[@REVISION]",
        help="repository to fetch (repeatable); default: pinned base model + LoRA",
    )
    parser.add_argument("--cache-dir", type=Path, default=None, help="HF cache directory")
    parser.add_argument("--workers", type=int, default=8, help="parallel file downloads (default: 8)")
    parser.add_argument("--no-xet", action="store_true", help="plain HTTP instead of the Xet transport")
    parser.add_argument(
        "--heartbeat",
        type=float,
        default=30.0,
        metavar="SECONDS",
        help="progress heartbeat interval (default: 30)",
    )
    return parser.parse_args(argv)


def _prepare_env(args: argparse.Namespace) -> Path:
    if args.no_xet:
        os.environ["HF_HUB_DISABLE_XET"] = "1"
    if args.cache_dir:
        os.environ["HF_HUB_CACHE"] = str(args.cache_dir)
    elif not os.environ.get("HF_HUB_CACHE") and not os.environ.get("HF_HOME"):
        if Path(DEFAULT_CACHE_BASE.anchor).exists():
            os.environ["HF_HOME"] = str(DEFAULT_CACHE_BASE)
    from huggingface_hub.constants import HF_HUB_CACHE

    return Path(HF_HUB_CACHE)


def _download(api, spec: str, cache_dir: Path, args: argparse.Namespace) -> tuple[bool, str]:
    from huggingface_hub import snapshot_download, try_to_load_from_cache

    repo, _, revision = spec.partition("@")
    info = api.model_info(repo_id=repo, revision=revision or "main", files_metadata=True)
    sha = info.sha
    sizes = {entry.rfilename: int(entry.size or 0) for entry in info.siblings}
    total = sum(sizes.values())
    cached = sum(
        size
        for name, size in sizes.items()
        if isinstance(try_to_load_from_cache(repo, name, cache_dir=cache_dir, revision=sha), str)
    )

    STATE.update(
        label=repo.rsplit("/", 1)[-1],
        bytes_done=float(cached),
        bytes_total=total,
        pending=total - cached,
        files_done=0,
        files_total=len(sizes),
        bytes_bar=None,
    )

    log("")
    log(f"{repo} @ {sha}  ({len(sizes)} files / {_size(total)}, {_size(cached)} cached)")
    snapshot = Path(cache_dir) / f"models--{repo.replace('/', '--')}" / "snapshots" / sha
    if STATE["pending"] <= 0:
        log(f"OK {repo} -> {snapshot}  ({_size(total)}, already cached)")
        return True, "already cached"

    log(f"fetching {_size(STATE['pending'])} ...")
    monitor = _Heartbeat(args.heartbeat)
    monitor.start()
    started = time.monotonic()
    try:
        snapshot = Path(
            snapshot_download(
                repo_id=repo,
                revision=sha,
                cache_dir=cache_dir,
                max_workers=args.workers,
                tqdm_class=STATE["bar_cls"],
                library_name="lipilens",
            )
        )
    finally:
        monitor.stop()
        bar = STATE.get("bytes_bar")
        if bar is not None:
            try:
                bar.close()
            except Exception:
                pass
    elapsed = max(time.monotonic() - started, 1e-9)
    log(f"OK {repo} -> {snapshot}  ({_size(total)} in {_dur(elapsed)})")
    return True, _dur(elapsed)


def _run(args: argparse.Namespace) -> int:
    cache_dir = _prepare_env(args)
    STATE["log"] = Path(cache_dir) / LOG_NAME
    try:
        Path(STATE["log"]).parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    from huggingface_hub import HfApi

    STATE["bar_cls"] = _make_bar_class()
    log(f"cache: {cache_dir}   log: {STATE['log']}   transport: {'http' if args.no_xet else 'xet'}")

    api = HfApi()
    results = []
    for spec in args.repo or DEFAULT_REPOS:
        try:
            results.append((spec, *_download(api, spec, cache_dir, args)))
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            log(f"FAILED {spec}: {type(exc).__name__}: {exc}")
            results.append((spec, False, str(exc)))

    log("")
    for spec, ok, detail in results:
        log(f"  {'OK  ' if ok else 'FAIL'} {spec}  {detail}")
    if all(ok for _, ok, _ in results):
        log("ALL DONE")
        return 0
    return 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        return _run(args)
    except KeyboardInterrupt:
        log("")
        log("Interrupted - finished files are kept, re-run the same command to resume.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
