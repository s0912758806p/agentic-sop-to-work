# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Loop-control instruments for the agentic-sop-kit engine (Loop Engineering triad):
progress (stall detection) · health (regression-run health) · state (bounded run-state)."""
from . import health, progress, state  # noqa: F401  eager: `from loop import x` via the lib shim
