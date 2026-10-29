# SPDX-License-Identifier: MIT
"""Render a LintReport to a DRAFT report (JSON + Markdown). Unlike the advisory reviewers,
lint IS a gate (exit 1 on HARD), so it uses the shared dual write without the
ADVISORY_ONLY frame."""
import dataclasses
from ._core import report as core_report


def build(rep):
    return {
        "tool": "plugin-forge",
        "schema": "plugin_forge_lint@1",
        "targets": rep.targets,
        "summary": {"hard": rep.hard, "soft": rep.soft},
        "clean": rep.clean,
        "findings": [dataclasses.asdict(f) for f in rep.findings],
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
    return core_report.write_dual(rep, out_dir, "plugin_forge_lint", to_markdown, advisory=False)
