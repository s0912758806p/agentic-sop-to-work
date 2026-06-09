"""Skill B 工具：compute — 讀 readings artifact，計算統計（count/sum/mean/min/max），輸出 stats artifact。
單一工具（python3 stdlib statistics）。trace 由上游透傳（保留來源追溯）。"""
import os
import sys
from statistics import mean

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import kit  # noqa: E402

DEPS = [{"kind": "python", "min": "3.8"}]
WHO = "compute"


def run(inp, out):
    up = kit.read_artifact(inp)
    vals = [r["value"] for r in up["data"]["readings"]]
    stats = {
        "count": len(vals),
        "sum": sum(vals),
        "mean": (mean(vals) if vals else None),
        "min": (min(vals) if vals else None),
        "max": (max(vals) if vals else None),
    }
    # 透傳上游 skipped（未解析行），讓下游報告可揭露，不在流程中遺失
    data = {"stats": stats, "skipped": up["data"].get("skipped", [])}
    kit.write_artifact(kit.artifact("stats@1", WHO, data, up.get("trace", [])), out)


if __name__ == "__main__":
    kit.skill_main(DEPS, WHO, run)
