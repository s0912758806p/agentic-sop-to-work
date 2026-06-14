# SPDX-License-Identifier: MIT
"""Integration test: run the real hooks/stop_ack.py as a subprocess (env + stdin + stdout),
covering the opt-in gate end to end.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(PLUGIN, "hooks", "stop_ack.py")


def _run(project, stop_active=False):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=project, CLAUDE_PLUGIN_ROOT=PLUGIN)
    return subprocess.run([sys.executable, HOOK],
                          input=json.dumps({"stop_hook_active": stop_active}),
                          capture_output=True, text=True, env=env)


def _opt_in(project):
    os.makedirs(os.path.join(project, ".second-opinion"), exist_ok=True)
    open(os.path.join(project, ".second-opinion", "require_ack"), "w").close()


def _kit_run(project, rid="run_20260601_000000_zzzz"):
    os.makedirs(os.path.join(project, ".agentic-sop-runs", rid), exist_ok=True)
    return rid


def _review(project, rid, acked=False):
    d = os.path.join(project, ".second-opinion-runs", rid)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "second_opinion.json"), "w").close()
    if acked:
        open(os.path.join(d, ".ack"), "w").close()


class TestStopAckHook(unittest.TestCase):
    def test_not_opted_in_is_silent_noop(self):
        with tempfile.TemporaryDirectory() as p:
            _kit_run(p)  # a DRAFT exists, but the project did NOT opt in
            r = _run(p)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout.strip(), "")

    def test_opted_in_unreviewed_blocks(self):
        with tempfile.TemporaryDirectory() as p:
            _opt_in(p)
            _kit_run(p)
            r = _run(p)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout)["decision"], "block")

    def test_opted_in_reviewed_and_acked_allows_stop(self):
        with tempfile.TemporaryDirectory() as p:
            _opt_in(p)
            rid = _kit_run(p)
            _review(p, rid, acked=True)
            r = _run(p)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout.strip(), "")

    def test_opted_in_reviewed_not_acked_blocks_with_reason(self):
        with tempfile.TemporaryDirectory() as p:
            _opt_in(p)
            rid = _kit_run(p)
            _review(p, rid, acked=False)
            out = json.loads(_run(p).stdout)
            self.assertEqual(out["decision"], "block")
            self.assertIn("acknowledg", out["reason"].lower())


if __name__ == "__main__":
    unittest.main()
