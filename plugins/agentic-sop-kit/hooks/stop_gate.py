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
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kit", "hooks"))
from _regression_core import STOP_MARK, project_registers, stop_gate  # noqa: E402


def main():
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if project_registers(project, "Stop", STOP_MARK):
        return 0
    return stop_gate(os.path.join(project, "agentic-sop-kit"))


if __name__ == "__main__":
    sys.exit(main())
