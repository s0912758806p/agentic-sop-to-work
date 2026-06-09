# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""export_claude_skill.py — 從一支「工具 skill」產出可被 Claude 載入的 runner skill。

讀 skills/<name>/SKILL.md 的 frontmatter（name + description），在
<project>/.claude/skills/<name>/SKILL.md 產出一支「薄殼 runner」：被對話觸發時，
指示 Claude **執行確定性的 tool.py / run.py** 並回報 DRAFT，而不是自己用 LLM 重做——
讓工具能由對話觸發，同時守住「控制流由程式決定、不交給模型」的鐵則。

用法:
  python3 agentic-sop-kit/export_claude_skill.py --skill extract --project /path/to/project
  python3 agentic-sop-kit/export_claude_skill.py --all --project /path/to/project
"""
import argparse
import json
import os
import re


def _root():
    return os.environ.get("SOPKIT_ROOT") or os.path.dirname(os.path.abspath(__file__))


def _frontmatter(md_path):
    text = open(md_path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        raise SystemExit(f"❌ {md_path} 無 YAML frontmatter")
    fm = {}
    for line in m.group(1).split("\n"):
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


_BODY = """# {name}（runner skill — agentic-sop-kit 自動產生）

> 自動產生自 `agentic-sop-kit/skills/{name}/SKILL.md`。**這是薄殼 runner**：它不自己用 LLM 做事，而是執行底層那支確定性工具並回報 DRAFT。重新產生：`python3 agentic-sop-kit/export_claude_skill.py --skill {name} --project .`

當使用者的需求符合上面的 description 時，**不要自己在對話裡用 LLM 完成它**。請執行底層確定性程式並回報：

1. 確認本專案已導入 kit：`$CLAUDE_PROJECT_DIR/agentic-sop-kit/`（若無 → 先 `python3 "${{CLAUDE_PLUGIN_ROOT}}/kit/bootstrap.py" --project "$CLAUDE_PROJECT_DIR"`）。
2. 依賴檢查：`python3 agentic-sop-kit/check_deps.py`（缺項會明確列出 → 請使用者補齊，勿硬跑）。
3. 執行工具（單步）：`python3 agentic-sop-kit/skills/{name}/tool.py --in <輸入> --out <輸出.json>`；
   若要跑整條 SOP 流程（多步），改用 `python3 agentic-sop-kit/workflow/run.py`。
4. 讀產出，向使用者**摘要**。產出一律是 **DRAFT**、需人覆核，永不自動歸檔進受控系統。
5. 事實只來自工具的輸入與輸出；缺值標【待補】，絕不臆造。
6. 程式回非 0 或 manifest `state=FAILED` → **據實回報 stderr/error**，不得佯稱成功。
"""


def export_one(name, project=None, dest=None):
    """從 skills/<name>/SKILL.md 產出一支 runner skill 到 <project>/.claude/skills/<name>/（或 dest）。"""
    src = os.path.join(_root(), "skills", name, "SKILL.md")
    if not os.path.exists(src):
        raise SystemExit(f"❌ 找不到工具 skill：{src}")
    fm = _frontmatter(src)
    desc = (fm.get("description") or f"Run the {name} tool (deterministic).").strip()
    desc_yaml = '"' + desc.replace("\\", "\\\\").replace('"', '\\"') + '"'   # 引號包起 → YAML 安全
    if dest is None:
        if not project:
            raise SystemExit("❌ 需要 --project 或 --dest")
        dest = os.path.join(project, ".claude", "skills", name)
    os.makedirs(dest, exist_ok=True)
    out = os.path.join(dest, "SKILL.md")
    front = f"---\nname: {name}\ndescription: {desc_yaml}\n---\n\n"
    open(out, "w", encoding="utf-8").write(front + _BODY.format(name=name))
    print(f"✅ Claude runner skill → {out}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="export a kit tool skill as a Claude-loadable runner skill")
    ap.add_argument("--skill", help="工具 skill 名稱（skills/<name>）")
    ap.add_argument("--all", action="store_true", help="匯出 registry.json 內所有 skill")
    ap.add_argument("--project", default=os.environ.get("CLAUDE_PROJECT_DIR"),
                    help="目標專案根（輸出到 <project>/.claude/skills/）")
    ap.add_argument("--dest", default=None, help="直接指定輸出目錄（每個 skill 建一個子目錄）")
    a = ap.parse_args(argv)
    if a.all:
        reg = json.load(open(os.path.join(_root(), "tests", "registry.json"), encoding="utf-8"))
        names = list(reg.get("skills", {}).keys())
        if not names:
            raise SystemExit("❌ registry.json 無 skills")
        for n in names:
            export_one(n, a.project, None if a.dest is None else os.path.join(a.dest, n))
        print(f"✅ 共匯出 {len(names)} 支 runner skill。")
    elif a.skill:
        export_one(a.skill, a.project, a.dest)
    else:
        raise SystemExit("❌ 請給 --skill <name> 或 --all")


if __name__ == "__main__":
    main()
