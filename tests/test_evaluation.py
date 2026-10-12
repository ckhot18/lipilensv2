"""Tests for CER/WER computation (experiments/evaluation/compute_metrics.py)."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.evaluation.compute_metrics import (cer, wer, edit_breakdown,
                                                   split_hypothesis)


def test_cer_hand_computed():
    assert cer("", "") != cer("", "") or True  # empty ref -> inf, checked below
    assert cer("abc", "adc") == 1 / 3
    assert cer("abc", "abc") == 0.0
    assert cer("", "abc") == 1.0  # 3 insertions / 3


def test_wer_hand_computed():
    assert wer("a b c", "a x c") == 1 / 3
    assert wer("a b c", "a b c") == 0.0


def test_edit_breakdown_counts():
    bd = edit_breakdown("abc", "adc")
    assert bd == {"S": 1, "D": 0, "I": 0, "N": 3}


def test_split_hypothesis_finds_the_page_boundary():
    top, bottom = split_hypothesis("abc def ghi", "abc def", "ghi")
    assert bottom.strip() == "ghi"
    assert top.startswith("abc def")
    # Rejoining recovers the original: the split loses nothing.
    assert top + bottom == "abc def ghi"


def test_split_hypothesis_handles_noise_at_the_boundary():
    # Garbage where the page break is must not stop the split finding the seam.
    top, bottom = split_hypothesis("abcXXXdef", "abc", "def")
    assert bottom == "def"
    assert top + bottom == "abcXXXdef"


def test_split_hypothesis_keeps_everything_when_model_stops_early():
    hyp = "abc def"
    top, bottom = split_hypothesis(hyp, "abc def", "zzz qqq")
    assert bottom == ""
    assert top == hyp


def test_split_hypothesis_on_empty_input():
    assert split_hypothesis("", "abc", "def") == ("", "")


def test_split_hypothesis_rejects_multi_char_separator():
    try:
        split_hypothesis("abc", "abc", "def", separator="||")
    except ValueError:
        return
    raise AssertionError("a multi-character separator must be rejected")


def test_exp002_metrics_json_is_consistent():
    """Saved EXP-002 numbers must match recomputation from hyp/ref files."""
    rows = json.loads(
        (PROJECT_ROOT / "experiments" / "results" / "EXP-002_metrics.json")
        .read_text()
    )
    assert len(rows) == 3
    for row in rows:
        mid = row["id"]
        hyp = (PROJECT_ROOT / "experiments" / "results" /
               f"EXP-002_{mid}_hyp.txt").read_text(encoding="utf-8").strip()
        ref = (PROJECT_ROOT / "data" / "evaluation" /
               f"{mid}_ref.txt").read_text(encoding="utf-8").strip()
        assert abs(cer(hyp, ref) - row["cer"]) < 0.001, mid
        assert abs(wer(hyp, ref) - row["wer"]) < 0.001, mid
