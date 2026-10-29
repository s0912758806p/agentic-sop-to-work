# SPDX-License-Identifier: MIT
"""Tier-0 frontmatter checks: SKILL.md + agents/*.md need name + description (HARD); command
.md should have a description (SOFT). Strict adds SOFT `commands-dir`: a plugin should ship
skills/<name>/SKILL.md, not commands/ (a skill of the same name keeps the same invocation)."""
import glob
import os
import re
from ..model import Finding

_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def _frontmatter(path):
    with open(path, encoding="utf-8") as f:
        m = _FM.match(f.read())
    return m.group(1) if m else None


def check(plugin_dir, strict):
    name = os.path.basename(os.path.normpath(plugin_dir))
    findings = []
    for sk in sorted(glob.glob(os.path.join(plugin_dir, "skills", "*", "SKILL.md"))):
        rel = os.path.relpath(sk, plugin_dir)
        fm = _frontmatter(sk)
        if fm is None:
            findings.append(Finding(f"frontmatter:skill:{rel}", "frontmatter", "HARD", name, rel,
                                    "SKILL.md missing YAML frontmatter"))
        elif "name:" not in fm or "description:" not in fm:
            findings.append(Finding(f"frontmatter:skill:{rel}", "frontmatter", "HARD", name, rel,
                                    "SKILL.md frontmatter needs name + description"))
    for ag in sorted(glob.glob(os.path.join(plugin_dir, "agents", "*.md"))):
        rel = os.path.relpath(ag, plugin_dir)
        fm = _frontmatter(ag)
        if fm is None or "name:" not in fm or "description:" not in fm:
            findings.append(Finding(f"frontmatter:agent:{rel}", "frontmatter", "HARD", name, rel,
                                    "agent .md needs YAML frontmatter with name + description"))
    cmds = sorted(glob.glob(os.path.join(plugin_dir, "commands", "*.md")))
    if strict and cmds:
        findings.append(Finding("frontmatter:commands-dir", "frontmatter", "SOFT", name, "commands/",
                                "ships commands/ — migrate each to skills/<name>/SKILL.md "
                                "(same invocation, plus auto-trigger)"))
    for cmd in cmds:
        rel = os.path.relpath(cmd, plugin_dir)
        fm = _frontmatter(cmd)
        if fm is None or "description:" not in fm:
            findings.append(Finding(f"frontmatter:cmd:{rel}", "frontmatter", "SOFT", name, rel,
                                    "command .md should have frontmatter with a description"))
    return findings
