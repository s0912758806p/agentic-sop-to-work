#!/usr/bin/env python3
# GENERATED from shared/sopcore/harness.py by tools/sync_core.py — do not edit this copy; edit the source and re-run `python3 tools/sync_core.py`.
# sopcore-sha256: dc55e3c4c0769868a60a3771fefdbf4f63a0a0e46e2045669c749db319cc3fb9
# SPDX-License-Identifier: MIT
"""SessionStart hook: install health check that NEVER blocks (logic in secondop/_core/session.py)."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E401,E702
from secondop._core import session; sys.exit(session.main("second-opinion", "secondop.review"))  # noqa: E402,E702
