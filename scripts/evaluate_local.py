#!/usr/bin/env python
"""Local-GPU accuracy harness: measure the real pipeline against expert refs.

Every accuracy claim in this project needs a number produced the same way, or
it cannot be compared with the last one. This runs the actual
restore -> segment -> transcribe path on MoDeTrans pages, scores the output
with the same CER/WER module the sweep used, and writes per-page results.

Why this exists: 8 of the 18 local transcriptions in the archive had no
reference to score against, so a regression like line segmentation shredding
each page into slivers (mean CER 0.345 -> 0.794) went unnoticed. Compare
against a reference or do not claim accuracy.

Usage:
    python scripts/evaluate_local.py --arm noseg --pages 10
    python scripts/evaluate_local.py --all-arms --pages 10
    python scripts/evaluate_local.py --report            # re-score, no GPU

The model is loaded once and kept resident across arms and pages, so a sweep
costs one ~65 s load rather than one per page.
"""

import argparse
import csv
import json
import re
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend import config as app_config
from backend.services import pipeline as pipeline_mod
from experiments.evaluation.compute_metrics import cer, edit_breakdown, wer

IMAGE_DIR = PROJECT_ROOT / "data" / "raw" / "mode_trans"
REF_DIR = PROJECT_ROOT / "data" / "evaluation"
OUT_DIR = PROJECT_ROOT / "experiments" / "results" / "eval"
WORK_DIR = PROJECT_ROOT / "data" / "processed" / "_eval"

# An "arm" is one set of pipeline settings. Names describe the setting, not a
# verdict on it — the numbers decide which one to ship.
ARMS: dict[str, dict] = {
    # Whole page, no decoding guard: the configuration the README's 0.316 mean
    # CER was measured with. Included to confirm this harness reproduces it.
    "plain": dict(config="original", segment=False, rep=1.0, max_new=256,
                  upscale=1.0),
    # Whole page + repetition guard + headroom on the token cap.
    "noseg": dict(config="original", segment=False, rep=1.05, max_new=512,
                  upscale=1.0),
    # Whole page + 1.5x pre-upscale, so the visual-token budget buys more
    # tokens per character (max_pixels alone cannot upscale).
    "up15": dict(config="original", segment=False, rep=1.05, max_new=512,
                 upscale=1.5),
    # Line segmentation, with the corrected band extents and aspect clamp.
    "seg": dict(config="original", segment=True, rep=1.05, max_new=512,
                upscale=1.0),
    # The UI's historical default pipeline, to price the preprocessing.
    "enh": dict(config="enhanced", segment=False, rep=1.05, max_new=512,
                upscale=1.0),
}

FIELDNAMES = ["arm", "page", "cer", "wer", "hyp_chars", "ref_chars",
              "S", "D", "I", "N", "secs", "lines", "error"]

# Held fixed across a preprocessing sweep so the restoration config is the
# only variable. These are the values measured as best-or-equal on clean pages
# (EVAL-01: repetition guard and token headroom were byte-identical to plain).
FIXED_DECODE = dict(segment=False, rep=1.05, max_new=512, upscale=1.0)

# Token-budget sweep. The whole page is 587k px, so a budget of 512*28*28
# forces a downscale and anything above 1280*28*28 is a no-op. Running these
# on an UNSCALED page separates "more visual tokens" from "distorted aspect
# ratio", which is the mechanism the segmentation result points at.
PIXEL_ARMS = {
    "px512": dict(config="original", **FIXED_DECODE, max_pixels=512 * 28 * 28),
    "px1280": dict(config="original", **FIXED_DECODE, max_pixels=1280 * 28 * 28),
    "px2048": dict(config="original", **FIXED_DECODE, max_pixels=2048 * 28 * 28),
}

# Inference levers, none of which had been tested before.
LEVER_ARMS = {
    "lever_base": dict(config="original", **FIXED_DECODE),
    "lever_beam4": dict(config="original", **FIXED_DECODE, num_beams=4),
    "lever_merge": dict(config="original", **FIXED_DECODE, merge=True),
    "lever_fp16": dict(config="original", **FIXED_DECODE, dtype="float16"),
}


def config_arm(config_name: str) -> dict:
    """An arm that varies only the restoration config."""
    return dict(config=config_name, **FIXED_DECODE)


def page_id(img: Path) -> str:
    """Map an image filename to its reference id.

    `MT-003.png` -> `MT-003`, and the degraded captures
    `MT-003_medium.png` -> `MT-003`, because the degradation is a property of
    the capture, not of the text.
    """
    stem = img.stem
    return stem if re.fullmatch(r"MT-\d+", stem) else stem.split("_")[0]


def all_pages(images_dir: Path) -> list[tuple[str, Path]]:
    """(page_id, image_path) for every image in dir that has a reference."""
    found = []
    for img in sorted(images_dir.glob("*.png")):
        pid = page_id(img)
        if (REF_DIR / f"{pid}_ref.txt").exists():
            found.append((pid, img))
    return found


