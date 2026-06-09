"""Meta-測試：驗證 verify.py 自身的行為（建置/開發期跑，不登記入 registry——避免 verify 套 verify 遞迴）。
在 KIT 的「拋棄式複本」上操作，絕不碰真實 kit 狀態。
涵蓋：--all 建基線 → 無變更略過 → 注入 bug 得 exit2 並寫 fail 紀錄 → 修好得 exit0 → 未登記 skill 得 exit3。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXCLUDE = {"runs", "__pycache__", ".git", ".pytest_cache"}
_EXCLUDE_RELS = {"tests/.verify_state.json", "tests/.retry_count", "tests/regression_log.jsonl"}


def _copy_kit(dst):
    def ignore(d, names):
        skip = set(n for n in names if n in _EXCLUDE)
        for n in names:
            rel = os.path.relpath(os.path.join(d, n), KIT).replace(os.sep, "/")
            if rel in _EXCLUDE_RELS:
                skip.add(n)
        return skip
    shutil.copytree(KIT, dst, ignore=ignore)


class TestVerify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.kit = os.path.join(self.tmp, "kit")
        _copy_kit(self.kit)
        self.verify = os.path.join(self.kit, "tests", "verify.py")
        self.log = os.path.join(self.kit, "tests", "regression_log.jsonl")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *extra):
        return subprocess.run([sys.executable, self.verify, *extra], cwd=self.kit,
                              capture_output=True, text=True)

    def _log_entries(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as f:
            return [json.loads(ln) for ln in f if ln.strip()]

    @staticmethod
    def _read(p):
        with open(p, encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _write(p, s):
        with open(p, "w", encoding="utf-8") as f:
            f.write(s)

    def test_full_lifecycle(self):
        # 1) --all 建基線
        r = self._run("--all")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(self._log_entries()), 1)
        self.assertEqual(self._log_entries()[-1]["verdict"], "pass")

        # 2) 無變更 → 略過，不新增紀錄
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("無變更", r.stdout)
        self.assertEqual(len(self._log_entries()), 1, "略過不應寫紀錄")

        # 3) 注入 bug：停用 extract 的 fail-loud → test_extract 失敗
        tp = os.path.join(self.kit, "skills", "extract", "tool.py")
        src = self._read(tp)
        self.assertIn("raise SystemExit(3)", src)
        self._write(tp, src.replace("raise SystemExit(3)", "pass  # BROKEN", 1))
        r = self._run()
        self.assertEqual(r.returncode, 2, "有測試失敗應 exit 2")
        self.assertIn("FAIL", r.stdout)
        entries = self._log_entries()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[-1]["verdict"], "fail")
        self.assertIn("extract", entries[-1]["affected_skills"])
        # 失敗時不更新快照 → 立刻再跑（未修）仍偵測為有變更並再次失敗（不會被當成無變更而放行）
        r2 = self._run()
        self.assertEqual(r2.returncode, 2, "未修好前不得被當成『無變更』而略過")

        # 4) 修好（還原 fail-loud；非位元組級相同——真實修正通常有差異 → 觸發重跑）→ exit 0、寫 pass 紀錄
        self._write(tp, src + "\n# fixed: fail-loud restored\n")
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._log_entries()[-1]["verdict"], "pass")

        # 5) flow 新增未登記測試的 skill → fail-loud exit 3
        fp = os.path.join(self.kit, "workflow", "flow.json")
        flow = json.loads(self._read(fp))
        flow["steps"].append({"skill": "ghost", "tool": "skills/ghost/tool.py", "in": "$RUN/x", "out": "$RUN/y"})
        self._write(fp, json.dumps(flow, ensure_ascii=False))
        r = self._run()
        self.assertEqual(r.returncode, 3, "未登記測試的 skill 應 fail-loud exit 3")
        self.assertIn("ghost", r.stderr)

    def _reg_path(self):
        return os.path.join(self.kit, "tests", "registry.json")

    def test_empty_skill_tests_fails(self):
        # skill 登記了卻空著 tests → 空洞登錄 → fail-loud
        reg = json.loads(self._read(self._reg_path()))
        reg["skills"]["report"]["tests"] = []
        self._write(self._reg_path(), json.dumps(reg, ensure_ascii=False))
        r = self._run()
        self.assertEqual(r.returncode, 3, "skill 無任何單元測試應 exit 3")
        self.assertIn("report", r.stderr)

    def test_empty_integration_tests_fails(self):
        reg = json.loads(self._read(self._reg_path()))
        reg["integration"]["tests"] = []
        self._write(self._reg_path(), json.dumps(reg, ensure_ascii=False))
        r = self._run()
        self.assertEqual(r.returncode, 3, "整合層缺測試應 exit 3")
        self.assertIn("整合", r.stderr)

    def test_watch_change_forces_all_units(self):
        # 動到共用層（lib/，在 registry.integration.watch）→ 受影響=全部 skill（config-driven）
        self.assertEqual(self._run("--all").returncode, 0)
        kp = os.path.join(self.kit, "lib", "kit.py")
        self._write(kp, self._read(kp) + "\n# shared-layer change\n")
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        last = self._log_entries()[-1]
        self.assertEqual(sorted(last["affected_skills"]), ["compute", "extract", "report"],
                         "共用層變動應觸發全部 skill 單元測試")
        self.assertEqual(len(last["unit"]), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
