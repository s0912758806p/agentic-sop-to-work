# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""sopkit.config is the single SOPKIT_* reader, and it reads at CALL time.

Before v1.11.0 SOPKIT_ROOT / SOPKIT_SCHEMA_DIR were frozen at import: setting them after
the first `import kit` did nothing. These tests set the env AFTER importing."""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, KIT)  # kit root → sopkit
from sopkit import config, kit, schema  # noqa: E402


class CallTime(unittest.TestCase):
    def test_kit_root_follows_env_after_import(self):
        self.assertEqual(kit.kit_path("x"), os.path.join(KIT, "x"))
        with mock.patch.dict(os.environ, {"SOPKIT_ROOT": "/elsewhere"}):
            self.assertEqual(kit.kit_path("x"), os.path.join("/elsewhere", "x"))
            self.assertEqual(kit.KIT_ROOT, "/elsewhere")
        self.assertEqual(kit.KIT_ROOT, KIT)

    def test_schema_dir_follows_env_after_import(self):
        with mock.patch.dict(os.environ, {"SOPKIT_SCHEMA_DIR": "/s"}):
            self.assertEqual(config.schema_dir(), "/s")
            self.assertEqual(schema.DEFAULT_DIR, "/s")
        with mock.patch.dict(os.environ, {"SOPKIT_ROOT": "/r"}):
            os.environ.pop("SOPKIT_SCHEMA_DIR", None)
            self.assertEqual(config.schema_dir(), os.path.join("/r", "workflow", "schemas"))

    def test_defaults_and_overrides(self):
        knobs = {"max_fix_retries": ("SOPKIT_MAX_FIX_RETRIES", 3, "5", 5),
                 "stall_window": ("SOPKIT_STALL_WINDOW", 2, "0", 0),
                 "keep_runs": ("SOPKIT_STATE_KEEP_RUNS", 20, "7", 7),
                 "keep_log": ("SOPKIT_STATE_KEEP_LOG", 200, "60", 60),
                 "health_slowdown_factor": ("SOPKIT_HEALTH_SLOWDOWN_FACTOR", 2.0, "3.5", 3.5),
                 "health_flaky_window": ("SOPKIT_HEALTH_FLAKY_WINDOW", 10, "4", 4)}
        clean = {k: v for k, v in os.environ.items() if not k.startswith("SOPKIT_")}
        for fn, (env, default, raw, want) in knobs.items():
            with mock.patch.dict(os.environ, clean, clear=True):
                self.assertEqual(getattr(config, fn)(), default, fn)
                os.environ[env] = raw
                self.assertEqual(getattr(config, fn)(), want, fn)

    def test_config_is_the_only_reader(self):
        """No other engine file reads a SOPKIT_* var from os.environ directly."""
        offenders = []
        for dp, dns, fns in os.walk(KIT):
            dns[:] = [d for d in dns if d not in ("__pycache__", "runs", "tests", "golden")]
            for fn in fns:
                p = os.path.join(dp, fn)
                if not fn.endswith(".py") or p == config.__file__:
                    continue
                with open(p, encoding="utf-8") as f:
                    src = f.read()
                if "environ" in src and "SOPKIT_" in src.split("environ", 1)[1][:80]:
                    offenders.append(os.path.relpath(p, KIT))
        self.assertEqual(offenders, [])



def _clean_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("SOPKIT_", "CLAUDE_PLUGIN_OPTION_", "CLAUDE_PLUGIN_DATA"))}
    env.update(extra)
    return mock.patch.dict(os.environ, env, clear=True)


class UserConfigPrecedence(unittest.TestCase):
    """env SOPKIT_* > plugin userConfig (CLAUDE_PLUGIN_OPTION_*) > default."""

    def test_option_used_when_no_env(self):
        with _clean_env(CLAUDE_PLUGIN_OPTION_MAX_FIX_RETRIES="5", CLAUDE_PLUGIN_OPTION_STALL_WINDOW="0",
                        CLAUDE_PLUGIN_OPTION_KEEP_RUNS="9"):
            self.assertEqual((config.max_fix_retries(), config.stall_window(), config.keep_runs()), (5, 0, 9))

    def test_env_beats_option(self):
        with _clean_env(SOPKIT_MAX_FIX_RETRIES="1", CLAUDE_PLUGIN_OPTION_MAX_FIX_RETRIES="5"):
            self.assertEqual(config.max_fix_retries(), 1)

    def test_unsubstituted_or_bad_option_is_ignored(self):
        # bootstrap-generated project commands carry the literal ${user_config.x}
        for raw in ("${user_config.max_fix_retries}", "", "abc"):
            with _clean_env(CLAUDE_PLUGIN_OPTION_MAX_FIX_RETRIES=raw):
                self.assertEqual(config.max_fix_retries(), 3, raw)

    def test_numeric_option_as_float_text(self):
        with _clean_env(CLAUDE_PLUGIN_OPTION_KEEP_RUNS="12.0"):
            self.assertEqual(config.keep_runs(), 12)


class RunsBase(unittest.TestCase):
    """--out-base > $CLAUDE_PLUGIN_DATA/runs (kit inside an installed plugin) > <kit>/runs."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.plugin_kit = os.path.join(self.tmp, "plugin", "kit")
        os.makedirs(os.path.join(self.tmp, "plugin", ".claude-plugin"))
        open(os.path.join(self.tmp, "plugin", ".claude-plugin", "plugin.json"), "w").close()
        os.makedirs(self.plugin_kit)
        self.project_kit = os.path.join(self.tmp, "proj", "agentic-sop-kit")
        os.makedirs(self.project_kit)

    def test_out_base_wins(self):
        with _clean_env(SOPKIT_ROOT=self.plugin_kit, CLAUDE_PLUGIN_DATA="/data"):
            self.assertEqual(config.runs_base("/explicit"), ("/explicit", None))

    def test_plugin_data_when_installed(self):
        with _clean_env(SOPKIT_ROOT=self.plugin_kit, CLAUDE_PLUGIN_DATA="/data"):
            self.assertEqual(config.runs_base(None), (os.path.join("/data", "runs"), None))

    def test_legacy_in_plugin_cache_warns(self):
        with _clean_env(SOPKIT_ROOT=self.plugin_kit):
            base, notice = config.runs_base(None)
            self.assertEqual(base, os.path.join(self.plugin_kit, "runs"))
            self.assertIn("deprecated", notice.lower())

    def test_project_kit_keeps_its_runs_dir_even_with_plugin_data(self):
        with _clean_env(SOPKIT_ROOT=self.project_kit, CLAUDE_PLUGIN_DATA="/data"):
            self.assertEqual(config.runs_base(None), (os.path.join(self.project_kit, "runs"), None))


if __name__ == "__main__":
    unittest.main()
