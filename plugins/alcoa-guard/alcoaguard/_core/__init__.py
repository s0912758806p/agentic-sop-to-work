# GENERATED from shared/sopcore/__init__.py by tools/sync_core.py — do not edit this copy; edit the source and re-run `python3 tools/sync_core.py`.
# sopcore-sha256: 77352272f5a5f6aac44fd4a6e07485160f70841ae9c74ae41651debc52b45d44
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""sopcore — the shared core of the agentic-sop-to-work companion plugins.

Single source: `shared/sopcore/` at the repo root. It is VENDORED (copied, never imported
across plugins) into each companion as `<pkg>/_core/` by `tools/sync_core.py`, so every
plugin still installs and runs standalone. CI runs `sync_core.py --check` and plugin-forge's
`vendored-core-drift` rule, so a hand-edited or stale copy fails the build.

Modules use relative imports only, so the same bytes work as `sopcore.x` and `<pkg>._core.x`.
  run_contract  the single reader definition of an agentic-sop-kit run dir
  findings      Severity, a Finding base, dedupe + HARD/SOFT count
  report        the DRAFT / ADVISORY_ONLY / human_owns_verdict frame + md/json dual write
  arithmetic    deterministic recompute + verdict re-evaluation
  markers       the 【待補】 placeholder
  cli           the shared --run-dir / --out-base argparse skeleton
  session       the SessionStart install health check
  harness       templates for the generated test harness + hook wrapper
  vendor        the GENERATED stamp (+ content hash) on every vendored copy
"""
