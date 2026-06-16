# SPDX-License-Identifier: MIT
"""Resolve lint targets: a single plugin dir, or all plugins from a marketplace.json."""
import json
import os


def from_marketplace(repo_root):
    """Return [(name, abs_plugin_dir), ...] from <repo_root>/.claude-plugin/marketplace.json."""
    mp = os.path.join(repo_root, ".claude-plugin", "marketplace.json")
    with open(mp, encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for p in data.get("plugins", []):
        src = p.get("source")
        if src:
            out.append((p.get("name") or src, os.path.normpath(os.path.join(repo_root, src))))
    return out


def plugin_name(plugin_dir):
    """The plugin's declared name, else the directory basename."""
    pj = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
    try:
        with open(pj, encoding="utf-8") as f:
            return json.load(f).get("name") or os.path.basename(os.path.normpath(plugin_dir))
    except (OSError, ValueError):
        return os.path.basename(os.path.normpath(plugin_dir))
