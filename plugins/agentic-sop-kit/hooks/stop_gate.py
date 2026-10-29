#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Plugin Stop hook — PROJECT-SCOPED regression gate.

Runs the CURRENT project's agentic-sop-kit/tests/verify.py when present, and NO-OPS
otherwise, so installing this plugin globally never fires regression in unrelated projects.

It also no-ops when the project's .claude/settings(.local).json already registers the kit's
own hooks/stop_regression.py (projects bootstrapped before v1.10.1): one gate per stop, one
owner of tests/.retry_count. The gate logic itself lives in kit/hooks/_regression_core.py,
shared with that project hook; see it for the block / retry-cap behaviour.
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
from _regression_core import STOP_MARK, project_registers, stop_gate  # noqa: E402


def main():
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if project_registers(project, "Stop", STOP_MARK):
        return 0
    return stop_gate(os.path.join(project, "agentic-sop-kit"))


if __name__ == "__main__":
    sys.exit(main())
