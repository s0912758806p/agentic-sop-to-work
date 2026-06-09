"""整合測試：整條 workflow（extract→compute→report）串起來，驗證交接處資料傳遞正確 + 失敗會明確傳播。
stdlib unittest；以 subprocess 跑 workflow/run.py（真實編排層）。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = os.path.join(KIT, "workflow", "run.py")


def _run_flow(text, run_id="t"):
    base = tempfile.mkdtemp()
    inp = os.path.join(base, "input.txt")
    open(inp, "w", encoding="utf-8").write(text)
    r = subprocess.run([sys.executable, RUN, "--input", inp, "--out-base", base, "--run-id", run_id],
                       capture_output=True, text=True)
    run_dir = os.path.join(base, run_id)
    return r, run_dir


class TestFlowIntegration(unittest.TestCase):
    def test_happy_path_and_handoff(self):
        r, run_dir = _run_flow("a: 2\nb: 4\nc: 6\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        # 1) manifest：完成、待人覆核、三步皆 OK
        mani = json.load(open(os.path.join(run_dir, "run_manifest.json"), encoding="utf-8"))
        self.assertEqual(mani["state"], "OK_FOR_REVIEW")
        self.assertTrue(mani["human_review_required"])
        self.assertEqual([s["skill"] for s in mani["steps"]], ["extract", "compute", "report"])
        self.assertTrue(all(s["ok"] for s in mani["steps"]))

        # 2) 交接：extract→readings@1
        a = json.load(open(os.path.join(run_dir, "a.readings.json"), encoding="utf-8"))
        self.assertEqual(a["schema"], "readings@1")
        self.assertEqual(len(a["data"]["readings"]), 3)
        self.assertEqual(len(a["trace"]), 3, "每個讀數應有來源追溯")

        # 3) 交接：compute→stats@1，數值由上游 readings 正確導出
        b = json.load(open(os.path.join(run_dir, "b.stats.json"), encoding="utf-8"))
        self.assertEqual(b["schema"], "stats@1")
        s = b["data"]["stats"]
        self.assertEqual(s["count"], 3)
        self.assertAlmostEqual(s["sum"], 12.0)
        self.assertAlmostEqual(s["mean"], 4.0)
        self.assertEqual(len(b["trace"]), 3, "trace 應逐層透傳，交接不遺失")

        # 4) 交接：report→Markdown DRAFT，含摘要 + 來源追溯
        md = open(os.path.join(run_dir, "report.md"), encoding="utf-8").read()
        self.assertIn("DRAFT", md)
        self.assertIn("count: 3", md)
        self.assertIn("來源追溯", md)

    def test_failure_propagates_and_stops(self):
        # extract 對「含數字卻無法解析」的行 fail-loud（exit3）；編排層應整條判定 FAILED、指名失敗步驟。
        r, run_dir = _run_flow("ok: 1\nbad: v1.2.3.4\n")
        self.assertEqual(r.returncode, 2, "任一步失敗 → run.py exit 2")
        mani = json.load(open(os.path.join(run_dir, "run_manifest.json"), encoding="utf-8"))
        self.assertEqual(mani["state"], "FAILED")
        self.assertEqual(mani["failed_step"], "extract")
        self.assertTrue(mani["human_review_required"])
        # 下游不應產生（在失敗點即停止，非靜默續跑）
        self.assertFalse(os.path.exists(os.path.join(run_dir, "b.stats.json")))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "report.md")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
