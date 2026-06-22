# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Meta-test: verify.py runtime-health gate (H1 coverage -> exit 3, ratchet, --rebaseline, advisory non-gating).
Runs verify.py on a DISPOSABLE kit copy (mirrors test_stop_hook.py). NOT registered (would recurse)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EXCLUDE = {"runs", "__pycache__", ".git", ".pytest_cache"}
_EXCLUDE_RELS = {"tests/.verify_state.json", "tests/.retry_count",
                 "tests/regression_log.jsonl", "tests/.health_baseline.json"}


def _copy_kit(dst):
    def ignore(d, names):
        skip = {n for n in names if n in _EXCLUDE}
        for n in names:
            rel = os.path.relpath(os.path.join(d, n), KIT).replace(os.sep, "/")
            if rel in _EXCLUDE_RELS:
                skip.add(n)
        return skip
    shutil.copytree(KIT, dst, ignore=ignore)


class HealthGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.kit = os.path.join(self.tmp, "kit")
        _copy_kit(self.kit)
        self.verify = os.path.join(self.kit, "tests", "verify.py")
        self.reg = os.path.join(self.kit, "tests", "registry.json")
        r0 = self._verify("--all")  # establish clean passing baseline
        self.assertEqual(r0.returncode, 0, "setUp baseline run failed:\n" + r0.stdout + r0.stderr)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _verify(self, *args):
        return subprocess.run([sys.executable, self.verify, *args],
                              cwd=self.kit, capture_output=True, text=True)

    def _shrink_registry(self):
        with open(self.reg, encoding="utf-8") as f:
            reg = json.load(f)
        reg["integration"]["tests"].pop()  # drop one registered test -> coverage shrinks
        with open(self.reg, "w", encoding="utf-8") as f:
            json.dump(reg, f, ensure_ascii=False)

    def test_coverage_shrink_returns_3(self):
        self._shrink_registry()
        r = self._verify("--all")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("HEALTH(hard)", r.stderr)
        self.assertIn("rebaseline", r.stderr)

    def test_rebaseline_clears_gate(self):
        self._shrink_registry()
        self.assertEqual(self._verify("--all").returncode, 3)
        self.assertEqual(self._verify("--rebaseline").returncode, 0)
        self.assertEqual(self._verify("--all").returncode, 0)  # lower baseline now accepted

    def test_healthy_returns_0(self):
        self.assertEqual(self._verify("--all").returncode, 0)

    def test_advisory_does_not_gate(self):
        log = os.path.join(self.kit, "tests", "regression_log.jsonl")
        flaky = [{"trigger": "all", "metrics": {"total_seconds": 1.0},
                  "unit": [], "integration": [{"test": "tests/integration/test_flow.py", "passed": p}]}
                 for p in (True, False, True, False)]
        with open(log, "a", encoding="utf-8") as f:
            for e in flaky:
                f.write(json.dumps(e) + "\n")
        r = self._verify("--all")
        self.assertEqual(r.returncode, 0, "advisory must NOT gate\n" + r.stdout + r.stderr)
        self.assertIn("HEALTH(advisory)", r.stdout)


    def test_log_rotation_keeps_last_M(self):
        log = os.path.join(self.kit, "tests", "regression_log.jsonl")
        with open(log, "a", encoding="utf-8") as f:
            for _ in range(100):
                f.write(json.dumps({"trigger": "all", "metrics": {"total_seconds": 1.0},
                                    "unit": [], "integration": []}) + "\n")
        env = dict(os.environ, SOPKIT_STATE_KEEP_LOG="60")  # > log_floor 50
        r = subprocess.run([sys.executable, self.verify, "--all"], cwd=self.kit, env=env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(log, encoding="utf-8") as f:
            n = sum(1 for _ in f)
        self.assertLessEqual(n, 60, "log should be rotated to keep <= 60")


if __name__ == "__main__":
    unittest.main(verbosity=2)
