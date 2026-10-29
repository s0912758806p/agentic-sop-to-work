# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""DEPRECATED shim → sopkit.loop (see lib/_shim.py). Removed in v2.0."""
import _shim

_shim.alias("loop", submodules=("health", "progress", "state"))
