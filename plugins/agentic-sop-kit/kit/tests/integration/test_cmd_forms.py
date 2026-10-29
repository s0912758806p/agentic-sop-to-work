# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""cmd steps: $INPUT / $RUN are substituted (shell-quoted for string cmds, verbatim per
argv element for list cmds), and a list cmd runs WITHOUT a shell."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = os.path.join(KIT, "workflow", "run.py")
PY = sys.executable


def _run(d, steps):
    inp = os.path.join(d, "in put.txt")            # a space: the quoting case
    with open(inp, "w", encoding="utf-8") as f:
        f.write("x")
    fp = os.path.join(d, "f.json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump({"name": "cmd-forms", "input_default": inp, "steps": steps}, f)
    base = os.path.join(d, "runs with space")
    r = subprocess.run([PY, RUN, "--flow", fp, "--out-base", base, "--run-id", "c"],
                       capture_output=True, text=True)
    return r, os.path.join(base, "c")


def _art(run_dir, name):
    with open(os.path.join(run_dir, name), encoding="utf-8") as f:
        return json.load(f)["data"]


class CmdForms(unittest.TestCase):
    def test_string_cmd_quotes_substituted_paths(self):
        with tempfile.TemporaryDirectory() as d:
            probe = "import sys,os; print(os.path.exists(sys.argv[1]), os.path.isdir(sys.argv[2]))"
            r, run_dir = _run(d, [{"cmd": f'"{PY}" -c "{probe}" $INPUT $RUN', "out": "$RUN/o.json",
                                   "gate": {"type": "cmd_gate"}}])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(_art(run_dir, "o.json")["stdout"].strip(), "True True")

    def test_list_cmd_runs_without_shell(self):
        with tempfile.TemporaryDirectory() as d:
            probe = "import sys; print(repr(sys.argv[1:]))"
            r, run_dir = _run(d, [{"cmd": [PY, "-c", probe, "$INPUT", "a b;echo pwned", "$(id)"],
                                   "out": "$RUN/o.json", "gate": {"type": "cmd_gate"}}])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            args = _art(run_dir, "o.json")["stdout"].strip()
            self.assertIn("in put.txt", args)
            self.assertIn("'a b;echo pwned', '$(id)'", args, "a list cmd must not go through a shell")

    def test_list_cmd_plan_and_manifest_label(self):
        with tempfile.TemporaryDirectory() as d:
            r, run_dir = _run(d, [{"cmd": [PY, "--version"], "out": "$RUN/o.json"}])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with open(os.path.join(run_dir, "run_manifest.json"), encoding="utf-8") as f:
                self.assertTrue(json.load(f)["steps"][0]["skill"].startswith("cmd: "))


if __name__ == "__main__":
    unittest.main()
