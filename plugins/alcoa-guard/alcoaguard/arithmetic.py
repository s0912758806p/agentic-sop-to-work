# SPDX-License-Identifier: MIT
"""Self-contained deterministic recompute kernel (stdlib only). Never raises."""
import math


def recompute(op, items, stated):
    """Recompute an aggregate over `items` and compare to `stated`.
    Returns (ok: bool, derived, reason: str). count uses exact equality;
    sum/mean/min/max use math.isclose."""
    if op == "count":
        derived = len(items)
        return (derived == stated, derived, "count")
    nums = []
    for x in items:
        try:
            nums.append(float(x))
        except (TypeError, ValueError):
            return (False, None, f"non-numeric item: {x!r}")
    if not nums:
        return (False, None, "no items")
    if op == "sum":
        derived = math.fsum(nums)
    elif op == "mean":
        derived = math.fsum(nums) / len(nums)
    elif op == "min":
        derived = min(nums)
    elif op == "max":
        derived = max(nums)
    else:
        return (False, None, f"unknown op: {op}")
    try:
        ok = math.isclose(derived, float(stated), rel_tol=1e-9, abs_tol=1e-12)
    except (TypeError, ValueError):
        ok = False
    return (ok, derived, op)
