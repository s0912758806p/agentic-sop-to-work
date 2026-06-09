# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""export_claude_skill.py — 產生/移除「可被 Claude 載入的 runner skill」（預設不執行，需明確呼叫）。

讀 skills/<name>/SKILL.md 的 frontmatter（name + description），在
<project>/.claude/skills/<name>/SKILL.md 產出一支「薄殼 runner」：被對話觸發時，
指示 Claude **執行確定性的 tool.py / run.py** 並回報 DRAFT，而不是自己用 LLM 重做——
讓工具能由對話觸發，同時守住「控制流由程式決定、不交給模型」的鐵則。

用法:
  # 產生
  python3 agentic-sop-kit/export_claude_skill.py --skill extract --project /path/to/project
  python3 agentic-sop-kit/export_claude_skill.py --all --project /path/to/project
  # 移除（只刪本工具產生的；手寫/改過的會被拒絕，除非 --force）
  python3 agentic-sop-kit/export_claude_skill.py --remove --skill extract --project /path/to/project
  python3 agentic-sop-kit/export_claude_skill.py --remove --all --project /path/to/project
"""
import argparse
import json
import os
import re

# 出現在「我們產生的」runner skill 內容中 → 用來辨識，避免 --remove 誤刪手寫/改過的 skill。
_MARKER = "agentic-sop-kit 自動產生"


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


def _dest_dir(name, project, dest):
    if dest is not None:
        return dest
    if not project:
        raise SystemExit("❌ 需要 --project 或 --dest")
    return os.path.join(project, ".claude", "skills", name)


def export_one(name, project=None, dest=None):
    """從 skills/<name>/SKILL.md 產出一支 runner skill 到 <project>/.claude/skills/<name>/（或 dest）。"""
    src = os.path.join(_root(), "skills", name, "SKILL.md")
    if not os.path.exists(src):
        raise SystemExit(f"❌ 找不到工具 skill：{src}")
    fm = _frontmatter(src)
    desc = (fm.get("description") or f"Run the {name} tool (deterministic).").strip()
    desc_yaml = '"' + desc.replace("\\", "\\\\").replace('"', '\\"') + '"'   # 引號包起 → YAML 安全
    dest = _dest_dir(name, project, dest)
    os.makedirs(dest, exist_ok=True)
    out = os.path.join(dest, "SKILL.md")
    front = f"---\nname: {name}\ndescription: {desc_yaml}\n---\n\n"
    open(out, "w", encoding="utf-8").write(front + _BODY.format(name=name))
    print(f"✅ Claude runner skill → {out}")
    return out


def remove_one(name, project=None, dest=None, force=False):
    """移除先前產生的 runner skill。安全鎖：只刪含本工具標記者（除非 force）；不存在則略過。"""
    dest = _dest_dir(name, project, dest)
    out = os.path.join(dest, "SKILL.md")
    if not os.path.exists(out):
        print(f"… 略過（找不到）：{out}")
        return False
    if _MARKER not in open(out, encoding="utf-8").read() and not force:
        print(f"⚠️  拒絕移除（非本工具產生或已被手改）：{out}（要強制刪除加 --force）")
        return False
    os.remove(out)
    try:                                  # 目錄若因此清空 → 一併移除（不刪使用者另放的檔）
        if not os.listdir(dest):
            os.rmdir(dest)
    except OSError:
        pass
    print(f"🗑️  已移除 runner skill → {out}")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="generate/remove a Claude-loadable runner skill from a kit tool skill")
    ap.add_argument("--skill", help="工具 skill 名稱（skills/<name>）")
    ap.add_argument("--all", action="store_true", help="作用於 registry.json 內所有 skill")
    ap.add_argument("--project", default=os.environ.get("CLAUDE_PROJECT_DIR"),
                    help="目標專案根（<project>/.claude/skills/）")
    ap.add_argument("--dest", default=None, help="直接指定目錄（每個 skill 建一個子目錄）")
    ap.add_argument("--remove", action="store_true", help="移除（而非產生）runner skill")
    ap.add_argument("--force", action="store_true",
                    help="搭配 --remove：即使看起來非本工具產生也強制刪除")
    a = ap.parse_args(argv)

    if not a.all and not a.skill:
        raise SystemExit("❌ 請給 --skill <name> 或 --all")
    if a.all:
        reg = json.load(open(os.path.join(_root(), "tests", "registry.json"), encoding="utf-8"))
        names = list(reg.get("skills", {}).keys())
        if not names:
            raise SystemExit("❌ registry.json 無 skills")
    else:
        names = [a.skill]

    if a.remove:
        done = sum(1 for n in names
                   if remove_one(n, a.project, None if a.dest is None else os.path.join(a.dest, n), a.force))
        print(f"🗑️  已移除 {done}/{len(names)} 支 runner skill。")
    else:
        for n in names:
            export_one(n, a.project, None if a.dest is None else os.path.join(a.dest, n))
        print(f"✅ 共匯出 {len(names)} 支 runner skill。")


if __name__ == "__main__":
    main()
