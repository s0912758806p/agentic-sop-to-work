# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Integration: sequential map_over (fan-out) in the engine."""
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


def _double_tool(d):
    p = os.path.join(d, "double.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write("import json,argparse\n"
                "p=argparse.ArgumentParser();p.add_argument('--in',dest='inp');p.add_argument('--out');x=p.parse_args()\n"
                "with open(x.inp) as fh: art=json.load(fh)\n"
                "v=art['data']\n"
                "with open(x.out,'w') as fh: json.dump({'schema':'d@1','produced_by':'double','data':v*2,'trace':[]}, fh)\n")
    return p


def _fail_tool(d):
    p = os.path.join(d, "boom.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write("import sys\nsys.exit(1)\n")
    return p


def _run(flow_path, *extra):
    return subprocess.run([sys.executable, RUN, "--flow", flow_path, *extra], capture_output=True, text=True)


class Map(unittest.TestCase):
    def _write(self, d, flow):
        fp = os.path.join(d, "f.json")
        with open(fp, "w", encoding="utf-8") as fh:
            json.dump(flow, fh)
        return fp

    def test_map_collects(self):
        with tempfile.TemporaryDirectory() as d:
            emit = _emit_tool(d, "emit", {"items": [1, 2, 3]})
            dbl = _double_tool(d)
            flow = {"name": "map-demo", "input_default": emit, "steps": [
                {"skill": "emit", "tool": emit, "in": "$INPUT", "out": "$RUN/a.json"},
                {"skill": "dbl", "tool": dbl, "map_over": "items", "in": "$RUN/a.json", "out": "$RUN/b.json"}]}
            base = os.path.join(d, "runs")
            r = _run(self._write(d, flow), "--out-base", base, "--run-id", "t1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with open(os.path.join(base, "t1", "b.json")) as fh:
                out = json.load(fh)
            self.assertEqual(out["data"]["items"], [2, 4, 6])
            self.assertEqual(out["data"]["count"], 3)

    def test_item_failure_fails(self):
        with tempfile.TemporaryDirectory() as d:
            emit = _emit_tool(d, "emit", {"items": [1, 2]})
            boom = _fail_tool(d)
            flow = {"name": "map-fail", "input_default": emit, "steps": [
                {"skill": "emit", "tool": emit, "in": "$INPUT", "out": "$RUN/a.json"},
                {"skill": "b", "tool": boom, "map_over": "items", "in": "$RUN/a.json", "out": "$RUN/b.json"}]}
            r = _run(self._write(d, flow), "--out-base", os.path.join(d, "runs"))
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_map_over_non_list_fails(self):
        with tempfile.TemporaryDirectory() as d:
            emit = _emit_tool(d, "emit", {"items": 5})
            dbl = _double_tool(d)
            flow = {"name": "map-bad", "input_default": emit, "steps": [
                {"skill": "emit", "tool": emit, "in": "$INPUT", "out": "$RUN/a.json"},
                {"skill": "dbl", "tool": dbl, "map_over": "items", "in": "$RUN/a.json", "out": "$RUN/b.json"}]}
            r = _run(self._write(d, flow), "--out-base", os.path.join(d, "runs"))
            self.assertEqual(r.returncode, 2)
            self.assertIn("list", (r.stdout + r.stderr).lower())


if __name__ == "__main__":
    unittest.main()
