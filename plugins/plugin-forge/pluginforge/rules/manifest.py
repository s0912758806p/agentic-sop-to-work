# SPDX-License-Identifier: MIT
"""Tier-0 manifest checks (strict superset of validate_manifests) + recommended fields + the
shape of plugin.json `userConfig` (HARD: Claude Code rejects a malformed option at load)."""
import json
import os
import re
from ..model import Finding

_REC = ("author", "license", "keywords")
# plugin.json userConfig: each key an identifier; each value a STRICT object (unknown keys are
# load errors in Claude Code) with a known type + title + description.
_UC_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_UC_TYPES = {"string", "number", "boolean", "directory", "file"}
_UC_FIELDS = {"type", "title", "description", "required", "default", "options", "multiple",
              "sensitive", "min", "max"}


def _user_config(uc, name):
    loc = ".claude-plugin/plugin.json"

    def bad(key, detail):
        return Finding(f"manifest:userConfig:{key}", "manifest", "HARD", name, loc, detail)

    if not isinstance(uc, dict):
        return [bad("shape", "userConfig must be an object of {key: option}")]
    out = []
    for key, opt in uc.items():
        if not _UC_KEY.match(str(key)):
            out.append(bad(key, f"userConfig key {key!r} must be an identifier"))
        elif not isinstance(opt, dict):
            out.append(bad(key, f"userConfig.{key} must be an object"))
        elif opt.get("type") not in _UC_TYPES:
            out.append(bad(key, f"userConfig.{key}.type must be one of {sorted(_UC_TYPES)}"))
        elif not opt.get("title") or not opt.get("description"):
            out.append(bad(key, f"userConfig.{key} needs title + description"))
        elif set(opt) - _UC_FIELDS:
            out.append(bad(key, f"userConfig.{key} has unknown field(s) {sorted(set(opt) - _UC_FIELDS)}"))
    return out


def _name(plugin_dir):
    return os.path.basename(os.path.normpath(plugin_dir))


def check_plugin_manifest(plugin_dir, strict):
    name = _name(plugin_dir)
    pj = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
    if not os.path.exists(pj):
        return [Finding("manifest:plugin:missing", "manifest", "HARD", name,
                        ".claude-plugin/plugin.json", "missing plugin.json")]
    try:
        with open(pj, encoding="utf-8") as f:
            d = json.load(f)
    except ValueError as e:
        return [Finding("manifest:plugin:json", "manifest", "HARD", name,
                        ".claude-plugin/plugin.json", f"invalid JSON: {e}")]
    findings = []
    if not d.get("name") or not d.get("version"):
        findings.append(Finding("manifest:plugin:fields", "manifest", "HARD", name,
                                ".claude-plugin/plugin.json", "plugin.json missing name/version"))
    if "userConfig" in d:
        findings.extend(_user_config(d["userConfig"], name))
    if strict:
        for rec in _REC:
            if not d.get(rec):
                findings.append(Finding(f"manifest:plugin:rec:{rec}", "manifest", "SOFT", name,
                                        ".claude-plugin/plugin.json", f"recommended field missing: {rec}"))
    return findings


def check_marketplace(repo_root):
    loc = ".claude-plugin/marketplace.json"
    mp = os.path.join(repo_root, ".claude-plugin", "marketplace.json")
    if not os.path.exists(mp):
        return [Finding("manifest:marketplace:missing", "manifest", "HARD", "<marketplace>", loc,
                        "missing marketplace.json")]
    try:
        with open(mp, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        return [Finding("manifest:marketplace:json", "manifest", "HARD", "<marketplace>", loc,
                        f"invalid JSON: {e}")]
    findings = []
    if not data.get("name") or not isinstance(data.get("plugins"), list):
        findings.append(Finding("manifest:marketplace:fields", "manifest", "HARD", "<marketplace>", loc,
                                "marketplace.json missing name/plugins"))
    for i, p in enumerate(data.get("plugins", [])):
        if not p.get("name") or not p.get("source"):
            findings.append(Finding(f"manifest:entry:{i}", "manifest", "HARD", "<marketplace>", loc,
                                    f"plugin entry needs name+source: {p}"))
            continue
        pj = os.path.join(repo_root, p["source"], ".claude-plugin", "plugin.json")
        if not os.path.exists(pj):
            findings.append(Finding(f"manifest:pluginjson:{i}:{p['name']}", "manifest", "HARD",
                                    p["name"], p["source"],
                                    f"missing {p['source']}/.claude-plugin/plugin.json"))
    return findings
