# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""sopkit.config is the single SOPKIT_* reader, and it reads at CALL time.

Before v1.11.0 SOPKIT_ROOT / SOPKIT_SCHEMA_DIR were frozen at import: setting them after
the first `import kit` did nothing. These tests set the env AFTER importing."""
import os
import sys
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


if __name__ == "__main__":
    unittest.main()
