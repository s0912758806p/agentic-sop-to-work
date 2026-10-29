#!/usr/bin/env python3
# GENERATED from shared/sopcore/harness.py by tools/sync_core.py — do not edit this copy; edit the source and re-run `python3 tools/sync_core.py`.
# sopcore-sha256: 37b06ec4e32f4cabc1713a97696fee079533fe0c4b3869afbb32e5b428a0e2f7
# SPDX-License-Identifier: MIT
"""SessionStart hook: install health check that NEVER blocks (logic in pluginforge/_core/session.py).
The version guard comes first and uses only old syntax, so an old python3 no-ops with a message
instead of crashing on the engine's imports."""
import os, sys  # noqa: E401
if sys.version_info < (3, 8):
    sys.stderr.write("[plugin-forge] needs python>=3.8 (have %s) — hook skipped\n" % sys.version.split()[0])
    sys.exit(0)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge._core import session; sys.exit(session.main("plugin-forge", "pluginforge.lint"))  # noqa: E402,E702
