# SPDX-License-Identifier: MIT
"""Resolve lint targets: a single plugin dir, or all plugins from a marketplace.json."""
import json
import os


def from_marketplace(repo_root):
    """Return [(name, abs_plugin_dir), ...] from <repo_root>/.claude-plugin/marketplace.json.
    Returns [] if the file is missing/invalid (check_marketplace reports that as a HARD finding);
    only yields entries that have BOTH name and source (nameless entries are flagged separately)."""
    mp = os.path.join(repo_root, ".claude-plugin", "marketplace.json")
    try:
        with open(mp, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    for p in data.get("plugins", []):
        src, name = p.get("source"), p.get("name")
        if src and name:
            out.append((name, os.path.normpath(os.path.join(repo_root, src))))
    return out


def plugin_name(plugin_dir):
    """The plugin's declared name, else the directory basename."""
    pj = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
    try:
        with open(pj, encoding="utf-8") as f:
            return json.load(f).get("name") or os.path.basename(os.path.normpath(plugin_dir))
    except (OSError, ValueError):
        return os.path.basename(os.path.normpath(plugin_dir))
