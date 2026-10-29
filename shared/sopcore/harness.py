# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
'''Templates for the per-plugin files that used to be copy-pasted between companions.

tools/sync_core.py renders them into every companion; plugin-forge's scaffold renders them
into every new plugin. Tokens: <<PKG>> (python package), <<LABEL>> (log prefix),
<<PROBE>> (module the SessionStart check imports).
  tests/verify.py               run every tests/test_*.py as a subprocess (exit 0 = green)
  tests/test_no_third_party.py  the engine package imports only stdlib (or itself)
  hooks/session_check.py        one call into <<PKG>>/_core/session.py
'''

VERIFY_PY = '''#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regression runner — every unit + integration test must pass.

Each test file is self-contained (it puts the plugin root on sys.path), so we just run
them as subprocesses. One command for CI and humans:
    python3 tests/verify.py        # exit 0 = all green, 1 = something failed
"""
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
        last = (r.stderr.strip().splitlines() or [""])[-1]
        n = ""
        for ln in r.stderr.splitlines():
            if ln.startswith("Ran "):
                n = ln.split()[1]
        print(f"{'PASS' if r.returncode == 0 else 'FAIL'}  {os.path.basename(f):<30} ({n} tests)  {last if r.returncode else ''}")
        ran += int(n or 0)
        if r.returncode != 0:
            failed.append(os.path.basename(f))
            print(r.stdout)
            print(r.stderr)
    print(f"\\n{len(files) - len(failed)}/{len(files)} files passed · {ran} tests total")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
'''

NO_THIRD_PARTY_PY = '''# SPDX-License-Identifier: MIT
"""Invariant: the <<PKG>> engine is STDLIB-ONLY (a blank project runs it with python3 alone).

Parses every .py under <<PKG>>/ (subpackages and the vendored _core/ included; examples/
are fixtures and excluded) and asserts each absolute import is stdlib or <<PKG>> itself.
"""
import ast
import importlib.util
import os
import sys
import sysconfig
import unittest

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(PLUGIN, "<<PKG>>")
OWN = "<<PKG>>"
_STDLIB = set(getattr(sys, "stdlib_module_names", ()))   # Python 3.10+
_STDLIB_DIR = os.path.normcase(os.path.realpath(sysconfig.get_paths()["stdlib"]))


def _is_stdlib(name):
    if name == OWN or name in sys.builtin_module_names or name in _STDLIB:
        return True
    if _STDLIB:
        return False
    spec = importlib.util.find_spec(name)   # < 3.10: decide by where the module lives
    if spec is None:
        return False
    origin = spec.origin or ""
    if origin in ("built-in", "frozen"):
        return True
    origin = os.path.normcase(os.path.realpath(origin))
    return origin.startswith(_STDLIB_DIR) and "site-packages" not in origin


def _sources():
    for root, dirs, files in os.walk(PKG):
        dirs[:] = [d for d in dirs if d not in ("examples", "__pycache__")]
        for fn in files:
            if fn.endswith(".py"):
                yield os.path.join(root, fn)


class TestNoThirdParty(unittest.TestCase):
    def test_engine_is_stdlib_only(self):
        paths = list(_sources())
        self.assertGreater(len(paths), 0, f"no source files found under {PKG!r}")
        offenders = []
        for path in paths:
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
            rel = os.path.relpath(path, PKG)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module]
                else:
                    continue
                offenders += [f"{rel}: {n}" for n in names if not _is_stdlib(n.split(".")[0])]
        self.assertEqual(offenders, [], f"third-party imports found: {offenders}")


if __name__ == "__main__":
    unittest.main()
'''

SESSION_CHECK_PY = '''#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""SessionStart hook: install health check that NEVER blocks (logic in <<PKG>>/_core/session.py).
The version guard comes first and uses only old syntax, so an old python3 no-ops with a message
instead of crashing on the engine's imports."""
import os, sys  # noqa: E401
if sys.version_info < (3, 8):
    sys.stderr.write("[<<LABEL>>] needs python>=3.8 (have %s) — hook skipped\\n" % sys.version.split()[0])
    sys.exit(0)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from <<PKG>>._core import session; sys.exit(session.main("<<LABEL>>", "<<PROBE>>"))  # noqa: E402,E702
'''

FILES = {
    "tests/verify.py": VERIFY_PY,
    "tests/test_no_third_party.py": NO_THIRD_PARTY_PY,
    "hooks/session_check.py": SESSION_CHECK_PY,
}


def render(text, pkg, label, probe):
    return text.replace("<<PKG>>", pkg).replace("<<LABEL>>", label).replace("<<PROBE>>", probe)
