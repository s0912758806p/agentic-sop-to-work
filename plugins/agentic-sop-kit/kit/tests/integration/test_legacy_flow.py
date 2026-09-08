# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""回歸護欄：未宣告圖欄位的 flow.json 行為必須與 graph-engineering 改版前**逐位元相同**。

v1.9.0 已上 marketplace，`bootstrap.py` 會把整套 kit 複進別的專案（NOTICE 要求逐檔保留屬名）
→ 野生副本無法列舉、無更新通道。圖功能一律 opt-in；這支測試是那個承諾的可執行版本。

刻意用**逐位元比對**而非「大約對」：graph 相關改動若讓 artifact 多一個鍵、少一個鍵、
或動到 trace 透傳，這裡就會紅。基線值取自改版前的實際輸出（bundled demo input）。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = os.path.join(KIT, "workflow", "run.py")
EX = os.path.join(KIT, "workflow", "examples")

# --- 改版前基線（bundled example/inputs/sample_readings.txt）-------------------
BASE_READINGS = {
    "schema": "readings@1",
    "produced_by": "extract",
    "data": {
        "readings": [
            {"key": "assay purity", "value": 99.4},
            {"key": "moisture", "value": 0.3},
            {"key": "ph", "value": 7.1},
            {"key": "weight mg", "value": 250.0},
            {"key": "related impurity", "value": 0.12},
        ],
        "skipped": [],
    },
    "trace": [
        {"value": "99.4", "source": "sample_readings.txt", "locator": "line 2"},
        {"value": "0.3", "source": "sample_readings.txt", "locator": "line 3"},
        {"value": "7.1", "source": "sample_readings.txt", "locator": "line 4"},
        {"value": "250", "source": "sample_readings.txt", "locator": "line 5"},
        {"value": "0.12", "source": "sample_readings.txt", "locator": "line 7"},
    ],
}

BASE_STATS = {
    "schema": "stats@1",
    "produced_by": "compute",
    "data": {
        "stats": {"count": 5, "sum": 356.92, "mean": 71.384, "min": 0.12, "max": 250.0},
        "skipped": [],
    },
    "trace": BASE_READINGS["trace"],
}

BASE_REPORT = """# Measurement Summary — DRAFT

> DRAFT — 需人員覆核；由 agentic-sop-kit 範例流程產生，非正式紀錄。

## Summary
- count: 5
- sum: 356.92
- mean: 71.384
- min: 0.12
- max: 250.0

## 來源追溯（每個讀數溯回輸入位置）
- 99.4 @ sample_readings.txt:line 2
- 0.3 @ sample_readings.txt:line 3
- 7.1 @ sample_readings.txt:line 4
- 250 @ sample_readings.txt:line 5
- 0.12 @ sample_readings.txt:line 7
"""

# manifest 的鍵集合（成功路徑）。多一個鍵就是契約變了 → secondop/alcoa-guard 的讀取假設也變了。
BASE_MANIFEST_KEYS = {"flow", "run_id", "state", "steps", "final_output",
                      "human_review_required", "banner"}
BASE_STEP_KEYS = {"skill", "ok", "out", "error"}


def _run_demo(base, run_id="legacy"):
    r = subprocess.run([sys.executable, RUN, "--out-base", base, "--run-id", run_id],
                       capture_output=True, text=True)
    return r, os.path.join(base, run_id)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class LegacyFlowUnchanged(unittest.TestCase):
    """線性 demo flow（無任何 graph 欄位）的產出不得因 graph 功能而改變。"""

    def test_artifacts_are_byte_identical_to_pre_graph_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            r, run_dir = _run_demo(d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

            a = json.loads(_read(os.path.join(run_dir, "a.readings.json")))
            self.assertEqual(a, BASE_READINGS, "extract 的 artifact 與改版前不符")

            b = json.loads(_read(os.path.join(run_dir, "b.stats.json")))
            self.assertEqual(b, BASE_STATS, "compute 的 artifact 與改版前不符（含 trace 透傳）")

            self.assertEqual(_read(os.path.join(run_dir, "report.md")), BASE_REPORT,
                             "report.md 與改版前不符")

    def test_manifest_contract_unchanged(self):
        """下游（second-opinion / alcoa-guard）靠 manifest 的鍵吃飯——鍵集合不得漂移。"""
        with tempfile.TemporaryDirectory() as d:
            r, run_dir = _run_demo(d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            mani = json.loads(_read(os.path.join(run_dir, "run_manifest.json")))

            self.assertEqual(set(mani), BASE_MANIFEST_KEYS,
                             "成功路徑的 manifest 鍵集合變了 → 下游讀取假設被破壞")
            self.assertEqual(mani["state"], "OK_FOR_REVIEW")
            self.assertEqual(mani["flow"], "measurement-report")
            self.assertTrue(mani["human_review_required"])
            self.assertEqual([s["skill"] for s in mani["steps"]], ["extract", "compute", "report"])
            for s in mani["steps"]:
                self.assertEqual(set(s), BASE_STEP_KEYS, "step 記錄的鍵集合變了")
            self.assertTrue(mani["final_output"].endswith("report.md"))

    def test_plan_still_clean_for_every_shipped_flow(self):
        """--plan 對所有既有 flow 仍須 exit 0（新的靜態拓撲檢查不得誤判既有流程）。"""
        flows = [os.path.join(KIT, "workflow", "flow.json")] + \
                [os.path.join(EX, n) for n in ("fe.json", "be.json", "db.json", "ai.json")]
        for f in flows:
            with self.subTest(flow=os.path.basename(f)):
                r = subprocess.run([sys.executable, RUN, "--flow", f, "--plan"],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_shipped_example_flow_still_runs(self):
        """四支 cross-domain 範例流程（各自綁一種 gate）仍須跑得過。"""
        for name in ("fe.json", "be.json", "db.json", "ai.json"):
            with self.subTest(flow=name):
                with tempfile.TemporaryDirectory() as d:
                    r = subprocess.run([sys.executable, RUN, "--flow", os.path.join(EX, name),
                                        "--out-base", d], capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
