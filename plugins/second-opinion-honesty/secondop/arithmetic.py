# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Deterministic re-derivation: recompute aggregates + re-evaluate spec verdicts.

Mirrors the kit recompute_gate discipline (count = exact int; sum/mean/min/max =
tolerant isclose). Pure functions; never raise on malformed input — they return a
(ok, derived/expected, reason) tuple so a check can turn the result into a Finding.
"""
import math

_TOL = dict(rel_tol=1e-9, abs_tol=1e-12)


def recompute(op, items, stated):
    """Re-derive `op` over `items` and compare to `stated`.

    Returns (ok: bool, derived, reason). count uses exact integer equality;
    sum/mean/min/max use a tolerant isclose to avoid float-representation false hits.
    """
    if not isinstance(items, list):
        return False, None, f"'over' is not a list: {type(items).__name__}"
    if op == "count":
        derived = len(items)
    else:
        try:
            nums = [float(x) for x in items]
        except (TypeError, ValueError) as e:
            return False, None, f"non-numeric item in list: {e}"
        if op == "sum":
            derived = sum(nums)
        elif op == "mean":
            derived = sum(nums) / len(nums) if nums else 0.0
        elif op == "min":
            derived = min(nums) if nums else None
        elif op == "max":
            derived = max(nums) if nums else None
        else:
            return False, None, f"unknown op {op!r}"
    snum = stated if isinstance(stated, (int, float)) and not isinstance(stated, bool) else None
    if snum is None:
        try:
            snum = float(str(stated).replace(",", ""))
        except (TypeError, ValueError):
            return False, derived, f"stated value not numeric: {stated!r}"
    if op == "count":
        ok = derived == snum
    else:
        ok = derived is not None and math.isclose(derived, snum, **_TOL)
    reason = "ok" if ok else f"recomputed {op}={derived} vs stated {stated}"
    return ok, derived, reason


def reeval_verdict(measured, lo, hi, stated_polarity):
    """Re-derive the in-spec polarity and compare to the stated one.

    Returns (ok: bool, expected_polarity, reason). `lo`/`hi` of None are unbounded.
    `stated_polarity` is expected to be normalized to "pass" / "fail" by the caller.
    """
    in_spec = (lo is None or measured >= lo) and (hi is None or measured <= hi)
    expected = "pass" if in_spec else "fail"
    ok = (stated_polarity == expected)
    reason = "ok" if ok else (
        f"measured {measured} vs limit [{lo}, {hi}] -> expected {expected}, stated {stated_polarity!r}"
    )
    return ok, expected, reason
