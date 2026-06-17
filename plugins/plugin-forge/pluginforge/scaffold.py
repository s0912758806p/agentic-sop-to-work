#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate a grammar-conformant plugin skeleton that passes `lint --strict` by construction."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge import templates as T  # noqa: E402
from pluginforge.model import PluginSpec  # noqa: E402


def _render(text, spec):
    return text.replace("<<NAME>>", spec.name).replace("<<PKG>>", spec.pkg)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def generate(spec, dest_root):
    """Create plugins/<name>/ under dest_root. Returns the plugin dir."""
    pdir = os.path.join(dest_root, "plugins", spec.name)
    if os.path.exists(pdir):
        raise FileExistsError(f"plugin directory already exists: {pdir}")
    files = {
        ".claude-plugin/plugin.json": T.PLUGIN_JSON,
        "README.md": T.README_MD,
        f"{spec.pkg}/__init__.py": T.INIT_PY,
        f"{spec.pkg}/model.py": T.MODEL_PY,
        f"{spec.pkg}/review.py": T.REVIEW_PY,
        "hooks/hooks.json": T.HOOKS_JSON,
        "hooks/session_check.py": T.SESSION_CHECK_PY,
        f"skills/{spec.name}/SKILL.md": T.SKILL_MD,
        f"commands/{spec.name}.md": T.COMMAND_MD,
        "tests/verify.py": T.VERIFY_PY,
        "tests/test_no_third_party.py": T.NO_THIRD_PARTY_PY,
        "tests/test_smoke.py": T.SMOKE_TEST_PY,
    }
    for rel, text in files.items():
        _write(os.path.join(pdir, rel), _render(text, spec))
    os.makedirs(os.path.join(pdir, f"{spec.pkg}", "examples"), exist_ok=True)
    return pdir


def main(argv=None):
    ap = argparse.ArgumentParser(description="scaffold a new Claude Code plugin")
    ap.add_argument("name", help="plugin name (kebab-case)")
    ap.add_argument("--pkg", default=None, help="python package name (default: name without hyphens)")
    ap.add_argument("--dest-root", default=".", help="repo root (default: .)")
    a = ap.parse_args(argv)
    spec = PluginSpec(name=a.name, pkg=a.pkg)
    pdir = generate(spec, a.dest_root)
    print(f"[plugin-forge] scaffolded {pdir}")
    print(f"[plugin-forge] next: add to marketplace.json + CI, then `lint {pdir} --strict`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
