"""CER/WER computation (Phase 8 module, standalone — no API/DB/model needed).

CER = (S + D + I) / N over characters (Levenshtein).
WER = (S + D + I) / N over whitespace-separated words.
"""

from __future__ import annotations


def _levenshtein(a: list, b: list) -> tuple[int, int, int]:
    """Return (substitutions, deletions, insertions) via edit-distance DP."""
    n, m = len(a), len(b)
    if n == 0:
        return 0, 0, m
    if m == 0:
        return 0, n, 0
    prev = list(range(m + 1))
    # backpointer-free formulation; recompute op counts via standard DP table
    table = [list(range(m + 1))]
    for i in range(1, n + 1):
        row = [i] + [0] * m
        ai = a[i - 1]
        for j in range(1, m + 1):
            cost = 0 if ai == b[j - 1] else 1
            row[j] = min(table[i - 1][j] + 1, row[j - 1] + 1,
                         table[i - 1][j - 1] + cost)
        table.append(row)
    # Backtrack to count op types.
    i, j = n, m
    s = d = ins = 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1]:
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and table[i][j] == table[i - 1][j - 1] + 1:
            s += 1
            i -= 1
            j -= 1
        elif i > 0 and table[i][j] == table[i - 1][j] + 1:
            d += 1
            i -= 1
        else:
            ins += 1
            j -= 1
    return s, d, ins


def cer(hypothesis: str, reference: str) -> float:
    """Character Error Rate."""
    s, d, ins = _levenshtein(list(hypothesis), list(reference))
    n = len(reference)
    return (s + d + ins) / n if n else float("inf")


def wer(hypothesis: str, reference: str) -> float:
    """Word Error Rate (whitespace tokenization)."""
    s, d, ins = _levenshtein(hypothesis.split(), reference.split())
    n = len(reference.split())
    return (s + d + ins) / n if n else float("inf")


def edit_breakdown(hypothesis: str, reference: str) -> dict:
    """Character-level (S, D, I, N) for analysis."""
    s, d, ins = _levenshtein(list(hypothesis), list(reference))
    return {"S": s, "D": d, "I": ins, "N": len(reference)}


# Never occurs in Devanagari or whitespace-collapsed output, so it is safe to
# align against.
PAGE_SEPARATOR = "⁣"


def split_hypothesis(hypothesis: str, ref_top: str, ref_bottom: str,
                     separator: str = PAGE_SEPARATOR) -> tuple[str, str]:
    """Split a hypothesis that covered two pages into its two halves.

    The model is asked to read only the top page and routinely reads both,
    emitting them in order. Where the boundary fell is recovered by aligning
    the hypothesis against the two references joined by a separator, and
    recording which hypothesis character the separator aligns to.

    Deterministic, and it uses both references, so it does not depend on a
    guessed offset. Returns the whole hypothesis as the top part if the
    separator is never reached (the model stopped early).
    """
    if len(separator) != 1:
        raise ValueError("separator must be a single character")
    a = list(hypothesis)
    b = list(ref_top) + [separator] + list(ref_bottom)
    n, m = len(a), len(b)

    table = [[0] * (m + 1) for _ in range(n + 1)]
    for j in range(m + 1):
        table[0][j] = j
    for i in range(1, n + 1):
        table[i][0] = i
        ai = a[i - 1]
        row, prev = table[i], table[i - 1]
        for j in range(1, m + 1):
            cost = 0 if ai == b[j - 1] else 1
            row[j] = min(prev[j] + 1, row[j - 1] + 1, prev[j - 1] + cost)

    # Backtrack with the same preference order as _levenshtein, noting which
    # hypothesis character the separator lands on.
    i, j, split_at = n, m, None
    while i > 0 or j > 0:
        if j > 0 and b[j - 1] == separator:
            split_at = i
            j -= 1
        elif i > 0 and j > 0 and a[i - 1] == b[j - 1]:
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and table[i][j] == table[i - 1][j - 1] + 1:
            i -= 1
            j -= 1
        elif i > 0 and table[i][j] == table[i - 1][j] + 1:
            i -= 1
        else:
            j -= 1

    if split_at is None:
        return hypothesis, ""
    return hypothesis[:split_at], hypothesis[split_at:]
