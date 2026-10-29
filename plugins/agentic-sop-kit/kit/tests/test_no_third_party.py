# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Guards on the engine's import surface.

  • stdlib-only: sopkit/ + lib/ + workflow/ import nothing but the standard library and the
    kit's own names (`sopkit`, plus the deprecated lib/ shim names).
  • one entry point: sopkit/ never touches sys.path and imports its siblings relatively;
    outside lib/ (the deprecated shims) no file puts kit/lib on sys.path any more — every
    script that needs the engine puts the KIT ROOT there (or lives in it) and imports sopkit.
"""
import ast
import os
import sys
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL = {"sopkit", "_shim", "kit", "gates", "flow", "engine", "loop", "schema", "graph"}
STDLIB = set(getattr(sys, "stdlib_module_names", set())) | LOCAL
ENGINE_DIRS = ("sopkit", "lib", "workflow")


def _py_files(*subs):
    for sub in subs:
        for dp, dns, fns in os.walk(os.path.join(KIT, sub)):
            dns[:] = [d for d in dns if d not in ("__pycache__", "runs", "golden")]
            for fn in fns:
                if fn.endswith(".py"):
                    yield os.path.join(dp, fn)


def _tree(path):
    with open(path, encoding="utf-8") as f:
        return ast.parse(f.read())


def _imports(tree):
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            mods.add(n.module.split(".")[0])
    return mods


def _is_sys_path_insert(n):
    f = getattr(n, "func", None) if isinstance(n, ast.Call) else None
    return (isinstance(f, ast.Attribute) and f.attr == "insert"
            and isinstance(f.value, ast.Attribute) and f.value.attr == "path"
            and isinstance(f.value.value, ast.Name) and f.value.value.id == "sys")


def _rel(path):
    return os.path.relpath(path, KIT).replace(os.sep, "/")


class NoThirdParty(unittest.TestCase):
    def test_engine_is_stdlib_only(self):
        if not getattr(sys, "stdlib_module_names", None):
            raise unittest.SkipTest("stdlib_module_names unavailable (<3.10); guard runs on CI's 3.x")
        offenders = {}
        for p in _py_files(*ENGINE_DIRS):
            bad = _imports(_tree(p)) - STDLIB
            if bad:
                offenders[_rel(p)] = sorted(bad)
        self.assertEqual(offenders, {}, f"third-party imports in engine: {offenders}")


class OneEntryPoint(unittest.TestCase):
    def test_sopkit_is_self_contained(self):
        """No sys.path games and no absolute imports of kit-local names inside the package."""
        bad = []
        for p in _py_files("sopkit"):
            tree = _tree(p)
            if any(isinstance(n, ast.Attribute) and n.attr == "path" and isinstance(n.value, ast.Name)
                   and n.value.id == "sys" for n in ast.walk(tree)):
                bad.append(f"{_rel(p)}: touches sys.path")
            local = _imports(tree) & LOCAL
            if local:
                bad.append(f"{_rel(p)}: absolute import of {sorted(local)} — use a relative import")
        self.assertEqual(bad, [])

    def test_nothing_outside_lib_puts_lib_on_path(self):
        bad = []
        for p in _py_files("."):
            rel = _rel(p)
            if rel.startswith("lib/"):
                continue
            for n in ast.walk(_tree(p)):
                if _is_sys_path_insert(n) and any(
                        isinstance(c, ast.Constant) and c.value == "lib" for c in ast.walk(n)):
                    bad.append(rel)
        self.assertEqual(bad, [], "use the kit root + `from sopkit import ...` instead of kit/lib")


if __name__ == "__main__":
    unittest.main()
