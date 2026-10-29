# SPDX-License-Identifier: MIT
"""Skeleton file templates for scaffold.py. Tokens: <<NAME>> (plugin name), <<PKG>> (package).

The shared harness (tests/verify.py, tests/test_no_third_party.py, hooks/session_check.py)
is NOT templated here: scaffold renders it from _core/harness.py, and copies the vendored
core (_core/*.py, the suite's shared/sopcore) into the new package verbatim — so a
scaffolded plugin ships the same run-dir contract, findings, report frame and arithmetic as
the companions."""

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
"""Data model for <<NAME>>. Findings can build on the shared base in _core/findings.py
(Severity, Finding, dedupe + count)."""
from dataclasses import dataclass

from ._core.findings import Finding, Severity  # noqa: F401


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

SMOKE_TEST_PY = '''# SPDX-License-Identifier: MIT
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import <<PKG>>.review

class TestSmoke(unittest.TestCase):
    def test_main_runs(self):
        self.assertEqual(<<PKG>>.review.main([]), 0)

if __name__ == "__main__":
    unittest.main()
'''
