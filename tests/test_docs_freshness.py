# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Docs-freshness gate (repo level): numbers and names the living docs assert are bound to
the values computed from the tree. Fail-closed — if a claimed phrase can no longer be found,
the test goes RED instead of silently passing (a doc that stopped making the claim must be
re-bound here on purpose).

Bound claims:
  • README skills badge (`skills-N`) and "N Skills / N 支 Skills" == plugin-level SKILL.md counts
  • every marketplace plugin's version is recorded in CHANGELOG.md
      agentic-sop-kit → a `## [x.y.z]` heading; companions → `**<name>** (vx.y.z)`
  • marketplace.json lists exactly the plugin dirs under plugins/
  • every SOPKIT_* env var read by plugin code is documented in kit/README.md
  • README "Compatibility / 相容性" tables == the CI test matrix (ci.yml), incl. which OS is non-blocking
  • every `python …` command CI runs is listed in CONTRIBUTING.md's local-checks block
CHANGELOG is a record, not a living doc: it is only checked for presence of entries, never rewritten.

Run: python3 tests/test_docs_freshness.py
"""
import glob
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT_NAME = "agentic-sop-kit"


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _plugin_skill_counts():
    counts = {}
    for p in glob.glob(os.path.join(ROOT, "plugins", "*", "skills", "*", "SKILL.md")):
        name = p.split(os.sep)[-4]
        counts[name] = counts.get(name, 0) + 1
    return counts


def _manifests():
    out = {}
    for p in glob.glob(os.path.join(ROOT, "plugins", "*", ".claude-plugin", "plugin.json")):
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
        out[m["name"]] = m
    return out


def _claim(pattern, text, where):
    """Return the int captured by `pattern`; fail-closed when the claim is gone."""
    m = re.search(pattern, text)
    if not m:
        raise AssertionError(f"claim /{pattern}/ not found in {where} — re-bind this check on purpose")
    return int(m.group(1))


class DocsFreshness(unittest.TestCase):
    def setUp(self):
        self.readme = _read("README.md")
        self.changelog = _read("CHANGELOG.md")
        self.counts = _plugin_skill_counts()
        self.assertTrue(self.counts, "found no plugin SKILL.md at all (fail-closed)")

    def test_skills_badge_matches_tree(self):
        total = sum(self.counts.values())
        self.assertEqual(_claim(r"skills-(\d+)", self.readme, "README badge"), total)

    def test_kit_skill_count_matches_tree(self):
        kit = self.counts.get(KIT_NAME, 0)
        self.assertEqual(_claim(r"\*\*(\d+) Skills\*\*", self.readme, "README (English)"), kit)
        self.assertEqual(_claim(r"\*\*(\d+) 支 Skills\*\*", self.readme, "README (中文)"), kit)

    def test_every_plugin_version_is_in_changelog(self):
        manifests = _manifests()
        self.assertIn(KIT_NAME, manifests)
        missing = []
        for name, m in manifests.items():
            v = re.escape(m["version"])
            pat = (rf"^## \[{v}\]" if name == KIT_NAME else rf"\*\*{re.escape(name)}\*\* \(v{v}\)")
            if not re.search(pat, self.changelog, re.M):
                missing.append(f"{name} {m['version']}")
        self.assertEqual(missing, [], "plugin versions with no CHANGELOG entry")

    def test_marketplace_lists_exactly_the_plugin_dirs(self):
        mk = json.loads(_read(".claude-plugin", "marketplace.json"))
        listed = sorted(p["name"] for p in mk["plugins"])
        on_disk = sorted(_manifests())
        self.assertEqual(listed, on_disk)

    def test_sopkit_env_vars_are_documented(self):
        code = ""
        for p in glob.glob(os.path.join(ROOT, "plugins", "**", "*.py"), recursive=True):
            with open(p, encoding="utf-8") as f:
                code += f.read()
        names = sorted(set(re.findall(r"SOPKIT_[A-Z_]+", code)))
        self.assertTrue(names, "found no SOPKIT_* var in code (fail-closed)")
        doc = _read("plugins", KIT_NAME, "kit", "README.md")
        self.assertEqual([n for n in names if n not in doc], [],
                         "SOPKIT_* env vars read by code but undocumented in kit/README.md")


    # ---- CI ↔ docs -------------------------------------------------------------------
    @staticmethod
    def _ci_matrix():
        ci = _read(".github", "workflows", "ci.yml")
        rows = re.findall(r"-\s*\{\s*os:\s*([\w.-]+),\s*python:\s*\"([\d.x]+)\"(.*?)\}", ci)
        if not rows:
            raise AssertionError("no `- { os: …, python: … }` rows in ci.yml — re-bind this check on purpose")
        return [(os_, py, "experimental: true" in rest) for os_, py, rest in rows]

    def test_compat_table_matches_ci_matrix(self):
        family = {"ubuntu": ("Linux", "Linux"), "macos": ("macOS", "macOS"), "windows": ("Windows", "Windows")}
        for heading, ok, warn in (("**Compatibility**", "✅ tested", "⚠️ runs in CI, non-blocking"),
                                  ("**相容性**", "✅ 已測", "⚠️ CI 有跑，不擋合併")):
            i = self.readme.find(heading)
            self.assertNotEqual(i, -1, f"{heading} table not found in README (fail-closed)")
            table = self.readme[i:self.readme.index("\n\n", self.readme.index("|", i))]
            claimed = set()
            for os_, py, experimental in self._ci_matrix():
                label = family[os_.split("-")[0]][0]
                col = 1 if py == "3.8" else 2
                row = next((ln for ln in table.splitlines() if ln.startswith(f"| {label}")), None)
                self.assertIsNotNone(row, f"{heading}: no row for {label}")
                cell = row.split("|")[col + 1]
                self.assertIn(warn if experimental else ok, cell, f"{heading}: {label} / Python {py}")
                claimed.add((label, col))
            # nothing claimed as tested that CI does not run
            for ln in table.splitlines()[2:]:
                cells = ln.split("|")
                label = cells[1].strip().split(" ")[0].split("（")[0]
                for col in (1, 2):
                    if "✅" in cells[col + 1] or "⚠️" in cells[col + 1]:
                        self.assertIn((label, col), claimed, f"{heading}: {label} col {col} claims CI coverage it lacks")

    def test_contributing_lists_every_ci_command(self):
        ci = _read(".github", "workflows", "ci.yml")
        cmds = sorted(set(re.findall(r"\bpython ((?:plugins|tests|tools)/\S+(?: [-\w]+)*)", ci)))
        self.assertTrue(cmds, "found no `python <path>` command in ci.yml (fail-closed)")
        doc = _read("CONTRIBUTING.md")
        self.assertEqual([c for c in cmds if f"python3 {c}" not in doc], [],
                         "CI commands missing from CONTRIBUTING.md's local-checks block")


if __name__ == "__main__":
    unittest.main(verbosity=2)
