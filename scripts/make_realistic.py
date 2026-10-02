#!/usr/bin/env python
"""Simulate real photographic capture of authentic Modi-script pages.

The MoDeTrans corpus is distributed as clean greyscale line crops, so it cannot
show what a restoration pipeline does to a real photograph: aged paper, uneven
lighting, colour cast, stains, skew, sensor noise and JPEG artefacts. This
script keeps the authentic script content and re-photographs it.

IMPORTANT: the script content and ground truth are authentic (MoDeTrans, IIT
Roorkee / MIT). Only the *capture* is simulated. Never present the output as a
real scan; it is a controlled degradation, which is what the H2 robustness test
needs anyway.

Usage:
    python scripts/make_realistic.py --severity medium --count 8
    python scripts/make_realistic.py --severity severe --out data/raw/realistic

Severities (documented, seeded per sample so runs are reproducible):
    mild    paper tint + gentle vignette + light grain
    medium  + colour cast, foxing stains, skew, JPEG artefacts
    severe  + heavy uneven lighting, gutter shadow, blur, strong noise
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SRC_DIR = PROJECT_ROOT / "data" / "raw" / "mode_trans"
EVAL_DIR = PROJECT_ROOT / "data" / "evaluation"

# Aged-paper base colours (BGR). Indigo ink stays near-black but picks up a
# warm/brown cast from the paper it sits on.
PAPER = {
    "cream": (232, 226, 208),
    "tan": (206, 196, 170),
    "grey": (214, 210, 200),
}
CASTS = {
    "tungsten": (1.06, 0.98, 0.88),
    "fluorescent": (0.95, 1.02, 1.05),
    "daylight": (1.0, 1.0, 1.0),
}

SEVERITY = {
    "mild": dict(cast=0.5, vignette=0.22, noise=4.0, foxing=0, skew=0.0,
                 jpeg=0, blur=0.0, uneven=0.10, gutter=0.0),
    "medium": dict(cast=1.0, vignette=0.34, noise=8.0, foxing=9, skew=0.9,
                   jpeg=55, blur=0.4, uneven=0.22, gutter=0.18),
    "severe": dict(cast=1.2, vignette=0.46, noise=13.0, foxing=16, skew=1.8,
                   jpeg=32, blur=0.8, uneven=0.36, gutter=0.30),
}


def paper_texture(rng, h, w):
    """Low-frequency fibre/pulp variation plus fine grain."""
    coarse = rng.normal(0, 1, (max(2, h // 24), max(2, w // 24)))
    coarse = cv2.resize(coarse.astype(np.float32), (w, h),
                        interpolation=cv2.INTER_CUBIC)
    coarse /= max(1e-6, np.abs(coarse).max())
    fine = rng.normal(0, 1, (h, w)).astype(np.float32)
    fine = cv2.GaussianBlur(fine, (0, 0), 0.7)
    return coarse * 7.0 + fine * 1.6


def uneven_lighting(rng, h, w, strength):
    """Smooth low-frequency brightness field, as under a lamp or window."""
    if strength <= 0:
        return np.zeros((h, w), np.float32)
    field = rng.normal(0, 1, (6, 8)).astype(np.float32)
    field = cv2.resize(field, (w, h), interpolation=cv2.INTER_CUBIC)
    field /= max(1e-6, np.abs(field).max())
    return field * strength


def vignette(h, w, strength):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    r = np.sqrt(((yy - cy) / cy) ** 2 + ((xx - cx) / cx) ** 2)
    return 1.0 - strength * np.clip(r / 1.41, 0, 1) ** 2


def gutter_shadow(h, w, strength):
    """Dark band down one edge, as from a book binding or curled page."""
    if strength <= 0:
        return np.zeros((h, w), np.float32)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32)
    band = np.clip(1.0 - x / 0.30, 0.0, 1.0) ** 2
    return -(band[None, :] * strength)


def add_foxing(img, rng, count, radius_px):
    """Age spots / foxing and the occasional water ring."""
    h, w = img.shape[:2]
    for _ in range(count):
        cx, cy = rng.integers(0, w), rng.integers(0, h)
        rad = int(rng.integers(radius_px, radius_px * 3))
        tint = rng.uniform(0.55, 0.95)
        layer = np.zeros((h, w), np.float32)
        cv2.circle(layer, (int(cx), int(cy)), rad, 1.0, -1)
        layer = cv2.GaussianBlur(layer, (0, 0), rad * 0.45)
        mask = layer[:, :, None]
        darken = img.astype(np.float32) * (1.0 - 0.30 * mask)
        warm = np.stack([
            darken[:, :, 0] * (1 + 0.06 * layer),
            darken[:, :, 1] * (1 + 0.02 * layer),
            darken[:, :, 2] * (1 - 0.10 * layer),
        ], axis=2)
        img = np.clip(warm * (tint * 0.2 + 0.8), 0, 255).astype(np.uint8)
    return img


def simulate(src: Path, rng, severity: str) -> np.ndarray:
    """Turn a clean greyscale crop into a plausible photographed page."""
    cfg = SEVERITY[severity]
    gray = cv2.imread(str(src), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError(f"unreadable {src}")
    h, w = gray.shape

    # 1) ink on aged paper: map ink darkness onto a paper colour.
    paper_name = str(rng.choice(list(PAPER)))
    paper = np.array(PAPER[paper_name], np.float32)
    ink = (gray.astype(np.float32) / 255.0)[:, :, None]
    out = paper[None, None, :] * (0.30 + 0.70 * ink)

    # 2) paper texture
    tex = paper_texture(rng, h, w)[:, :, None]
    out += tex * 0.55

    # 3) colour cast (white balance)
    cast = np.array(CASTS[str(rng.choice(list(CASTS)))], np.float32)
    cast = 1.0 + (cast - 1.0) * cfg["cast"]
    out *= cast[None, None, :]

    # 4) stains (round-trips through uint8, so out is uint8 here)
    out = add_foxing(out, rng, cfg["foxing"], max(4, h // 26)).astype(np.float32)

    # 5) lighting: uneven field + vignette + gutter shadow
    field = uneven_lighting(rng, h, w, cfg["uneven"] * 255.0)
    field += (vignette(h, w, cfg["vignette"]) - 1.0) * 255.0
    field += gutter_shadow(h, w, cfg["gutter"]) * 255.0
    out = out * (1.0 + field / 255.0)[:, :, None]

    out = np.clip(out, 0, 255).astype(np.uint8)

    # 6) skew (page not square to the sensor)
    if cfg["skew"] > 0:
        angle = float(rng.uniform(-cfg["skew"], cfg["skew"]))
        rot = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        border = int(np.mean([paper[0], paper[1], paper[2]]))
        out = cv2.warpAffine(out, rot, (w, h), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT,
                             borderValue=(int(border), int(border), int(border)))

    # 7) defocus
    if cfg["blur"] > 0:
        out = cv2.GaussianBlur(out, (0, 0), float(rng.uniform(0.3, cfg["blur"])))

    # 8) sensor noise
    if cfg["noise"] > 0:
        out = np.clip(out.astype(np.float32)
                      + rng.normal(0, cfg["noise"], out.shape), 0, 255
                      ).astype(np.uint8)

    # 9) JPEG compression
    if cfg["jpeg"]:
        q = int(cfg["jpeg"] + rng.integers(-8, 9))
        q = int(np.clip(q, 8, 95))
        ok, enc = cv2.imencode(".jpg", out, [int(cv2.IMWRITE_JPEG_QUALITY), q])
        if ok:
            out = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--severity", choices=sorted(SEVERITY), default="medium")
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20260917)
    ap.add_argument("--out", default=f"data/raw/realistic_{'{severity}'}")
    args = ap.parse_args()

    out_dir = PROJECT_ROOT / args.out.format(severity=args.severity)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "MANIFEST.json"

    sources = sorted(SRC_DIR.glob("MT-*.png"))
    if not sources:
        raise SystemExit(f"no source pages in {SRC_DIR}; run fetch_modetrans.py")

    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    done = {m["id"] for m in manifest}

    made = 0
    for i, src in enumerate(sources):
        mid = src.stem
        if mid in done:
            continue
        # Stable per-sample seed: same page always yields the same capture.
        rng = np.random.default_rng(abs(hash((args.seed, mid))) % (2 ** 32))
        img = simulate(src, rng, args.severity)
        out_path = out_dir / f"{mid}_{args.severity}.png"
        cv2.imwrite(str(out_path), img)

        ref = EVAL_DIR / f"{mid}_ref.txt"
        manifest.append({
            "id": mid,
            "severity": args.severity,
            "out": out_path.name,
            "seed": int(abs(hash((args.seed, mid))) % (2 ** 32)),
            "has_ground_truth": ref.exists(),
            "ref_chars": len(ref.read_text(encoding="utf-8").strip())
            if ref.exists() else None,
        })
        made += 1
        print(f"{mid} -> {out_path.name}", flush=True)
        if made >= args.count:
            break

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nseverity={args.severity}  new={made}  total={len(manifest)}")
    print(f"out: {out_dir}")
    print("NOTE: authentic script + ground truth; capture is SIMULATED.")


if __name__ == "__main__":
    main()
