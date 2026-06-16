# SPDX-License-Identifier: MIT
"""Render the Verdict to a DRAFT report (JSON + Markdown). The report cannot express approval:
verdict is frozen to ADVISORY_ONLY and a deterministic GREEN explicitly does not mean compliant."""
import json
import os


def build(verdict):
    return {
        "tool": "alcoa-guard",
        "schema": "alcoa_guard@1",
        "mode": verdict.mode,
        "summary": {"hard": verdict.hard, "soft": verdict.soft,
                    "human_judgment_items": verdict.human_items},
        "verdict": "ADVISORY_ONLY",
        "human_owns_verdict": True,
        "findings": [vars(f) for f in verdict.findings],
        "human_judgment_checklist": list(verdict.checklist),
    }


def to_markdown(rep):
    s = rep["summary"]
    lines = [
        f"# ALCOA+ Data-Integrity Report (DRAFT — mode {rep['mode']})", "",
        f"**HARD: {s['hard']} · SOFT: {s['soft']} · human-judgment items: {s['human_judgment_items']}**",
        "",
        "_DRAFT. A deterministic GREEN does NOT mean fully compliant — see the human-judgment "
        "checklist. The human owns the verdict._", "",
    ]
    hard = [f for f in rep["findings"] if f["severity"] == "HARD"]
    soft = [f for f in rep["findings"] if f["severity"] == "SOFT"]
    for title, group in (("HARD findings", hard), ("SOFT findings", soft)):
        lines.append(f"## {title}")
        if not group:
            lines.append("- none")
        for f in group:
            lines.append(f"- [{f['principle']}] {f['location']}: {f['detail']}")
        lines.append("")
    lines.append("## Human-judgment checklist (not auto-verifiable — you must assess)")
    for item in rep["human_judgment_checklist"]:
        lines.append(f"- [ ] {item}")
    return "\n".join(lines) + "\n"


def write(rep, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    jpath = os.path.join(out_dir, "alcoa_guard.json")
    mpath = os.path.join(out_dir, "alcoa_guard.md")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    with open(mpath, "w", encoding="utf-8") as f:
        f.write(to_markdown(rep))
    return jpath, mpath
