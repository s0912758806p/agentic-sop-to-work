# GENERATED from shared/sopcore/arithmetic.py by tools/sync_core.py — do not edit this copy; edit the source and re-run `python3 tools/sync_core.py`.
# sopcore-sha256: cc4881da95363546c0caf89095b0919e63e26850d736f172747bf1adead3d5ca
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Deterministic re-derivation: recompute an aggregate, re-evaluate a spec verdict.

One semantics for every companion (mirrors the kit's recompute_gate discipline):
  • count is exact (3 == 3.0; 3.7 is NOT 3); sum/mean/min/max use a tolerant isclose
  • sum and mean use math.fsum (no float-accumulation false mismatches)
  • an EMPTY list fails sum/mean/min/max — there is nothing to recompute, so a stated value
    cannot be confirmed (an empty count is simply 0)
  • a mismatch reason always reads "recomputed <op>=<derived> vs stated <stated>"
Pure functions; never raise on malformed input — they return (ok, derived, reason).
"""
import math

_TOL = dict(rel_tol=1e-9, abs_tol=1e-12)
OPS = ("count", "sum", "mean", "min", "max")


def _num(x):
    if isinstance(x, bool):
        raise ValueError(f"boolean is not a number: {x!r}")
    if isinstance(x, (int, float)):
        return float(x)
    return float(str(x).replace(",", ""))


def recompute(op, items, stated):
    """Re-derive `op` over `items` and compare to `stated`. Returns (ok, derived, reason)."""
    if op not in OPS:
        return False, None, f"unknown op {op!r}"
    if not isinstance(items, list):
        return False, None, f"'over' is not a list: {type(items).__name__}"
    if op == "count":
        derived = len(items)
    else:
        try:
            nums = [_num(x) for x in items]
        except (TypeError, ValueError) as e:
            return False, None, f"non-numeric item in list: {e}"
        if not nums:
            return False, None, f"no items to recompute {op} over"
        if op == "sum":
            derived = math.fsum(nums)
        elif op == "mean":
            derived = math.fsum(nums) / len(nums)
        elif op == "min":
            derived = min(nums)
        else:
            derived = max(nums)
    try:
        snum = _num(stated)
    except (TypeError, ValueError):
        return False, derived, f"stated value not numeric: {stated!r}"
    ok = (derived == snum) if op == "count" else math.isclose(derived, snum, **_TOL)
    return ok, derived, ("ok" if ok else f"recomputed {op}={derived} vs stated {stated}")


def reeval_verdict(measured, lo, hi, stated_polarity):
    """Re-derive in-spec polarity and compare to the stated one ("pass"/"fail").
    Returns (ok, expected_polarity, reason). `lo`/`hi` of None are unbounded."""
    in_spec = (lo is None or measured >= lo) and (hi is None or measured <= hi)
    expected = "pass" if in_spec else "fail"
    ok = stated_polarity == expected
    reason = "ok" if ok else (
        f"measured {measured} vs limit [{lo}, {hi}] -> expected {expected}, stated {stated_polarity!r}")
    return ok, expected, reason
