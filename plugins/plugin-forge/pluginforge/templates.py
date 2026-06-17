# SPDX-License-Identifier: MIT
"""Skeleton file templates for scaffold.py. Tokens: <<NAME>> (plugin name), <<PKG>> (package)."""

PLUGIN_JSON = '''{
  "name": "<<NAME>>",
  "description": "TODO: one-paragraph description of <<NAME>>.",
  "version": "0.1.0",
  "author": { "name": "s0912758806p", "url": "https://github.com/s0912758806p" },
  "homepage": "https://github.com/s0912758806p/agentic-sop-to-work",
  "repository": "https://github.com/s0912758806p/agentic-sop-to-work",
  "license": "MIT",
  "keywords": ["<<NAME>>", "claude-code", "agentic-sop"]
}
'''

INIT_PY = "# SPDX-License-Identifier: MIT\n"

MODEL_PY = '''# SPDX-License-Identifier: MIT
"""Data model for <<NAME>>."""
from dataclasses import dataclass


@dataclass
class Result:
    ok: bool
    detail: str = ""
'''

REVIEW_PY = '''#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""<<NAME>> CLI entry point."""
import argparse
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(description="<<NAME>>")
    ap.add_argument("--in", dest="inp", help="input")
    ap.parse_args(argv)
    print("<<NAME>>: TODO implement")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

HOOKS_JSON = '''{
  "_comment": "SessionStart health-check only.",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          { "type": "command", "command": "python3 \\"${CLAUDE_PLUGIN_ROOT}/hooks/session_check.py\\"" }
        ]
      }
    ]
  }
}
'''

SESSION_CHECK_PY = '''#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""SessionStart health check: python>=3.8 + engine imports. Always exit 0."""
import os
import sys

ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
problems = []
if sys.version_info < (3, 8):
    problems.append("python>=3.8 required")
sys.path.insert(0, ROOT)
try:
    import <<PKG>>.review  # noqa: F401
except Exception as e:  # pragma: no cover
    problems.append(f"engine import failed: {e}")
if problems:
    print("[<<NAME>>] install check: " + "; ".join(problems), file=sys.stderr)
sys.exit(0)
'''

SKILL_MD = '''---
name: <<NAME>>
description: TODO — when to use <<NAME>>.
---

# <<NAME>>

TODO: workflow.
'''

COMMAND_MD = '''---
description: TODO — what /<<NAME>> does.
argument-hint: "<args>"
---

# /<<NAME>>

TODO.
'''

README_MD = '''# <<NAME>>

TODO: description. A companion in the agentic-sop-to-work suite; runs standalone too.

```bash
python3 -m <<PKG>>.review --in <input>
```
'''

VERIFY_PY = '''#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression runner: run every test_*.py as a subprocess. Exit 0 = all green."""
import glob
import os
import subprocess
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))


def main():
    files = sorted(glob.glob(os.path.join(TESTS, "test_*.py")))
    failed, ran = [], 0
    for f in files:
        r = subprocess.run([sys.executable, f], capture_output=True, text=True)
        n = ""
        for ln in r.stderr.splitlines():
            if ln.startswith("Ran "):
                n = ln.split()[1]
        print(f"{'PASS' if r.returncode == 0 else 'FAIL'}  {os.path.basename(f):<28} ({n} tests)")
        ran += int(n or 0)
        if r.returncode != 0:
            failed.append(os.path.basename(f))
            print(r.stdout); print(r.stderr)
    print(f"\\n{len(files) - len(failed)}/{len(files)} files passed · {ran} tests total")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
'''

NO_THIRD_PARTY_PY = '''# SPDX-License-Identifier: MIT
"""Invariant: <<PKG>> is stdlib-only."""
import ast
import glob
import os
import sys
import unittest

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(PLUGIN, "<<PKG>>")
_STDLIB = set(getattr(sys, "stdlib_module_names", ()))
_FALLBACK = {"json", "os", "re", "sys", "argparse", "dataclasses", "typing", "datetime"}
ALLOWED = (_STDLIB or _FALLBACK) | {"<<PKG>>"}


class TestNoThirdParty(unittest.TestCase):
    def test_stdlib_only(self):
        offenders = []
        paths = glob.glob(os.path.join(PKG, "*.py")) + glob.glob(os.path.join(PKG, "**", "*.py"))
        self.assertGreater(len(paths), 0, f"no sources under {PKG!r}")
        for path in paths:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        if a.name.split(".")[0] not in ALLOWED:
                            offenders.append(f"{os.path.basename(path)}: import {a.name}")
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    if node.module.split(".")[0] not in ALLOWED:
                        offenders.append(f"{os.path.basename(path)}: from {node.module}")
        self.assertEqual(offenders, [], f"third-party imports: {offenders}")


if __name__ == "__main__":
    unittest.main()
'''

SMOKE_TEST_PY = '''import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import <<PKG>>.review

class TestSmoke(unittest.TestCase):
    def test_main_runs(self):
        self.assertEqual(<<PKG>>.review.main([]), 0)

if __name__ == "__main__":
    unittest.main()
'''