def apply_arm(arm: dict) -> None:
    """Push an arm's settings into the live config the pipeline reads."""
    app_config.SEGMENT_LINES = bool(arm["segment"])
    app_config.REPETITION_PENALTY = float(arm["rep"])
    app_config.MAX_NEW_TOKENS = int(arm["max_new"])
    app_config.MODEL_UPSCALE = float(arm["upscale"])
    app_config.MAX_MODEL_PIXELS = int(
        arm.get("max_pixels", 1280 * 28 * 28))
    app_config.NUM_BEAMS = int(arm.get("num_beams", 1))
    app_config.COMPUTE_DTYPE = str(arm.get("dtype", "bfloat16"))
    # Merging rewrites weights and dtype changes how they are dequantised, so
    # an arm that differs in either needs its own load. Without this the arm
    # silently inherits the previous arm's weights and reports nothing real.
    app_config.MERGE_LORA = bool(arm.get("merge", False))
    import backend.services.transcription.local_qwen as lq

    if not lq.model_matches(app_config.COMPUTE_DTYPE, app_config.MERGE_LORA):
        lq.invalidate_model()
    # The service is wrapped from SEGMENT_LINES, so rebuild the wrapper. The
    # 3B model itself stays loaded in local_qwen's module globals.
    pipeline_mod.clear_service_cache()


def normalise(text: str) -> str:
    return " ".join((text or "").split())


