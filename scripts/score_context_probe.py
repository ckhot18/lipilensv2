"""Score the context probe: does neighbouring page content help?

The token sweep (PIXELS) established that visual tokens saturate at native
resolution, so "more tokens" is not available as a lever. This probe asks the
open question instead: does *more page context* help?

Two arms, identical prompt, identical pixel ceiling, and page P at its **full
native resolution in both**:

  CTXSINGLE   P alone
  CTXPAIR     P stacked above P+1

So the pair arm has strictly more information and strictly no less resolution.
Any paired CER difference is attributable to context.

The model does not reliably obey "only the top page" — it reads both and emits
them in order — so the pair hypothesis is split at the page boundary using
`compute_metrics.split_hypothesis`, which aligns against both references.

Writes eval_CTX_metrics.csv with one row per page and arm.

    python scripts/score_context_probe.py
"""

import csv
import pathlib
import statistics
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.evaluation.compute_metrics import cer, split_hypothesis

EVAL = PROJECT_ROOT / "experiments" / "results" / "eval"
REF = PROJECT_ROOT / "data" / "evaluation"

FIELDS = ["arm", "page", "cer", "ref_chars", "hyp_chars",
          "cer_bottom", "ref_chars_bottom", "hyp_chars_bottom"]


def norm(t: str) -> str:
    return " ".join((t or "").split())


def next_page(page: str) -> str:
    return f"MT-{int(page.split('-')[1]) + 1:03d}"


def load_arm(tag: str, pages: list[str]) -> dict[str, str]:
    out = {}
    for page in pages:
        p = EVAL / f"{tag}_noseg_{page}_hyp.txt"
        if p.exists():
            out[page] = norm(p.read_text(encoding="utf-8"))
    return out


def main() -> None:
    pages = [f"MT-{i:03d}" for i in range(1, 21)]

    single = load_arm("CTXSINGLE", pages)
    pair = load_arm("CTXPAIR", pages)
    print(f"hypotheses: single={len(single)}  pair={len(pair)}")

    rows: list[dict] = []

    for page in pages:
        ref = norm((REF / f"{page}_ref.txt").read_text(encoding="utf-8"))
        nxt = next_page(page)

        if page in single:
            h = single[page]
            rows.append({"arm": "single", "page": page,
                         "cer": round(cer(h, ref), 4),
                         "ref_chars": len(ref), "hyp_chars": len(h),
                         "cer_bottom": "", "ref_chars_bottom": "",
                         "hyp_chars_bottom": ""})

        if page in pair and (REF / f"{nxt}_ref.txt").exists():
            ref_b = norm((REF / f"{nxt}_ref.txt").read_text(encoding="utf-8"))
            top, bottom = split_hypothesis(pair[page], ref, ref_b)
            rows.append({"arm": "pair_top", "page": page,
                         "cer": round(cer(top, ref), 4),
                         "ref_chars": len(ref), "hyp_chars": len(top),
                         "cer_bottom": round(cer(bottom, ref_b), 4) if bottom else "",
                         "ref_chars_bottom": len(ref_b) if bottom else "",
                         "hyp_chars_bottom": len(bottom)})

    out = EVAL / "eval_CTX_metrics.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}")

    by = {}
    for r in rows:
        by.setdefault(r["arm"], {})[r["page"]] = r

    def mean(arm):
        v = [float(r["cer"]) for r in rows if r["arm"] == arm]
        return statistics.mean(v) if v else float("nan")

    def acc(arm):
        c = [float(r["cer"]) for r in rows if r["arm"] == arm]
        return (1 - statistics.mean(c)) * 100 if c else float("nan")

    print(f"\n{'arm':<10}{'n':>4}{'meanCER':>10}{'accuracy':>10}")
    for arm in ("single", "pair_top"):
        n = len(by.get(arm, {}))
        print(f"{arm:<10}{n:>4}{mean(arm):>10.3f}{acc(arm):>9.1f}%")

    bot = [float(r["cer_bottom"]) for r in rows
           if r["arm"] == "pair_top" and r["cer_bottom"] != ""]
    if bot:
        print(f"\nthe second page, read for free alongside the first: "
              f"n={len(bot)} meanCER={statistics.mean(bot):.3f}")

    # paired comparison of the top page, with vs without its neighbour present
    common = sorted(set(by.get("single", {})) & set(by.get("pair_top", {})))
    if common:
        d = [float(by["pair_top"][p]["cer"]) - float(by["single"][p]["cer"])
             for p in common]
        worse = sum(1 for x in d if x > 1e-9)
        better = sum(1 for x in d if x < -1e-9)
        print(f"\npaired, same page, with vs without its neighbour: n={len(d)} "
              f"mean delta={statistics.mean(d):+.4f}  "
              f"worse={worse} better={better} tie={len(d) - worse - better}")

    # The other half of the question: the page the model read *second*. Every
    # page except the last exists both as a solo target and as a stacked second
    # page, so the cost of being second can be paired too.
    solo = {r["page"]: float(r["cer"]) for r in rows if r["arm"] == "single"}
    as_second = {}
    for r in rows:
        if r["arm"] == "pair_top" and r["cer_bottom"] not in ("", None):
            as_second[next_page(r["page"])] = float(r["cer_bottom"])
    both = sorted(set(solo) & set(as_second))
    if both:
        d = [as_second[p] - solo[p] for p in both]
        worse = sum(1 for x in d if x > 1e-9)
        better = sum(1 for x in d if x < -1e-9)
        print(f"\nthe same page, read alone vs read second in a stack: "
              f"n={len(d)}")
        print(f"  read alone   {statistics.mean(solo[p] for p in both):.3f}")
        print(f"  read second  {statistics.mean(as_second[p] for p in both):.3f}")
        print(f"  paired delta {statistics.mean(d):+.4f}  "
              f"worse={worse} better={better} tie={len(d) - worse - better}")


if __name__ == "__main__":
    main()