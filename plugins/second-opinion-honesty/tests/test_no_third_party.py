# GENERATED from shared/sopcore/harness.py by tools/sync_core.py — do not edit this copy; edit the source and re-run `python3 tools/sync_core.py`.
# sopcore-sha256: a3e44327e50f21281d299c42e669609a405c8deb406e0d1d5ad2c375f199045c
# SPDX-License-Identifier: MIT
"""Invariant: the secondop engine is STDLIB-ONLY (a blank project runs it with python3 alone).

Parses every .py under secondop/ (subpackages and the vendored _core/ included; examples/
are fixtures and excluded) and asserts each absolute import is stdlib or secondop itself.
"""
import ast
import importlib.util
import os
import sys
import sysconfig
import unittest

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(PLUGIN, "secondop")
OWN = "secondop"
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
