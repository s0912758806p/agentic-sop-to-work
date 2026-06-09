#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""CI guard: validate marketplace.json + each plugin.json + every plugin-level SKILL.md frontmatter.

Run from the repo root. Exit 1 (with a list of problems) on any failure; exit 0 when clean.
"""
import json
import pathlib
import re
import sys

errs = []

mp_path = pathlib.Path(".claude-plugin/marketplace.json")
if not mp_path.exists():
    print("❌ missing .claude-plugin/marketplace.json")
    sys.exit(1)
mp = json.loads(mp_path.read_text(encoding="utf-8"))
if not mp.get("name") or not mp.get("plugins"):
    errs.append("marketplace.json missing name/plugins")

for p in mp.get("plugins", []):
    if not p.get("name") or not p.get("source"):
        errs.append(f"plugin entry needs name+source: {p}")
        continue
    pj = pathlib.Path(p["source"], ".claude-plugin", "plugin.json")
    if not pj.exists():
        errs.append(f"missing {pj}")
        continue
    d = json.loads(pj.read_text(encoding="utf-8"))
    if not d.get("name") or not d.get("version"):
        errs.append(f"{pj} missing name/version")

for sk in sorted(pathlib.Path("plugins/agentic-sop-kit/skills").glob("*/SKILL.md")):
    t = sk.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", t, re.S)
    if not m:
        errs.append(f"{sk} missing YAML frontmatter")
        continue
    fm = m.group(1)
    if "name:" not in fm or "description:" not in fm:
        errs.append(f"{sk} frontmatter needs name + description")

if errs:
    print("❌ manifest validation failed:")
    for e in errs:
        print("  -", e)
    sys.exit(1)
print("✅ manifests + skill frontmatter valid")
