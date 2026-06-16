# SPDX-License-Identifier: MIT
"""A — Accurate: values within declared limits; declared aggregates recompute correctly."""
from ..model import Finding
from .. import arithmetic


def check(record, contract, severity):
    findings = []
    for f, lim in contract.limits.items():
        v = record.fields.get(f)
        try:
            x = float(v)
        except (TypeError, ValueError):
            continue
        try:
            lo = float(lim["lo"]) if lim.get("lo") is not None else None
            hi = float(lim["hi"]) if lim.get("hi") is not None else None
        except (TypeError, ValueError):
            continue
        if (lo is not None and x < lo) or (hi is not None and x > hi):
            findings.append(Finding(
                id=f"accurate:spec:{f}", principle="accurate", severity=severity,
                origin="deterministic", location=f,
                detail=f"value {x} out of spec [{lo}, {hi}]"))
    for agg in contract.aggregates:
        op, over, stated = agg.get("op"), agg.get("over"), agg.get("stated")
        if not op or over is None or stated is None:
            continue
        items = record.fields.get(over)
        if not isinstance(items, list):
            continue
        ok, derived, reason = arithmetic.recompute(op, items, stated)
        if not ok:
            findings.append(Finding(
                id=f"accurate:agg:{op}:{over}", principle="accurate", severity=severity,
                origin="deterministic", location=over,
                detail=f"{op} over {over}: stated {stated}, recomputed {derived} ({reason})"))
    return findings
