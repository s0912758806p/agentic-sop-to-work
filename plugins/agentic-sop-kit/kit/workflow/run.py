"""Agentic Workflow 編排層：依 flow.json 的 SOP 順序，把各「單一工具 skill」串成完整流程（A→B→C）。

逐步以子程序執行各 skill（同一 python3），串接 artifact（上一步 out = 下一步 in），
產出 run-scoped 覆核包 `run_manifest.json`，最後 **人核准 STOP**。
任一步驟失敗（含缺依賴 → skill 內 require_deps 拋錯）→ **立即停止並回報該步 stderr**（明確報錯，非靜默）。
退出碼：0 = 流程完成（DRAFT 待覆核）；2 = 某步失敗。
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import kit  # noqa: E402

FLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow.json")
BANNER = "DRAFT — 範例流程產出，需人員覆核；本 kit 永不自動歸檔進任何受控系統。"


def main(argv=None):
    flow = json.load(open(FLOW, encoding="utf-8"))
    ap = argparse.ArgumentParser(description="agentic-sop-kit workflow: " + flow["name"])
    ap.add_argument("--input", default=None, help="流程初始輸入（預設 flow.input_default）")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out-base", default=None, help="run 目錄基底（預設 <kit>/runs）")
    a = ap.parse_args(argv)

    inp = a.input or kit.kit_path(flow["input_default"])
    run = kit.run_dir(a.out_base, a.run_id)
    rid = os.path.basename(run)

    def resolve(v):
        return v.replace("$INPUT", inp).replace("$RUN", run)

    print(f"flow={flow['name']} run={rid}")
    steps = []
    for st in flow["steps"]:
        tool, ip, op = kit.kit_path(st["tool"]), resolve(st["in"]), resolve(st["out"])
        r = subprocess.run([sys.executable, tool, "--in", ip, "--out", op],
                           capture_output=True, text=True)
        ok = (r.returncode == 0) and os.path.exists(op)
        steps.append({"skill": st["skill"], "ok": ok, "out": op, "stderr": (r.stderr or "").strip()[-600:]})
        print(f"  [{'OK' if ok else 'FAIL'}] {st['skill']} → {op}")
        if not ok:
            mani = {"flow": flow["name"], "run_id": rid, "state": "FAILED", "failed_step": st["skill"],
                    "error": (r.stderr or r.stdout or "").strip()[-1000:], "steps": steps,
                    "human_review_required": True, "banner": BANNER}
            kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
            print("  ❌ 步驟失敗：", mani["error"][:300])
            print("  manifest:", os.path.join(run, "run_manifest.json"))
            raise SystemExit(2)

    final = steps[-1]["out"]
    mani = {"flow": flow["name"], "run_id": rid, "state": "OK_FOR_REVIEW", "steps": steps,
            "final_output": final, "human_review_required": True, "banner": BANNER}
    kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
    print(f"  ✅ 流程完成 → {final}")
    print("  manifest:", os.path.join(run, "run_manifest.json"))
    print("  " + BANNER)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
