---
name: plugin-forge
description: Use when creating, scaffolding, or linting a Claude Code plugin — generate a grammar-conformant plugin skeleton, or validate a plugin / whole marketplace against house invariants (manifest, frontmatter, stdlib-only, hook protocol, test harness). ｜ 要新建 / scaffold 一個 Claude Code plugin，或 lint 既有 plugin / 整個 marketplace 是否符合房規時使用。
---

# plugin-forge — lint + scaffold Claude Code plugins

## Lint
- One plugin: `python3 plugins/plugin-forge/pluginforge/lint.py <plugin-dir>`
- Whole marketplace: `python3 plugins/plugin-forge/pluginforge/lint.py --all --strict`
- `--strict` adds house invariants (stdlib-only, verify.py, test_no_third_party). Exits 1 on any HARD.

## Scaffold
- `python3 plugins/plugin-forge/pluginforge/scaffold.py <name>` → a skeleton that passes `lint --strict`.
- Then add it to `marketplace.json` + CI and flesh out the TODOs.

The lint report is a DRAFT; a human decides. HARD = fails CI; SOFT = advisory.
