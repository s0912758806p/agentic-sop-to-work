# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Guard: the engine (lib/ + workflow/) must import only the Python standard library."""
import ast
import os
import sys
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STDLIB = set(getattr(sys, "stdlib_module_names", set())) | {"kit", "gates", "flow", "engine"}


def _imports(path):
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            mods.add(n.module.split(".")[0])
    return mods


class NoThirdParty(unittest.TestCase):
    def test_engine_is_stdlib_only(self):
        if not getattr(sys, "stdlib_module_names", None):
            raise unittest.SkipTest("stdlib_module_names unavailable (<3.10); guard runs on CI's 3.x")
        offenders = {}
        for sub in ("lib", "workflow"):
            base = os.path.join(KIT, sub)
            for dp, _, fns in os.walk(base):
                for fn in fns:
                    if fn.endswith(".py"):
                        bad = _imports(os.path.join(dp, fn)) - STDLIB
                        if bad:
                            offenders[os.path.join(sub, fn)] = sorted(bad)
        self.assertEqual(offenders, {}, f"third-party imports in engine: {offenders}")


if __name__ == "__main__":
    unittest.main()
