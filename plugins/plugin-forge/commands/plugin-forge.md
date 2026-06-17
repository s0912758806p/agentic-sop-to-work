---
description: Lint a Claude Code plugin / marketplace against house invariants, or scaffold a new grammar-conformant plugin skeleton.
argument-hint: "lint <plugin-dir> | lint --all --strict | new <name>"
---

# /plugin-forge

- `lint <plugin-dir>` → `python3 plugins/plugin-forge/pluginforge/lint.py <plugin-dir> [--strict]`
- `lint --all` → `python3 plugins/plugin-forge/pluginforge/lint.py --all --strict`
- `new <name>` → `python3 plugins/plugin-forge/pluginforge/scaffold.py <name>`

Present the lint findings (HARD then SOFT) verbatim; for scaffold, report the new dir + next steps.
