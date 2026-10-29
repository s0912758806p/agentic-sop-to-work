#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Plugin SessionStart hook — PROJECT-SCOPED dependency check.

If the current project has an agentic-sop-kit/, run its check_deps.py so missing
dependencies fail loud at session start. No-op for projects without the kit, and no-op when
the project's own settings already run check_deps.py on SessionStart (projects bootstrapped
before v1.10.1) — so the check never runs twice. Shared logic: kit/hooks/_regression_core.py.
"""
import sys

# Python-version guard FIRST, in syntax any Python 3 (and 2) can parse: the rest of the hook
# imports modules that use 3.8 features, and a hook must never crash a session.
if sys.version_info < (3, 8):
    sys.stderr.write("agentic-sop-kit hook skipped: needs Python >= 3.8 (found %s)\n"
                     % sys.version.split()[0])
    sys.exit(0)

import os  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kit", "hooks"))
from _regression_core import SESSION_MARK, project_registers, session_check  # noqa: E402


def main():
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if project_registers(project, "SessionStart", SESSION_MARK):
        return 0
    return session_check(os.path.join(project, "agentic-sop-kit"))


if __name__ == "__main__":
    sys.exit(main())
