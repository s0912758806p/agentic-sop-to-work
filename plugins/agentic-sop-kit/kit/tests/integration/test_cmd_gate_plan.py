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


if __name__ == "__main__":
    unittest.main()
