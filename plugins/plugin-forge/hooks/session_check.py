#!/usr/bin/env python3
# GENERATED from shared/sopcore/harness.py by tools/sync_core.py — do not edit this copy; edit the source and re-run `python3 tools/sync_core.py`.
# sopcore-sha256: 36ef103d28074851c6a2ae985c4da5db9159cff337c11102f5a941fcbcd2d8c1
# SPDX-License-Identifier: MIT
"""SessionStart hook: install health check that NEVER blocks (logic in pluginforge/_core/session.py)."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E401,E702
from pluginforge._core import session; sys.exit(session.main("plugin-forge", "pluginforge.lint"))  # noqa: E402,E702
