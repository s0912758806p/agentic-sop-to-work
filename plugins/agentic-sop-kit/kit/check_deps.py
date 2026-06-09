"""聚合依賴檢查（驗收 c）：彙總編排層 + flow.json 內**每一個** skill 宣告的依賴，缺任一 → 明確列出並 exit 1。

用法：python3 check_deps.py
- skill 清單由 `workflow/flow.json` 推導（不寫死）→ 你用範本新增的 skill 也會被涵蓋。
- DEPS 以 **AST 靜態讀取**（不 import/執行 tool.py）→ 即使某 skill 頂層 import 缺的第三方套件，也能給乾淨彙總訊息，不吐 raw traceback、不中途中止。
"""
import ast
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import kit  # noqa: E402


def _deps_of(tool_path):
    """靜態（AST）取 tool.py 頂層的 DEPS literal；不執行模組（避免缺套件 import 崩潰）。"""
    if not os.path.exists(tool_path):
        return [{"kind": "exe", "name": f"<找不到 tool: {tool_path}>"}]
    try:
        tree = ast.parse(open(tool_path, encoding="utf-8").read())
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "DEPS" for t in node.targets):
                return ast.literal_eval(node.value)
    except Exception as e:
        return [{"kind": "module", "name": f"<{os.path.basename(os.path.dirname(tool_path))} 的 DEPS 無法靜態解析: {e}>"}]
    return []


def _flow_tools():
    flow = json.load(open(kit.kit_path("workflow", "flow.json"), encoding="utf-8"))
    out, seen = [], set()
    for st in flow["steps"]:
        tp = kit.kit_path(st["tool"])
        if tp not in seen:
            seen.add(tp)
            out.append((st["skill"], tp))
    return out


def main():
    all_deps = [{"kind": "python", "min": "3.8"}]   # 編排層自身
    names = []
    for name, tp in _flow_tools():
        names.append(name)
        all_deps += _deps_of(tp)
    missing = sorted(set(kit.check_deps(all_deps)))
    if missing:
        print("❌ 缺少依賴（請先安裝/設定）：\n  - " + "\n  - ".join(missing))
        raise SystemExit(1)
    print("✅ 所有依賴齊備（編排層 + " + " / ".join(names) + "）。")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
