# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Contract reader -> one NormalizedDraft for both modes.

FULL mode (read_full): point at an agentic-sop-kit run_dir. Pools the trace across all
JSON step artifacts (the verbatim allow-set), then harvests from the artifact that
feeds the final report (NOT by parsing the markdown — the report's numbers are rendered
from that JSON, so harvesting there keeps the authoritative trace link).

Recognized, DOMAIN-NEUTRAL convention inside `data`:
  • data.results[]    -> Verdicts (#1) + each record's `value` as a claim (#2/#3)
  • data.aggregates[] -> Aggregates (#1, recompute)
  • every other scalar -> a claim; long/prose strings are skipped (that's the #4 LLM layer)
"""
import json
import os

from . import core, extract
from .model import Aggregate, Claim, NormalizedDraft, Verdict

_PASS_WORDS = {"pass", "passed", "符合", "conform", "conforms", "within", "ok", "合格", "in spec"}
_FAIL_WORDS = {"fail", "failed", "不符合", "oos", "outside", "ng", "不合格", "out of spec"}


def _polarity(word):
    w = str(word).strip().lower()
    if w in _PASS_WORDS:
        return "pass"
    if w in _FAIL_WORDS:
        return "fail"
    return "unknown"


def _lim(record, *keys):
    for k in keys:
        if record.get(k) is not None:
            return core.to_number(record.get(k))
    return None


def _scalar_claim(idp, label, value, sources):
    """A single scalar -> a Claim, or None if it shouldn't be checked (prose/verdict words)."""
    if isinstance(value, bool) or value is None:
        return None
    num = core.to_number(value)
    if num is not None:
        return Claim(id=idp, value=value, label=label, location=idp, kind="number",
                     sourced=core.is_sourced(value, sources))
    s = str(value).strip()
    if s == "【待補】":
        return Claim(id=idp, value=s, label=label, location=idp, kind="placeholder", sourced=None)
    # identifier heuristic: short, single token, contains a digit (lot/batch/date/code).
    # Prose (conclusions, names with spaces) is left for the advisory #4 layer.
    if len(s) <= 30 and (" " not in s) and any(ch.isdigit() for ch in s):
        return Claim(id=idp, value=s, label=label, location=idp, kind="identifier",
                     sourced=core.is_sourced(s, sources))
    return None


def _walk(idp, label, value, sources, claims):
    if isinstance(value, dict):
        for k, v in value.items():
            _walk(f"{idp}.{k}", k, v, sources, claims)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _walk(f"{idp}[{i}]", label, v, sources, claims)
    else:
        c = _scalar_claim(idp, label, value, sources)
        if c is not None:
            claims.append(c)


def _harvest(data, sources, produced_by):
    claims, aggregates, verdicts = [], [], []
    if not isinstance(data, dict):
        return claims, aggregates, verdicts
    pb = produced_by or "draft"

    for i, agg in enumerate(data.get("aggregates", []) or []):
        aggregates.append(Aggregate(
            id=f"{pb}.aggregates[{i}]", op=agg.get("op"),
            over=agg.get("over", []) or [], stated=agg.get("stated"),
            stated_locator=agg.get("label") or f"aggregates[{i}]"))

    for i, r in enumerate(data.get("results", []) or []):
        if not isinstance(r, dict):
            continue
        label = r.get("test") or r.get("name") or r.get("label") or f"results[{i}]"
        val = r.get("value")
        if "verdict" in r or "result" in r:
            word = r.get("verdict") if r.get("verdict") is not None else r.get("result")
            verdicts.append(Verdict(
                id=f"{pb}.results[{i}]", text=str(word), polarity=_polarity(word),
                measured=core.to_number(val),
                lo=_lim(r, "limit_lo", "lo", "nlt", "min"),
                hi=_lim(r, "limit_hi", "hi", "nmt", "max"),
                locator=f"results[{i}]:{label}", label=label))
        if val is not None:
            claims.append(Claim(
                id=f"{pb}.results[{i}].value", value=val, label=label,
                location=f"results[{i}]:{label}",
                kind="number" if core.to_number(val) is not None else "value",
                sourced=core.is_sourced(val, sources)))

    for k, v in data.items():
        if k in ("results", "aggregates"):
            continue
        _walk(f"{pb}.{k}", k, v, sources, claims)

    return claims, aggregates, verdicts


def _resolve(run_dir, p):
    """Resolve an artifact path. The kit writes ABSOLUTE paths, but a shipped or
    relocated run_dir needs them resolved by basename relative to run_dir."""
    if not p:
        return p
    if os.path.isabs(p) and os.path.exists(p):
        return p
    cand = os.path.join(run_dir, os.path.basename(p))
    return cand if os.path.exists(cand) else p


def read_full(run_dir):
    manifest = core.read_json(os.path.join(run_dir, "run_manifest.json"))
    steps = manifest.get("steps", []) or []
    final_output = _resolve(run_dir, manifest.get("final_output"))

    sources, seen, feeding = [], set(), None
    for st in steps:
        out = _resolve(run_dir, st.get("out"))
        if not out or not str(out).endswith(".json") or not os.path.exists(out):
            continue
        art = core.read_json(out)
        for t in art.get("trace", []) or []:
            key = (str(t.get("value")), t.get("source"), t.get("locator"))
            if key not in seen:
                seen.add(key)
                sources.append(t)
        feeding = art  # last JSON artifact feeds the report

    raw_text = ""
    if final_output and os.path.exists(final_output):
        if str(final_output).endswith(".json"):
            feeding = core.read_json(final_output)
            raw_text = json.dumps(feeding.get("data", {}), ensure_ascii=False, indent=2)
        else:
            with open(final_output, encoding="utf-8") as f:
                raw_text = f.read()

    data = (feeding or {}).get("data", {})
    produced_by = (feeding or {}).get("produced_by")
    claims, aggregates, verdicts = _harvest(data, sources, produced_by)

    return NormalizedDraft(
        mode="FULL", sources=sources, claims=claims, aggregates=aggregates,
        verdicts=verdicts, raw_text=raw_text, run_id=manifest.get("run_id"),
        produced_by=produced_by, draft_path=final_output,
        notes=[f"FULL mode: pooled {len(sources)} trace tokens from {manifest.get('flow')}"])


def read_degraded(doc_path, inputs_paths):
    """DEGRADED mode: a plain document + user-supplied input files. No kit trace, so
    provenance is reconstructed best-effort by extract.py and checks come out SOFT.
    Verdicts/aggregates (#1) are not reliably parseable from prose -> left to the LLM."""
    with open(doc_path, encoding="utf-8") as f:
        raw_text = f.read()
    sources = extract.extract_sources(inputs_paths)
    claims = extract.extract_claims(raw_text, sources)
    return NormalizedDraft(
        mode="DEGRADED", sources=sources, claims=claims, aggregates=[], verdicts=[],
        raw_text=raw_text, draft_path=doc_path,
        notes=[f"DEGRADED mode: reconstructed {len(sources)} source tokens from "
               f"{len(inputs_paths or [])} input file(s); #1/#4 left to the advisory layer"])
