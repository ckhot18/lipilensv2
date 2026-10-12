"""Build the context probe: does neighbouring page content help at all?

The token sweep (PIXELS) showed visual tokens saturate at native resolution, so
adding tokens cannot be the lever. The open question the paper leaves is *which
context* those tokens should cover. This builds the two arms that answer it.

Both arms give page P its **full native resolution**. Nothing is downscaled, so
there is no resolution confound:

  CTX_SINGLE   P alone                       1268 x 463
  CTX_PAIR     P stacked above its neighbour 1268 x 966

The only difference between the arms is whether the neighbouring page is
present. A paired CER comparison is therefore attributable to context and
nothing else.

The probe deliberately does NOT halve the resolution the way a side-by-side
composite would. That version was rejected: at half width the text stops being
readable at all, so both arms would score near-CER 1.0 and the comparison would
be uninformative. Stacking keeps every page legible.

Usage:
    python scripts/make_context_probe.py --out data/raw/ctx_pair --mode pair
    python scripts/make_context_probe.py --out data/raw/ctx_single --mode single
"""

import argparse
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image

SRC = PROJECT_ROOT / "data" / "raw" / "mode_trans"

# A white gutter, wide enough to be unambiguous about where one page ends.
GUTTER = 40


def page_ids(n: int) -> list[str]:
    """MT-001..MT-0NN, in order."""
    return [f"MT-{i:03d}" for i in range(1, n + 1)]


def compose_pair(top_id: str, next_id: str) -> Image.Image:
    top = Image.open(SRC / f"{top_id}.png").convert("RGB")
    nxt = Image.open(SRC / f"{next_id}.png").convert("RGB")
    if top.size != nxt.size:
        raise ValueError(f"size mismatch: {top_id} {top.size} vs {next_id} {nxt.size}")

    w, h = top.size
    canvas = Image.new("RGB", (w, h * 2 + GUTTER), "white")
    canvas.paste(top, (0, 0))
    canvas.paste(nxt, (0, h + GUTTER))
    return canvas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=["pair", "single"], required=True)
    ap.add_argument("--pages", type=int, default=20)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    if not out.is_absolute():
        out = PROJECT_ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    ids = page_ids(args.pages + 1)
    for top_id in ids[:-1]:
        if args.mode == "pair":
            img = compose_pair(top_id, ids[ids.index(top_id) + 1])
        else:
            img = Image.open(SRC / f"{top_id}.png").convert("RGB")
        # Named after the TOP page, because that is the page whose reference
        # the transcription is scored against.
        img.save(out / f"{top_id}.png")

    print(f"wrote {len(ids) - 1} {args.mode} images to {out}")
    first = compose_pair(ids[0], ids[1])
    print(f"  page alone : {Image.open(SRC / f'{ids[0]}.png').size}")
    print(f"  composite  : {first.size}  ({first.size[0] * first.size[1]:,} px)")


if __name__ == "__main__":
    main()