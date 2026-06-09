#!/usr/bin/env python3
"""Plugin SessionStart hook — PROJECT-SCOPED dependency check.

If the current project has an agentic-sop-kit/, run its check_deps.py so missing
dependencies fail loud at session start. No-op for projects without the kit, so
the plugin stays quiet in unrelated projects.
"""
import os
import subprocess
import sys

PROJECT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
CHECK = os.path.join(PROJECT, "agentic-sop-kit", "check_deps.py")

if os.path.exists(CHECK):
    sys.exit(subprocess.run([sys.executable, CHECK]).returncode)
sys.exit(0)
