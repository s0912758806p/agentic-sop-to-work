# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Deterministic honesty checks — the HARD layer.

Disjoint scheme, one finding per unsourced slot:
  #1 check_arith_verdict   wrong PASS/FAIL vs spec limits + aggregate recompute mismatch
  #2 check_fabrication     unsourced NUMERIC values (with nearest-token transcription hint)
  #3 check_missing_source  unsourced NON-NUMERIC values (id/date/name/conclusion -> 【待補】)

FULL mode -> HARD @ confidence 1.0 (the kit trace is authoritative).
DEGRADED mode -> SOFT @ 0.5 (provenance is reconstructed, may be incomplete).
Vector #4 (conclusion overreach) is intentionally NOT here — it is judgment, so it
lives in the capped advisory LLM layer.
"""
from . import arithmetic, core
from .model import Finding

_PLACEHOLDER = "【待補】"


def _sev(draft):
    return ("HARD", 1.0) if draft.mode == "FULL" else ("SOFT", 0.5)


def _is_placeholder(claim):
    return claim.kind == "placeholder" or str(claim.value).strip() == _PLACEHOLDER


def check_arith_verdict(draft):
    """#1 — recompute aggregates and re-evaluate spec verdicts."""
    sev, conf = _sev(draft)
    out = []
    for agg in draft.aggregates:
        ok, derived, reason = arithmetic.recompute(agg.op, agg.over, agg.stated)
        if not ok:
            out.append(Finding(
                id=f"#1:{agg.id}", vector="#1", severity=sev, origin="deterministic",
                location=agg.stated_locator or agg.over_locator,
                claim=f"{agg.op} = {agg.stated}", evidence=reason,
                mode_confidence=conf, settled_key=f"slot:{agg.id}"))
    for v in draft.verdicts:
        if v.measured is None or (v.lo is None and v.hi is None):
            continue  # not deterministically re-evaluable -> left to advisory fuzzy #1
        ok, expected, reason = arithmetic.reeval_verdict(v.measured, v.lo, v.hi, v.polarity)
        if not ok:
            out.append(Finding(
                id=f"#1:{v.id}", vector="#1", severity=sev, origin="deterministic",
                location=v.locator, claim=f"verdict '{v.text}' for {v.label or v.id}",
                evidence=reason, mode_confidence=conf, settled_key=f"slot:{v.id}"))
    return out


def check_fabrication(draft):
    """#2 — numeric values with no matching source token."""
    sev, conf = _sev(draft)
    out = []
    for c in draft.claims:
        if c.sourced or _is_placeholder(c):
            continue
        if core.to_number(c.value) is None:
            continue  # non-numeric handled by #3
        near = core.nearest_token(c.value, draft.sources)
        hint = ""
        if near is not None:
            where = " ".join(x for x in [near.get("source"), near.get("locator")] if x)
            where = f" @ {where}" if where else ""
            hint = f"; nearest source token {near.get('value')}{where} (possible transcription error)"
        out.append(Finding(
            id=f"#2:{c.id}", vector="#2", severity=sev, origin="deterministic",
            location=c.location, claim=f"{c.label or 'value'} = {c.value}",
            evidence=f"value {c.value} has no matching token in declared sources{hint}",
            mode_confidence=conf, settled_key=f"slot:{c.id}"))
    return out


def check_missing_source(draft):
    """#3 — non-numeric values (identifier/date/name/conclusion) with no provenance."""
    sev, conf = _sev(draft)
    out = []
    for c in draft.claims:
        if c.sourced or _is_placeholder(c):
            continue
        if core.to_number(c.value) is not None:
            continue  # numeric handled by #2
        out.append(Finding(
            id=f"#3:{c.id}", vector="#3", severity=sev, origin="deterministic",
            location=c.location, claim=f"{c.label or 'field'} = {c.value}",
            evidence=(f"'{c.value}' has no provenance in declared sources; an invented "
                      f"identifier/date/name/conclusion should be 【待補】 or corrected"),
            mode_confidence=conf, settled_key=f"slot:{c.id}"))
    return out


REGISTRY = {
    "arith_verdict": check_arith_verdict,
    "fabrication": check_fabrication,
    "missing_source": check_missing_source,
}


def run_checks(draft, only=None):
    """Run all registered deterministic checks; stable dedupe by finding id."""
    seen = {}
    for name, fn in REGISTRY.items():
        if only and name not in only:
            continue
        for f in fn(draft):
            seen[f.id] = f
    return list(seen.values())
