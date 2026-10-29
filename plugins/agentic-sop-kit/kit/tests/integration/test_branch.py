# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Integration: forward-only conditional branching in the engine."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = os.path.join(KIT, "workflow", "run.py")


def _emit_tool(d, name, data):
    p = os.path.join(d, name + ".py")
    with open(p, "w", encoding="utf-8") as f:
        f.write("import json,argparse\n"
                "a=argparse.ArgumentParser();a.add_argument('--in');a.add_argument('--out');x=a.parse_args()\n"
                "json.dump({'schema':'t@1','produced_by':%r,'data':%r,'trace':[]}, open(x.out,'w'))\n"
                % (name, data))
    return p


def _run(flow_path, *extra):
    return subprocess.run([sys.executable, RUN, "--flow", flow_path, *extra], capture_output=True, text=True)


class Branch(unittest.TestCase):
    def _flow(self, d, severity):
        classify = _emit_tool(d, "classify", {"severity": severity})
        investigate = _emit_tool(d, "investigate", {"path": "investigate"})
        release = _emit_tool(d, "release", {"path": "release"})
        return {
            "name": "branch-demo", "input_default": classify,
            "steps": [
                {"skill": "classify", "tool": classify, "in": "$INPUT", "out": "$RUN/c.json"},
                {"branch": "$RUN/c.json", "cases": [
                    {"when": {"path": "severity", "op": "==", "value": "OOS"}, "goto": "investigate"},
                    {"default": True, "goto": "release"}]},
                {"skill": "investigate", "tool": investigate, "in": "$RUN/c.json", "out": "$RUN/i.json"},
                {"skill": "release", "tool": release, "in": "$RUN/c.json", "out": "$RUN/r.json"},
            ]}

    def test_routes_to_investigate(self):
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "f.json")
            with open(fp, "w") as fh:
                json.dump(self._flow(d, "OOS"), fh)
            r = _run(fp, "--out-base", os.path.join(d, "runs"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("investigate", r.stdout)

    def test_routes_to_release_via_default(self):
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "f.json")
            with open(fp, "w") as fh:
                json.dump(self._flow(d, "OK"), fh)
            r = _run(fp, "--out-base", os.path.join(d, "runs"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("release", r.stdout)

    def test_backward_goto_fails(self):
        with tempfile.TemporaryDirectory() as d:
            t = _emit_tool(d, "a", {"x": 1})
            flow = {"name": "bad", "input_default": t, "steps": [
                {"skill": "a", "tool": t, "in": "$INPUT", "out": "$RUN/a.json"},
                {"branch": "$RUN/a.json", "cases": [{"default": True, "goto": "a"}]}]}
            fp = os.path.join(d, "f.json")
            with open(fp, "w") as fh:
                json.dump(flow, fh)
            r = _run(fp, "--out-base", os.path.join(d, "runs"))
            self.assertEqual(r.returncode, 2)
            self.assertIn("forward", (r.stdout + r.stderr).lower())

    def test_unknown_goto_fails(self):
        with tempfile.TemporaryDirectory() as d:
            t = _emit_tool(d, "a", {"x": 1})
            flow = {"name": "bad2", "input_default": t, "steps": [
                {"skill": "a", "tool": t, "in": "$INPUT", "out": "$RUN/a.json"},
                {"branch": "$RUN/a.json", "cases": [{"default": True, "goto": "nope"}]}]}
            fp = os.path.join(d, "f.json")
            with open(fp, "w") as fh:
                json.dump(flow, fh)
            r = _run(fp, "--out-base", os.path.join(d, "runs"))
            self.assertEqual(r.returncode, 2)
            self.assertIn("nope", r.stdout + r.stderr)


    def test_missing_branch_artifact_is_a_hard_failure(self):
        """A branch reading an artifact that does not exist must FAIL, not route on empty data
        through `default` (v1.10.0 silently took the default path)."""
        with tempfile.TemporaryDirectory() as d:
            t = _emit_tool(d, "a", {"x": 1})
            b = _emit_tool(d, "b", {"y": 2})
            flow = {"name": "missing-art", "input_default": t, "steps": [
                {"skill": "a", "tool": t, "in": "$INPUT", "out": "$RUN/a.json"},
                {"branch": "$RUN/nope.json", "cases": [{"default": True, "goto": "b"}]},
                {"skill": "b", "tool": b, "in": "$RUN/a.json", "out": "$RUN/b.json"}]}
            fp = os.path.join(d, "f.json")
            with open(fp, "w") as fh:
                json.dump(flow, fh)
            runs = os.path.join(d, "runs")
            r = _run(fp, "--out-base", runs, "--run-id", "m")
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            with open(os.path.join(runs, "m", "run_manifest.json"), encoding="utf-8") as fh:
                m = json.load(fh)
            self.assertEqual(m["state"], "FAILED")
            self.assertIn("nope.json", m["failure"]["artifact"])
            self.assertFalse(os.path.exists(os.path.join(runs, "m", "b.json")), "default must not run")


if __name__ == "__main__":
    unittest.main()
