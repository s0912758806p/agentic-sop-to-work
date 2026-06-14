#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Plugin SessionStart hook — install health check that NEVER blocks.

Verifies the bundled, stdlib-only engine imports under python3>=3.8 so a broken install
surfaces once at session start rather than mysteriously mid-review. Always exits 0 — it
is advisory, never a gate (the real enforcement, if any, is the optional 做法 3 Stop-hook).
"""
import os
import sys

ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
problems = []

if sys.version_info < (3, 8):
    problems.append(f"python>=3.8 required (have {sys.version.split()[0]})")

sys.path.insert(0, ROOT)
try:
    import secondop.review  # noqa: F401
except Exception as e:  # pragma: no cover - defensive
    problems.append(f"engine import failed: {e}")

if problems:
    print("[second-opinion] install check: " + "; ".join(problems), file=sys.stderr)

sys.exit(0)  # advisory; never block a session
