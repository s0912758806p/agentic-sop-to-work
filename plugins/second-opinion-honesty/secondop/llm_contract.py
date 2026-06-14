# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""The capped advisory LLM layer's CODE side.

The LLM (driven by the /second-opinion command) does the adversarial reading; this
module owns the guarantees that keep it honest — and they live in code, not prose:
  • build_llm_envelope  — hands the model the draft + sources + what's already settled
  • merge_llm_findings  — clamp every finding to SOFT/advisory/conf≤0.5, drop accusations
                          that cite nothing (evidence gate), drop re-litigation of settled slots
  • max_passes / counter — code-enforced cap on advisory passes (mirrors SOPKIT_MAX_FIX_RETRIES)
"""
import os
import re

from .model import Finding

MAX_PASSES_ENV = "SECONDOP_MAX_LLM_PASSES"
DEFAULT_MAX_PASSES = 1
HARD_CEILING = 3
_QUOTED = re.compile(r"""["']([^"']{4,})["']""")


def max_passes():
    try:
        v = int(os.environ.get(MAX_PASSES_ENV, str(DEFAULT_MAX_PASSES)))
    except ValueError:
        v = DEFAULT_MAX_PASSES
    return max(0, min(v, HARD_CEILING))


def _passes_file(out_dir):
    return os.path.join(out_dir, ".llm_passes")


def passes_used(out_dir):
    p = _passes_file(out_dir)
    if not os.path.exists(p):
        return 0
    try:
        return int(open(p, encoding="utf-8").read().strip() or "0")
    except ValueError:
        return 0


def bump_passes(out_dir):
    n = passes_used(out_dir) + 1
    os.makedirs(out_dir, exist_ok=True)
    with open(_passes_file(out_dir), "w", encoding="utf-8") as f:
        f.write(str(n))
    return n


def build_llm_envelope(draft, det_findings, attempt=1):
    """The JSON envelope handed to the LLM red-team."""
    settled = [{"settled_key": f.settled_key, "vector": f.vector, "claim": f.claim,
                "evidence": f.evidence} for f in det_findings if f.settled_key]
    return {
        "mode": draft.mode,
        "draft_text": draft.raw_text,
        "declared_sources": [{"value": s.get("value"), "source": s.get("source"),
                              "locator": s.get("locator")} for s in draft.sources],
        "claims": [{"id": c.id, "location": c.location, "label": c.label,
                    "value": str(c.value), "kind": c.kind, "sourced": c.sourced}
                   for c in draft.claims],
        "already_settled": settled,
        "focus": ["#4", "#1-fuzzy"],
        "attempt": attempt,
        "max_attempts": max_passes(),
        "rules": [
            "Findings are ADVISORY only; a human owns the verdict.",
            "Every finding MUST cite evidence: quote a verbatim span from draft_text AND "
            "a declared_source token, or state 'NO SOURCE' for a missing/unsupported value.",
            "Do NOT invent input values. If you cannot cite a draft span or a declared "
            "source, you may not raise the finding.",
            "Do NOT re-flag anything whose slot/settled_key is in already_settled.",
            "Prefer #4 (conclusion overreach) and fuzzy #1 (verdicts/limits the "
            "deterministic layer could not parse).",
        ],
    }


def _cites(claim, evidence, draft_text):
    """The evidence gate: an accusation must point at something real in the draft."""
    if "NO SOURCE" in evidence.upper():
        return True
    if claim and len(claim) >= 4 and claim in draft_text:
        return True
    for q in _QUOTED.findall(evidence):
        if q in draft_text:
            return True
    return False


def merge_llm_findings(llm_findings, draft_text, settled_keys):
    """Clamp + evidence-gate + settled-suppress. Returns (kept_findings, dropped)."""
    kept, dropped = [], []
    settled = set(settled_keys or [])
    for raw in llm_findings or []:
        vector = raw.get("vector", "#4")
        location = raw.get("location", "") or ""
        claim = str(raw.get("claim", ""))
        evidence = str(raw.get("evidence", ""))
        key = f"slot:{location}" if location else ""
        if key and key in settled:
            dropped.append({"claim": claim,
                            "reason": "re-flags a slot already settled deterministically"})
            continue
        if not _cites(claim, evidence, draft_text):
            dropped.append({"claim": claim,
                            "reason": "no verbatim draft span or declared-source citation (evidence gate)"})
            continue
        try:
            conf = min(float(raw.get("confidence", 0.5)), 0.5)
        except (TypeError, ValueError):
            conf = 0.5
        kept.append(Finding(
            id=f"{vector}:llm:{len(kept)}", vector=vector, severity="SOFT", origin="advisory",
            location=location or "(draft)", claim=claim, evidence=evidence,
            mode_confidence=conf, settled_key=key, suggested_fix=raw.get("suggested_fix")))
    return kept, dropped
