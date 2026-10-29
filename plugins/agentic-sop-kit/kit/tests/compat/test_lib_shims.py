# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Compat (v1.11.0 zero-break promise): a v1.10-style custom tool — the kind bootstrap put in
users' projects, doing `sys.path.insert(..., "lib"); import kit` — must keep working
unchanged through the kit/lib/ shims, and its stderr (copied into the manifest) must stay
clean under default warning filters. The DeprecationWarning is real but opt-in visible.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, KIT)  # kit root → sopkit
from sopkit.kit import copy_kit  # noqa: E402

# Byte-for-byte the v1.10.0 templates/skill_template/tool.py.tmpl import idiom.
V110_TOOL = '''import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import kit  # noqa: E402
import gates  # noqa: E402
from loop import progress  # noqa: E402

DEPS = [{"kind": "python", "min": "3.8"}]
WHO = "legacy"


def run(inp, out):
    up = kit.read_artifact(inp)
    assert gates.run_gate("schema_gate", up, {"required": ["id"]})[0]
    assert len(progress.progress_signature({"step": "x"})) == 16
    kit.write_artifact(kit.artifact("legacy@1", WHO, {"id": up["data"]["id"], "root": kit.KIT_ROOT}), out)


if __name__ == "__main__":
    kit.skill_main(DEPS, WHO, run)
'''


class V110CustomTool(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.kit = os.path.join(self.tmp, "kit")           # disposable copy: never touch the real tree
        copy_kit(KIT, self.kit)
        self.skill = os.path.join(self.kit, "skills", "zz_legacy_compat")
        os.makedirs(self.skill)
        with open(os.path.join(self.skill, "tool.py"), "w", encoding="utf-8") as f:
            f.write(V110_TOOL)
        self.inp = os.path.join(self.tmp, "in.json")
        with open(self.inp, "w", encoding="utf-8") as f:
            json.dump({"schema": "x@1", "produced_by": "t", "data": {"id": 7}, "trace": []}, f)

    def _tool(self, *py):
        out = os.path.join(self.tmp, "out.json")
        r = subprocess.run([sys.executable, *py, os.path.join(self.skill, "tool.py"),
                            "--in", self.inp, "--out", out], capture_output=True, text=True)
        return r, out

    def test_runs_unchanged_with_clean_stderr(self):
        r, out = self._tool()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "", "default filters must keep the shim silent (stderr lands in manifests)")
        with open(out, encoding="utf-8") as f:
            art = json.load(f)
        self.assertEqual(art["data"], {"id": 7, "root": self.kit})

    def test_deprecation_warning_is_emitted(self):
        r, _ = self._tool("-W", "default::DeprecationWarning")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("DeprecationWarning", r.stderr)
        self.assertIn("from sopkit import kit", r.stderr)

    def test_runs_inside_a_flow(self):
        flow = os.path.join(self.tmp, "f.json")
        with open(flow, "w", encoding="utf-8") as f:
            json.dump({"name": "compat", "input_default": self.inp, "steps": [
                {"skill": "zz_legacy_compat", "tool": "skills/zz_legacy_compat/tool.py",
                 "in": "$INPUT", "out": "$RUN/o.json",
                 "gate": {"type": "schema_gate", "args": {"required": ["id"]}}}]}, f)
        r = subprocess.run([sys.executable, os.path.join(self.kit, "workflow", "run.py"), "--flow", flow, "--out-base", self.tmp, "--run-id", "c"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class ShimIsTheSameModule(unittest.TestCase):
    def test_import_kit_is_sopkit_kit(self):
        code = ("import sys, warnings; warnings.simplefilter('error')\n"
                f"sys.path.insert(0, {os.path.join(KIT, 'lib')!r})\n"
                "try:\n    import kit\nexcept DeprecationWarning as e:\n    print('WARNED', e); raise SystemExit(0)\n"
                "raise SystemExit('no warning')\n")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("WARNED", r.stdout)

        code = (f"import sys, warnings; warnings.simplefilter('ignore'); sys.path.insert(0, {os.path.join(KIT, 'lib')!r})\n"
                "import kit, graph, loop\nfrom loop import state\nimport sopkit.kit, sopkit.graph, sopkit.loop.state\n"
                "assert kit is sopkit.kit and graph is sopkit.graph and state is sopkit.loop.state\n"
                "assert graph._kind is graph.kind and graph._valid_bound is graph.valid_bound\n")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
