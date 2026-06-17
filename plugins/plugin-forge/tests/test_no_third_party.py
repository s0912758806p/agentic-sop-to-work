# SPDX-License-Identifier: MIT
"""Invariant: pluginforge engine is stdlib-only (examples/ are fixtures, excluded)."""
import ast
import glob
import os
import sys
import unittest

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(PLUGIN, "pluginforge")
_STDLIB = set(getattr(sys, "stdlib_module_names", ()))
_FALLBACK = {"json", "os", "re", "sys", "ast", "glob", "argparse", "dataclasses", "typing", "datetime"}
ALLOWED = (_STDLIB or _FALLBACK) | {"pluginforge"}


class TestNoThirdParty(unittest.TestCase):
    def test_stdlib_only(self):
        offenders = []
        paths = glob.glob(os.path.join(PKG, "*.py")) + glob.glob(os.path.join(PKG, "rules", "*.py"))
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
