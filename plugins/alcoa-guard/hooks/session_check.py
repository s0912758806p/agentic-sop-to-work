#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""SessionStart health check: verify python>=3.8 and that the engine imports. Always exit 0."""
import os
import sys

ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
problems = []

if sys.version_info < (3, 8):
    problems.append(f"python>=3.8 required (have {sys.version.split()[0]})")

sys.path.insert(0, ROOT)
try:
    import alcoaguard.review  # noqa: F401
except Exception as e:  # pragma: no cover - defensive
    problems.append(f"engine import failed: {e}")

if problems:
    print("[alcoa-guard] install check: " + "; ".join(problems), file=sys.stderr)

sys.exit(0)
