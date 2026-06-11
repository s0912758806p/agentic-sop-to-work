# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Integration: per-step gate, cmd step, --allow-mutations, --plan."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = os.path.join(KIT, "workflow", "run.py")


def _write(d, name, obj):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return p


def _run(flow_path, *extra):
    return subprocess.run([sys.executable, RUN, "--flow", flow_path, *extra],
                          capture_output=True, text=True)


class GateOnStep(unittest.TestCase):
    def test_failing_gate_stops_run(self):
        with tempfile.TemporaryDirectory() as d:
            tool = os.path.join(d, "emit.py")
            with open(tool, "w", encoding="utf-8") as f:
                f.write('import json,argparse\n'
                        'a=argparse.ArgumentParser();a.add_argument("--in");a.add_argument("--out");x=a.parse_args()\n'
                        'json.dump({"schema":"t@1","produced_by":"emit","data":{"id":1},"trace":[]},open(x.out,"w"))\n')
            flow = _write(d, "flow.json", {
                "name": "gate-demo", "input_default": tool,
                "steps": [{"skill": "emit", "tool": tool, "in": "$INPUT", "out": "$RUN/a.json",
                           "gate": {"type": "schema_gate", "args": {"required": ["id", "name"]}}}]})
            r = _run(flow, "--out-base", os.path.join(d, "runs"))
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("name", r.stdout + r.stderr)


class CmdStep(unittest.TestCase):
    def test_cmd_runs_and_cmd_gate_passes(self):
        with tempfile.TemporaryDirectory() as d:
            flow = _write(d, "flow.json", {
                "name": "cmd-demo", "input_default": __file__,
                "steps": [{"cmd": sys.executable + " --version",
                           "out": "$RUN/b.json", "gate": {"type": "cmd_gate"}}]})
            r = _run(flow, "--out-base", os.path.join(d, "runs"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_mutating_cmd_blocked_without_flag(self):
        with tempfile.TemporaryDirectory() as d:
            flow = _write(d, "flow.json", {
                "name": "mut", "input_default": __file__,
                "steps": [{"cmd": sys.executable + " --version", "mutates": True, "out": "$RUN/m.json"}]})
            r = _run(flow, "--out-base", os.path.join(d, "runs"))
            self.assertEqual(r.returncode, 2)
            self.assertIn("allow-mutations", r.stdout + r.stderr)
            r2 = _run(flow, "--out-base", os.path.join(d, "runs2"), "--allow-mutations")
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)


class Plan(unittest.TestCase):
    def test_plan_lists_without_executing(self):
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "ran.txt")
            script = os.path.join(d, "mk.py")
            with open(script, "w", encoding="utf-8") as f:
                f.write("open(r%r, 'w').write('x')\n" % marker)
            flow = _write(d, "flow.json", {
                "name": "plan-demo", "input_default": __file__,
                "steps": [{"cmd": sys.executable + " " + script, "mutates": True, "out": "$RUN/p.json"}]})
            r = _run(flow, "--plan")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("MUTATES", r.stdout)
            self.assertFalse(os.path.exists(marker), "--plan must not execute anything")


    def test_plan_shows_branch_and_map(self):
        with tempfile.TemporaryDirectory() as d:
            t = os.path.join(d, "t.py")
            with open(t, "w", encoding="utf-8") as f:
                f.write("import json,argparse\n"
                        "a=argparse.ArgumentParser();a.add_argument('--in');a.add_argument('--out');x=a.parse_args()\n"
                        "json.dump({'schema':'t@1','produced_by':'t','data':{'flag':'x','items':[1]},'trace':[]},open(x.out,'w'))\n")
            flow = _write(d, "flow.json", {
                "name": "pbm", "input_default": t, "steps": [
                    {"skill": "c", "tool": t, "in": "$INPUT", "out": "$RUN/c.json"},
                    {"branch": "$RUN/c.json", "cases": [{"default": True, "goto": "m"}]},
                    {"skill": "m", "tool": t, "map_over": "items", "in": "$RUN/c.json", "out": "$RUN/m.json"}]})
            r = _run(flow, "--plan")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("branch", r.stdout)
            self.assertIn("map_over", r.stdout)
            self.assertNotIn("tool: None", r.stdout)   # a branch step must NOT print "tool: None"

    def test_plan_flags_bad_goto(self):
        with tempfile.TemporaryDirectory() as d:
            t = os.path.join(d, "t.py")
            with open(t, "w", encoding="utf-8") as f:
                f.write("import json,argparse\n"
                        "a=argparse.ArgumentParser();a.add_argument('--in');a.add_argument('--out');x=a.parse_args()\n"
                        "json.dump({'schema':'t@1','produced_by':'t','data':{},'trace':[]},open(x.out,'w'))\n")
            flow = _write(d, "flow.json", {
                "name": "pbad", "input_default": t, "steps": [
                    {"skill": "a", "tool": t, "in": "$INPUT", "out": "$RUN/a.json"},
                    {"branch": "$RUN/a.json", "cases": [{"default": True, "goto": "nope"}]}]})
            r = _run(flow, "--plan")
            self.assertEqual(r.returncode, 2)
            self.assertIn("goto", (r.stdout + r.stderr).lower())

    def test_plan_flags_backward_goto(self):
        with tempfile.TemporaryDirectory() as d:
            t = os.path.join(d, "t.py")
            with open(t, "w", encoding="utf-8") as f:
                f.write("import json,argparse\n"
                        "a=argparse.ArgumentParser();a.add_argument('--in');a.add_argument('--out');x=a.parse_args()\n"
                        "json.dump({'schema':'t@1','produced_by':'t','data':{},'trace':[]},open(x.out,'w'))\n")
            flow = _write(d, "flow.json", {
                "name": "pback", "input_default": t, "steps": [
                    {"skill": "a", "tool": t, "in": "$INPUT", "out": "$RUN/a.json"},
                    {"branch": "$RUN/a.json", "cases": [{"default": True, "goto": "a"}]}]})
            r = _run(flow, "--plan")
            self.assertEqual(r.returncode, 2)
            self.assertIn("forward", (r.stdout + r.stderr).lower())

    def test_plan_duplicate_name_without_goto_is_ok(self):
        with tempfile.TemporaryDirectory() as d:
            t = os.path.join(d, "t.py")
            with open(t, "w", encoding="utf-8") as f:
                f.write("import json,argparse\n"
                        "a=argparse.ArgumentParser();a.add_argument('--in');a.add_argument('--out');x=a.parse_args()\n"
                        "json.dump({'schema':'t@1','produced_by':'t','data':{},'trace':[]},open(x.out,'w'))\n")
            flow = _write(d, "flow.json", {
                "name": "pdup", "input_default": t, "steps": [
                    {"skill": "a", "tool": t, "in": "$INPUT", "out": "$RUN/a.json"},
                    {"skill": "a", "tool": t, "in": "$RUN/a.json", "out": "$RUN/a2.json"}]})
            r = _run(flow, "--plan")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)  # branchless dup → not a problem, matches runtime


if __name__ == "__main__":
    unittest.main()
