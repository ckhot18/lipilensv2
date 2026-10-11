#!/usr/bin/env python
"""Re-score every historical hypothesis under one scorer.

EXP-001..EXP-007 wrote ~190 hypothesis files across different protocols,
different scorers and different days. They are the largest evidence base this
project owns and almost none of them have been compared on equal terms.

This script reads every `*_hyp.txt` in experiments/results, pairs it with the
expert reference in data/evaluation, and scores it with the single
experiments.evaluation.compute_metrics module. No GPU, no model, no network.

Output: research/paper/data/consolidated.csv + a summary per experiment tag.
"""

from __future__ import annotations

import collections
import csv
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from experiments.evaluation.compute_metrics import cer, edit_breakdown, wer

RESULTS = ROOT / "experiments" / "results"
REFS = ROOT / "data" / "evaluation"
OUT = pathlib.Path(__file__).resolve().parent / "data"

# EXP-005_{config}_{mid}_hyp.txt  and  EXP-00N_{mid}_hyp.txt
PATTERNS = [
    re.compile(r"^(EXP-\d+)_(?P<config>[a-z_]+?)_(?P<mid>MT-\d+)_hyp\.txt$"),
    re.compile(r"^(EXP-\d+)_(?P<mid>MT-\d+)_hyp\.txt$"),
]


def parse(name: str):
    for pat in PATTERNS:
        m = pat.match(name)
        if m:
            g = m.groupdict()
            return m.group(1), g.get("mid"), g.get("config") or "baseline"
    return None


def normalise(text: str) -> str:
    return " ".join((text or "").split())


def main() -> None:
    if not RESULTS.is_dir():
        raise SystemExit(f"results directory not found: {RESULTS}")
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    skipped_no_ref = []
    skipped_empty = 0

    for hyp_path in sorted(RESULTS.rglob("*_hyp.txt")):
        parsed = parse(hyp_path.name)
        if not parsed:
            continue
        tag, mid, config = parsed
        ref_path = REFS / f"{mid}_ref.txt"
        if not ref_path.exists():
            skipped_no_ref.append(hyp_path.name)
            continue
        hyp = normalise(hyp_path.read_text(encoding="utf-8"))
        if not hyp:
            skipped_empty += 1
            continue
        ref = normalise(ref_path.read_text(encoding="utf-8"))
        eb = edit_breakdown(hyp, ref)
        rows.append({
            "tag": tag, "mid": mid, "config": config,
            "cer": round(cer(hyp, ref), 4),
            "wer": round(wer(hyp, ref), 4),
            "hyp_chars": len(hyp), "ref_chars": len(ref),
            "S": eb["S"], "D": eb["D"], "I": eb["I"], "N": eb["N"],
            "file": hyp_path.relative_to(RESULTS).as_posix(),
        })

    if not rows:
        print("nothing scored")
        return

    fields = list(rows[0])
    with (OUT / "consolidated.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"scored {len(rows)} historical hypotheses")
    print(f"  skipped (no reference on file): {len(skipped_no_ref)}")
    print(f"  skipped (empty hypothesis)    : {skipped_empty}")

    by_tag = collections.defaultdict(list)
    by_cfg = collections.defaultdict(list)
    by_mid = collections.defaultdict(list)
    for r in rows:
        by_tag[r["tag"]].append(r["cer"])
        by_cfg[(r["tag"], r["config"])].append(r["cer"])
        by_mid[r["mid"]].append(r["cer"])

    print("\n--- mean CER per experiment tag ---")
    for tag in sorted(by_tag):
        v = by_tag[tag]
        print(f"  {tag}  n={len(v):>3}  mean={statistics.mean(v):.3f}  "
              f"median={statistics.median(v):.3f}  "
              f"accuracy={100*(1-statistics.mean(v)):.1f}%")

    print("\n--- mean CER per (tag, config) ---")
    for (tag, cfg) in sorted(by_cfg):
        v = by_cfg[(tag, cfg)]
        print(f"  {tag:<9} {cfg:<18} n={len(v):>3}  mean={statistics.mean(v):.3f}")

    # How many DISTINCT pages have any historical measurement?
    print(f"\ndistinct pages ever transcribed: {len(by_mid)}")
    print(f"wrote {OUT / 'consolidated.csv'}")


if __name__ == "__main__":
    main()