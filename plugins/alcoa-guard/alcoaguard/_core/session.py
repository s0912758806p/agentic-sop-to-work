# GENERATED from shared/sopcore/session.py by tools/sync_core.py — do not edit this copy; edit the source and re-run `python3 tools/sync_core.py`.
# sopcore-sha256: aa226265a0726fc3e4f2868944bc2203eaedafc8eecef09683e8d103c087e37a
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""SessionStart install health check, shared by every companion's hooks/session_check.py.

Verifies python>=3.8 and that the plugin's engine imports, so a broken install surfaces once
at session start rather than mysteriously mid-review. Advisory: it NEVER blocks a session —
`main()` always returns 0, whatever it finds.
"""
import importlib
import sys


def problems(probe_module):
    found = []
    if sys.version_info < (3, 8):
        found.append("python>=3.8 required (have %s)" % sys.version.split()[0])
    try:
        importlib.import_module(probe_module)
    except Exception as e:  # any import-time failure is the finding
        found.append("engine import failed: %s" % e)
    return found


def main(label, probe_module):
    found = problems(probe_module)
    if found:
        print("[%s] install check: %s" % (label, "; ".join(found)), file=sys.stderr)
    return 0
