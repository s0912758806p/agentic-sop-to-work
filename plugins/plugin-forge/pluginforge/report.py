# SPDX-License-Identifier: MIT
"""Render a LintReport to a DRAFT report (JSON + Markdown)."""
import json
import os


def build(rep):
    return {
        "tool": "plugin-forge",
        "schema": "plugin_forge_lint@1",
        "targets": rep.targets,
        "summary": {"hard": rep.hard, "soft": rep.soft},
        "clean": rep.clean,
        "findings": [vars(f) for f in rep.findings],
    }


def to_markdown(rep):
    s = rep["summary"]
    lines = [
        f"# plugin-forge lint (DRAFT) — targets: {', '.join(rep['targets']) or '(none)'}", "",
        f"**HARD: {s['hard']} · SOFT: {s['soft']} · {'CLEAN' if rep['clean'] else 'FAIL'}**", "",
    ]
    hard = [f for f in rep["findings"] if f["severity"] == "HARD"]
    soft = [f for f in rep["findings"] if f["severity"] == "SOFT"]
    for title, group in (("HARD", hard), ("SOFT / advisory", soft)):
        lines.append(f"## {title}")
        if not group:
            lines.append("- none")
        for f in group:
            lines.append(f"- [{f['plugin']}] [{f['rule']}] {f['location']}: {f['detail']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def write(rep, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    jpath = os.path.join(out_dir, "plugin_forge_lint.json")
    mpath = os.path.join(out_dir, "plugin_forge_lint.md")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    with open(mpath, "w", encoding="utf-8") as f:
        f.write(to_markdown(rep))
    return jpath, mpath
