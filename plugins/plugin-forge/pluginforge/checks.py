# SPDX-License-Identifier: MIT
"""Aggregate the rules into a LintReport. Tier-0 always runs; Tier-1 runs when strict."""
from . import discover
from .model import LintReport
from .rules import manifest, frontmatter, hooks, stdlib
from .rules import tests as tests_rule

# Plugin-level rule modules with a uniform check(plugin_dir, strict) signature.
_PLUGIN_RULES = (frontmatter, hooks, stdlib, tests_rule)


def lint_plugin(plugin_dir, strict):
    findings = list(manifest.check_plugin_manifest(plugin_dir, strict))
    for mod in _PLUGIN_RULES:
        findings.extend(mod.check(plugin_dir, strict))
    return findings


def run_lint(repo_root=None, plugin_dir=None, all_plugins=False, strict=False):
    findings, targets = [], []
    if all_plugins:
        targets.append("<marketplace>")
        findings.extend(manifest.check_marketplace(repo_root))
        for nm, pdir in discover.from_marketplace(repo_root):
            targets.append(nm)
            findings.extend(lint_plugin(pdir, strict))
    else:
        targets.append(discover.plugin_name(plugin_dir))
        findings.extend(lint_plugin(plugin_dir, strict))
    seen, deduped = set(), []
    for f in findings:
        key = (f.id, f.plugin)
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    hard = sum(1 for f in deduped if f.severity == "HARD")
    soft = sum(1 for f in deduped if f.severity == "SOFT")
    return LintReport(targets=targets, hard=hard, soft=soft, findings=deduped)
