#!/usr/bin/env python3
# GENERATED from shared/sopcore/harness.py by tools/sync_core.py — do not edit this copy; edit the source and re-run `python3 tools/sync_core.py`.
# sopcore-sha256: 1422b9e96f5c07e741c3f5e2cdcca776a06d8367a344cde5255c479b64114926
# SPDX-License-Identifier: MIT
"""SessionStart hook: install health check that NEVER blocks (logic in alcoaguard/_core/session.py)."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E401,E702
from alcoaguard._core import session; sys.exit(session.main("alcoa-guard", "alcoaguard.review"))  # noqa: E402,E702
