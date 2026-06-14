# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Assemble the Second Opinion report — a machine JSON + a human-readable markdown
DRAFT. The schema is built so it CANNOT express "Second Opinion approved this":
`verdict` is the frozen literal "ADVISORY_ONLY" and `human_owns_verdict` is always True.
"""
import os
from dataclasses import asdict

from . import core

BANNER = ("DRAFT — adversarial SECOND OPINION, advisory only; a human owns the final "
          "verdict. This report neither approves nor rejects, and is not a controlled record.")

LIMITATIONS = [
    "Second Opinion checks honesty (claims-vs-evidence), NOT code quality / bugs / security.",
    "DEGRADED mode: provenance is reconstructed from supplied inputs; a missing match may "
    "reflect incomplete inputs, not fabrication.",
]


def _mode_explainer(mode):
    if mode == "FULL":
        return ("FULL: the run's trace is authoritative -> deterministic findings are HARD at "
                "confidence 1.0.")
    return ("DEGRADED: provenance reconstructed from supplied inputs -> findings are SOFT at "
            "confidence 0.5; verify against the real sources.")


def _ordered(findings):
    # deterministic (HARD) first, then advisory; stable within by vector then id
    return sorted(findings, key=lambda f: (f.origin != "deterministic",
                                           f.severity != "HARD", f.vector, f.id))


def build(draft, findings, llm=None, dropped=None):
    by_vector = {}
    for f in findings:
        by_vector[f.vector] = by_vector.get(f.vector, 0) + 1
    summary = {
        "hard": sum(1 for f in findings if f.severity == "HARD"),
        "soft": sum(1 for f in findings if f.severity == "SOFT"),
        "by_vector": by_vector,
        "deterministic": sum(1 for f in findings if f.origin == "deterministic"),
        "advisory": sum(1 for f in findings if f.origin == "advisory"),
        "llm_dropped": len(dropped or []),
    }
    return {
        "schema": "second_opinion@1",
        "produced_by": "second-opinion",
        "review_of": {
            "mode": draft.mode,
            "run_id": draft.run_id,
            "flow": draft.produced_by,
            "draft_path": draft.draft_path,
            "input_sources": sorted({s.get("source") for s in draft.sources if s.get("source")}),
        },
        "verdict": "ADVISORY_ONLY",      # frozen — never "approved"
        "human_owns_verdict": True,      # constant
        "banner": BANNER,
        "summary": summary,
        "mode_explainer": _mode_explainer(draft.mode),
        "checks_run": ["arith_verdict", "fabrication", "missing_source"],
        "llm": llm or {"passes_used": 0, "max_passes": 0, "capped": False},
        "findings": [asdict(f) for f in _ordered(findings)],
        "llm_dropped": dropped or [],
        "limitations": LIMITATIONS,
    }


def _table(rows):
    out = ["| Vector | Conf | Location | Claim | Evidence |",
           "|---|---|---|---|---|"]
    for f in rows:
        ev = str(f.get("evidence", "")).replace("\n", " ").replace("|", "\\|")
        cl = str(f.get("claim", "")).replace("|", "\\|")
        out.append(f"| {f['vector']} | {f['mode_confidence']} | {f['location']} | {cl} | {ev} |")
    return "\n".join(out)


def to_markdown(rep):
    hard = [f for f in rep["findings"] if f["severity"] == "HARD"]
    soft = [f for f in rep["findings"] if f["severity"] == "SOFT"]
    ro = rep["review_of"]
    lines = [
        "# Second Opinion — DRAFT",
        "",
        f"> {rep['banner']}",
        "",
        "**✋ Human owns the verdict.** Second Opinion is advisory; it does not approve or reject.",
        "",
        "## Scope",
        f"- Target: `{ro.get('draft_path')}`  ·  Mode: **{ro['mode']}**"
        + (f"  ·  run: `{ro.get('run_id')}`" if ro.get("run_id") else ""),
        f"- Evidence basis: {', '.join(ro.get('input_sources') or ['(supplied inputs)'])}",
        f"- {rep['mode_explainer']}",
        "- Scope note: honesty (claims-vs-evidence) only — NOT source-code quality/bugs/security.",
        "",
        f"## Deterministic findings (code-owned) — {len(hard)}",
        (_table(hard) if hard else "_No hard honesty defects found by the deterministic layer._"),
        "",
        f"## Advisory findings (LLM — non-binding, capped) — {len(soft)}",
        (_table(soft) if soft else "_None._"),
    ]
    if rep.get("llm_dropped"):
        lines += ["", "## Dropped advisory accusations (failed the evidence gate)"]
        for d in rep["llm_dropped"]:
            lines.append(f"- {d.get('claim', '')} — {d.get('reason', '')}")
    lines += [
        "",
        "## Summary for the human",
        f"- HARD: {rep['summary']['hard']}  ·  SOFT: {rep['summary']['soft']}  "
        f"·  by vector: {rep['summary']['by_vector']}",
        "- This is a DRAFT review. You decide: approve · send back for fix · override a finding (with reason).",
        "",
        "## Limitations",
    ] + [f"- {x}" for x in rep["limitations"]]
    return "\n".join(lines) + "\n"


def write(rep, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    jpath = core.write_json(rep, os.path.join(out_dir, "second_opinion.json"))
    mpath = os.path.join(out_dir, "second_opinion.md")
    with open(mpath, "w", encoding="utf-8") as f:
        f.write(to_markdown(rep))
    return jpath, mpath
