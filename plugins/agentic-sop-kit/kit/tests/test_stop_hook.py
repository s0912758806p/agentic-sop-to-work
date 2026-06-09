# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Meta-測試：Stop hook（hooks/stop_regression.py）的 block-on-fail 與 stop_hook_active+重試上限防迴圈。
在 kit 拋棄式複本上操作；以 SOPKIT_MAX_FIX_RETRIES=2 加速。不登記入 registry。"""
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
        skip = {n for n in names if n in _EXCLUDE}
        for n in names:
            rel = os.path.relpath(os.path.join(d, n), KIT).replace(os.sep, "/")
            if rel in _EXCLUDE_RELS:
                skip.add(n)
        return skip
    shutil.copytree(KIT, dst, ignore=ignore)


class TestStopHook(unittest.TestCase):
    MAX = 2

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.kit = os.path.join(self.tmp, "kit")
        _copy_kit(self.kit)
        self.hook = os.path.join(self.kit, "hooks", "stop_regression.py")
        self.count = os.path.join(self.kit, "tests", ".retry_count")
        self.extract = os.path.join(self.kit, "skills", "extract", "tool.py")
        # 建立通過基線
        subprocess.run([sys.executable, os.path.join(self.kit, "tests", "verify.py"), "--all"],
                       cwd=self.kit, capture_output=True, text=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _hook(self, stop_active):
        env = dict(os.environ, SOPKIT_MAX_FIX_RETRIES=str(self.MAX))
        return subprocess.run([sys.executable, self.hook], cwd=self.kit, env=env,
                              input=json.dumps({"stop_hook_active": stop_active,
                                                "hook_event_name": "Stop"}),
                              capture_output=True, text=True)

    def _count(self):
        try:
            with open(self.count, encoding="utf-8") as f:
                return int(f.read().strip() or "0")
        except Exception:
            return 0

    def _break(self):
        with open(self.extract, encoding="utf-8") as f:
            src = f.read()
        with open(self.extract, "w", encoding="utf-8") as f:
            f.write(src.replace("raise SystemExit(3)", "pass  # BROKEN", 1))

    def _fix(self):
        with open(self.extract, encoding="utf-8") as f:
            src = f.read()
        with open(self.extract, "w", encoding="utf-8") as f:
            f.write(src.replace("pass  # BROKEN", "raise SystemExit(3)", 1) + "\n# fixed\n")

    def test_pass_allows_stop_no_block(self):
        r = self._hook(stop_active=False)
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("block", r.stdout, "通過/無變更不應輸出 block")

    def test_fail_blocks_then_loop_guard_stops(self):
        self._break()

        # 第 1 次（全新停止 stop_active=False）：fail → block，計數=1
        r1 = self._hook(stop_active=False)
        self.assertEqual(r1.returncode, 0)
        d1 = json.loads(r1.stdout)
        self.assertEqual(d1["decision"], "block")
        self.assertIn("回歸", d1["reason"])
        self.assertIn("FAIL", d1["reason"], "block reason 應含失敗詳情供 Claude 修")
        self.assertEqual(self._count(), 1)

        # 第 2 次（hook 續跑 stop_active=True）：仍 fail → block，計數=2（達上限值）
        r2 = self._hook(stop_active=True)
        self.assertEqual(json.loads(r2.stdout)["decision"], "block")
        self.assertEqual(self._count(), 2)

        # 第 3 次（stop_active=True 且計數>=MAX）：防迴圈啟動 → 不再 block、放行、計數歸零、stderr 提示人工介入
        r3 = self._hook(stop_active=True)
        self.assertEqual(r3.returncode, 0)
        self.assertNotIn("block", r3.stdout, "達重試上限後不應再 block（否則無限循環）")
        self.assertIn("上限", r3.stderr)
        self.assertEqual(self._count(), 0)

    def test_fix_after_block_allows_stop_and_resets(self):
        self._break()
        self._hook(stop_active=False)        # block, count=1
        self.assertEqual(self._count(), 1)
        self._fix()                          # 修好（內容改變 → 觸發重跑）
        r = self._hook(stop_active=True)
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("block", r.stdout, "修好後應放行")
        self.assertEqual(self._count(), 0, "通過後重試計數應歸零")


if __name__ == "__main__":
    unittest.main(verbosity=2)