def run_arm(arm_name: str, arm: dict, pages: list[tuple[str, Path]],
            tag: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    apply_arm(arm)

    print(f"\n=== arm '{arm_name}': {arm} ===", flush=True)
    cuda_failures = 0
    for i, (page, img_path) in enumerate(pages, start=1):
        hyp_path = OUT_DIR / f"{tag}_{arm_name}_{page}_hyp.txt"
        if hyp_path.exists():
            print(f"  [{i}/{len(pages)}] {page} skipped (resume)", flush=True)
            continue
        t0 = time.perf_counter()
        try:
            out = pipeline_mod.run_full_pipeline(
                img_path, arm["config"],
                output_dir=WORK_DIR / f"{tag}_{arm_name}_{page}")
            hyp_path.write_text(out.transcription, encoding="utf-8")
            dt = time.perf_counter() - t0
            # Timing is the point of the inference-lever sweep, and the arm may
            # be resumed days later, so it has to survive in the hypothesis
            # itself rather than in this process's memory.
            hyp_path.with_suffix(".meta.json").write_text(
                json.dumps({"secs": round(dt, 3),
                            "lines": int(getattr(out, "line_count", 0) or 0)}),
                encoding="utf-8")
            print(f"  [{i}/{len(pages)}] {page} {dt:6.1f}s "
                  f"chars={len(out.transcription)}", flush=True)
        except Exception as exc:  # noqa: BLE001
            dt = time.perf_counter() - t0
            # Deliberately do NOT write an empty hypothesis: a missing page must
            # be absent, never scored as CER 1.0 and quietly averaged in.
            print(f"  [{i}/{len(pages)}] {page} FAILED after {dt:.1f}s: "
                  f"{type(exc).__name__}: {exc}"[:200], flush=True)
            if _is_cuda_death(exc):
                cuda_failures += 1
                if cuda_failures >= 2:
                    print(f"  CUDA context is dead ({cuda_failures} in a row) — "
                          "stopping. Another process is probably holding the "
                          "GPU (the API server keeps its model resident), or "
                          "this card has run out of VRAM.", flush=True)
                    return


def _is_cuda_death(exc: BaseException) -> bool:
    """True for the unrecoverable CUDA errors that poison the whole process."""
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(k in text for k in (
        "cuda error: unknown error",
        "cudaerrorunknown",
        "out of memory",
        "cublas_status",
        "cuda_error",
    ))


def report(tag: str, pages: list[str], arms: list[str]) -> None:
    rows = []
    for arm_name in arms:
        for page, _img in pages:
            hyp = OUT_DIR / f"{tag}_{arm_name}_{page}_hyp.txt"
            if not hyp.exists():
                continue
            secs = 0.0
            lines = 0
            meta = hyp.with_suffix(".meta.json")
            if meta.exists():
                try:
                    m = json.loads(meta.read_text(encoding="utf-8"))
                    secs = float(m.get("secs") or 0.0)
                    lines = int(m.get("lines") or 0)
                except (ValueError, TypeError):
                    pass
            try:
                ref = normalise((REF_DIR / f"{page}_ref.txt")
                                .read_text(encoding="utf-8"))
                h = normalise(hyp.read_text(encoding="utf-8"))
                eb = edit_breakdown(h, ref)
                rows.append({
                    "arm": arm_name, "page": page,
                    "cer": round(cer(h, ref), 4), "wer": round(wer(h, ref), 4),
                    "hyp_chars": len(h), "ref_chars": len(ref),
                    "S": eb["S"], "D": eb["D"], "I": eb["I"], "N": eb["N"],
                    "secs": secs, "lines": lines, "error": "",
                })
            except Exception as exc:  # noqa: BLE001
                print(f"  score failed for {arm_name}/{page}: {exc}")

    if not rows:
        print("nothing to score — run an arm first")
        return

    csv_path = OUT_DIR / f"eval_{tag}_metrics.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{'arm':<8}{'n':>4}{'meanCER':>9}{'medCER':>8}{'meanWER':>9}"
          f"{'hyp/ref':>9}{'D(%)':>7}{'accuracy':>10}")
    incomplete = []
    for arm_name in arms:
        sub = [r for r in rows if r["arm"] == arm_name]
        if not sub:
            print(f"{arm_name:<8}{0:>4}   (no results)")
            continue
        if len(sub) < len(pages):
            incomplete.append((arm_name, len(sub)))
        cers = [r["cer"] for r in sub]
        wers = [r["wer"] for r in sub]
        ratio = statistics.mean(r["hyp_chars"] / max(1, r["ref_chars"])
                                for r in sub)
        # Share of reference characters the model failed to produce: the
        # adapter's dominant published error mode.
        dels = sum(r["D"] for r in sub)
        tot = sum(r["N"] for r in sub)
        mean_cer = statistics.mean(cers)
        print(f"{arm_name:<8}{len(sub):>4}{mean_cer:>9.3f}"
              f"{statistics.median(cers):>8.3f}{statistics.mean(wers):>9.3f}"
              f"{ratio:>9.2f}{100*dels/max(1,tot):>7.1f}"
              f"{100*(1-mean_cer):>9.1f}%")

    if incomplete:
        print("\nINCOMPLETE — these arms did not finish every page, so their "
              "means are not comparable:")
        for arm_name, got in incomplete:
            print(f"  {arm_name}: {got}/{len(pages)} pages")

    print(f"\nper-page CER")
    print(f"{'page':<9}" + "".join(f"{a:>9}" for a in arms))
    for page, _img in pages:
        cells = ""
        for arm_name in arms:
            hit = [r for r in rows if r["arm"] == arm_name and r["page"] == page]
            cells += f"{hit[0]['cer']:>9.3f}" if hit else f"{'-':>9}"
        print(f"{page:<9}{cells}")
    print(f"\nwrote {csv_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter)
    ap.add_argument("--arm", action="append", default=None,
                    help=f"arm name, repeatable. one of {list(ARMS)}")
    ap.add_argument("--all-arms", action="store_true")
    ap.add_argument("--configs", nargs="*", default=None,
                    help="sweep only the restoration config, holding decoding "
                         "fixed. arms are named c_<config>.")
    ap.add_argument("--pixels", nargs="*", default=None,
                    help="token-budget sweep, arms named px<k> (e.g. px512).")
    ap.add_argument("--levers", nargs="*", default=None,
                    help="inference-lever sweep, arms named lever_*.")
    ap.add_argument("--images", default=None,
                    help="image directory (default data/raw/mode_trans). Use "
                         "data/raw/realistic_<severity> for dirty captures.")
    ap.add_argument("--pages", type=int, default=10,
                    help="use the first N pages that have references")
    ap.add_argument("--tag", default="EVAL-01")
    ap.add_argument("--report", action="store_true",
                    help="re-score saved hypotheses without using the GPU")
    args = ap.parse_args()

    images_dir = Path(args.images) if args.images else IMAGE_DIR
    if not images_dir.is_absolute():
        images_dir = PROJECT_ROOT / images_dir
    pages = all_pages(images_dir)[:args.pages]
    if not pages:
        print(f"no pages with references found in {images_dir}")
        sys.exit(1)

    arms: dict[str, dict] = dict(ARMS)
    if args.configs:
        for cfg in args.configs:
            arms[f"c_{cfg}"] = config_arm(cfg)
    if args.pixels:
        arms.update({k: v for k, v in PIXEL_ARMS.items() if k in args.pixels})
    if args.levers:
        arms.update({k: v for k, v in LEVER_ARMS.items() if k in args.levers})

    if args.all_arms:
        names = list(ARMS)
    elif args.pixels:
        names = list(args.pixels)
    elif args.levers:
        names = list(args.levers)
    elif args.configs:
        names = [f"c_{c}" for c in args.configs]
    elif args.arm:
        names = args.arm
    else:
        names = ["noseg"]
    unknown = [n for n in names if n not in arms]
    if unknown:
        print(f"unknown arms: {unknown}; choose from {list(arms)}")
        sys.exit(1)

    print(f"images: {images_dir}")
    print(f"pages:  {pages[0][0]}..{pages[-1][0]} ({len(pages)})")
    if not args.report:
        for arm_name in names:
            run_arm(arm_name, arms[arm_name], pages, args.tag)
    report(args.tag, pages, names)


if __name__ == "__main__":
    main()