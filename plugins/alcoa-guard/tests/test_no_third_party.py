# SPDX-License-Identifier: MIT
"""Invariant: alcoaguard is STDLIB-ONLY (a blank project runs it with python3 alone).
Parses every alcoaguard/*.py AND alcoaguard/rules/*.py and asserts each top-level import is a
stdlib module (or the package's own 'alcoaguard')."""
import ast
import glob
import os
import sys
import unittest

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(PLUGIN, "alcoaguard")

_STDLIB = set(getattr(sys, "stdlib_module_names", ()))
_FALLBACK = {"json", "csv", "math", "os", "re", "sys", "argparse", "dataclasses", "typing", "datetime"}
ALLOWED = (_STDLIB or _FALLBACK) | {"alcoaguard"}


class TestNoThirdParty(unittest.TestCase):
    def test_engine_is_stdlib_only(self):
        offenders = []
        paths = glob.glob(os.path.join(PKG, "*.py")) + glob.glob(os.path.join(PKG, "rules", "*.py"))
        self.assertGreater(len(paths), 0, f"no alcoaguard source files found under {PKG!r}")
        for path in paths:
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        if top not in ALLOWED:
                            offenders.append(f"{os.path.basename(path)}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    top = node.module.split(".")[0]
                    if top not in ALLOWED:
                        offenders.append(f"{os.path.basename(path)}: from {node.module}")
        self.assertEqual(offenders, [], f"third-party imports found: {offenders}")


if __name__ == "__main__":
    unittest.main()
