# SPDX-License-Identifier: MIT
"""Invariant: the engine is STDLIB-ONLY (so a blank project runs it with python3 alone).

Parses every secondop/*.py and asserts each absolute top-level import is a stdlib module
(or the package's own 'secondop'). Mirrors the kit's no-third-party guarantee.
"""
import ast
import glob
import os
import sys
import unittest

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(PLUGIN, "secondop")

# Python 3.10+ exposes the full set; fall back to the engine's known stdlib imports.
_STDLIB = set(getattr(sys, "stdlib_module_names", ()))
_FALLBACK = {"json", "math", "os", "re", "sys", "argparse", "dataclasses", "typing", "datetime"}
ALLOWED = (_STDLIB or _FALLBACK) | {"secondop"}


class TestNoThirdParty(unittest.TestCase):
    def test_engine_is_stdlib_only(self):
        offenders = []
        for path in glob.glob(os.path.join(PKG, "*.py")):
            tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
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
