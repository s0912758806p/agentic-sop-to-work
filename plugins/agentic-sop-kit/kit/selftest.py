# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""agentic-sop-kit 自我測試（stdlib unittest；可在任何專案 `python3 selftest.py` 跑）。

涵蓋驗收 (a)(c) + 對抗驗證找到的修正：
  - 範例流程跑通；check_deps 綠。
  - extract 不得靜默丟資料：擴充數值文法（千分位/科學記號/帶單位）；含數字卻無法解析 → fail-loud（預設 exit≠0）。
  - check_deps：以 AST 靜態讀 DEPS（skill 頂層 import 缺套件也不會 raw traceback）、且依 flow.json 涵蓋使用者新增的 skill。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(args, **kw):
    return subprocess.run([PY] + args, capture_output=True, text=True, **kw)


def fresh_copy():
    d = tempfile.mkdtemp()
    dst = os.path.join(d, "agentic-sop-kit")
    shutil.copytree(KIT, dst, ignore=shutil.ignore_patterns("runs", "__pycache__"))
    return d, dst


class Kit(unittest.TestCase):
    def test_a_example_runs_and_check_deps_green(self):
        self.assertEqual(run([os.path.join(KIT, "check_deps.py")]).returncode, 0)
        d, k = fresh_copy()
        try:
            r = run([os.path.join(k, "workflow", "run.py")])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            runs = [os.path.join(k, "runs", x) for x in os.listdir(os.path.join(k, "runs"))]
            rep = os.path.join(runs[0], "report.md")
            self.assertTrue(os.path.exists(rep))
            self.assertIn("DRAFT", open(rep, encoding="utf-8").read())
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_extract_broadened_grammar(self):
        d, k = fresh_copy()
        try:
            inp = os.path.join(d, "in.txt")
            open(inp, "w").write("yield: 1,234\nconc: 1.2e3\nweight: 250 mg\n")
            out = os.path.join(d, "a.json")
            r = run([os.path.join(k, "skills", "extract", "tool.py"), "--in", inp, "--out", out])
            self.assertEqual(r.returncode, 0, r.stderr)
            vals = sorted(x["value"] for x in json.load(open(out))["data"]["readings"])
            self.assertEqual(vals, [250.0, 1200.0, 1234.0], vals)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_extract_failloud_on_unparsed_digit_line(self):
        d, k = fresh_copy()
        try:
            inp = os.path.join(d, "in.txt")
            # 含數字卻無法解析（純文字 note 行不算；此行有數字但畸形）
            open(inp, "w").write("ok: 5\nbroken: v1.2.3.4-rc5\n")
            out = os.path.join(d, "a.json")
            r = run([os.path.join(k, "skills", "extract", "tool.py"), "--in", inp, "--out", out])
            self.assertNotEqual(r.returncode, 0, "含數字無法解析的行應 fail-loud，不可靜默 exit0\n" + r.stdout)
            self.assertIn("broken", (r.stderr + r.stdout))
            # --allow-unparsed 則記錄 skipped 並放行
            r2 = run([os.path.join(k, "skills", "extract", "tool.py"), "--in", inp, "--out", out, "--allow-unparsed"])
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertTrue(json.load(open(out))["data"]["skipped"], "skipped 應被記錄")
        finally:
            shutil.rmtree(d, ignore_errors=True)
    # NOTE: 純文字行（無數字）仍應安靜忽略 → 範例的 'note:' 行不應觸發 fail-loud（由 test_a 覆蓋）。

    def test_check_deps_no_raw_traceback_on_bad_import(self):
        d, k = fresh_copy()
        try:
            bad = os.path.join(k, "skills", "badimport")
            os.makedirs(bad)
            open(os.path.join(bad, "tool.py"), "w").write(
                "import sys\nimport definitely_absent_pkg_zzz\n"
                'DEPS = [{"kind": "module", "name": "definitely_absent_pkg_zzz", "hint": "pip install x"}]\n')
            # 把 badimport 加進 flow.json
            fp = os.path.join(k, "workflow", "flow.json")
            flow = json.load(open(fp))
            flow["steps"].append({"skill": "badimport", "tool": "skills/badimport/tool.py", "in": "$RUN/a.readings.json", "out": "$RUN/z.json"})
            json.dump(flow, open(fp, "w"))
            r = run([os.path.join(k, "check_deps.py")])
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertNotIn("Traceback", r.stdout + r.stderr, "不可吐 raw traceback")
            self.assertIn("definitely_absent_pkg_zzz", r.stdout)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_check_deps_covers_flow_added_skill(self):
        d, k = fresh_copy()
        try:
            new = os.path.join(k, "skills", "needexe")
            os.makedirs(new)
            open(os.path.join(new, "tool.py"), "w").write(
                'DEPS = [{"kind": "exe", "name": "totally_absent_exe_zzz"}]\n')
            fp = os.path.join(k, "workflow", "flow.json")
            flow = json.load(open(fp))
            flow["steps"].append({"skill": "needexe", "tool": "skills/needexe/tool.py", "in": "$RUN/a.readings.json", "out": "$RUN/z.json"})
            json.dump(flow, open(fp, "w"))
            r = run([os.path.join(k, "check_deps.py")])
            self.assertEqual(r.returncode, 1, "新增 skill 的缺依賴應被涵蓋（依 flow.json）\n" + r.stdout)
            self.assertIn("totally_absent_exe_zzz", r.stdout)
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
