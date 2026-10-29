#!/usr/bin/env python3
# GENERATED from shared/sopcore/harness.py by tools/sync_core.py — do not edit this copy; edit the source and re-run `python3 tools/sync_core.py`.
# sopcore-sha256: dd4297470fb02bebc39290ebd9926769a90c2a1e5ed4a8f182fc6486a6ae3a19
# SPDX-License-Identifier: MIT
"""SessionStart hook: install health check that NEVER blocks (logic in secondop/_core/session.py).
The version guard comes first and uses only old syntax, so an old python3 no-ops with a message
instead of crashing on the engine's imports."""
import os, sys  # noqa: E401
if sys.version_info < (3, 8):
    sys.stderr.write("[second-opinion] needs python>=3.8 (have %s) — hook skipped\n" % sys.version.split()[0])
    sys.exit(0)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from secondop._core import session; sys.exit(session.main("second-opinion", "secondop.review"))  # noqa: E402,E702
