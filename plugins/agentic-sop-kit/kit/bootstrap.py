#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""bootstrap.py — 一鍵把 agentic-sop-kit 導入一個目標專案。

把「canonical kit（本檔所在目錄）」複製進 <project>/agentic-sop-kit/，並安裝 Claude Code
觸發點：slash command（/sop-flow）+ hooks（SessionStart 依賴檢查、Stop 自動回歸）。
全程冪等、純標準庫、不靜默覆蓋（既有 kit 需 --force）；所有動作明確列印。

用法:
    python3 ~/.claude/agentic-sop-kit/bootstrap.py --project /path/to/project [--force] [--no-hooks]
"""
import argparse
import json
import os
import shutil
import sys

KIT_SRC = os.path.dirname(os.path.abspath(__file__))   # 本 kit 根（canonical）
DEST_NAME = "agentic-sop-kit"
# 複製時排除的執行期/雜項（保持目標乾淨）
IGNORE = shutil.ignore_patterns(
    "runs", "__pycache__", "*.pyc", ".DS_Store",
    "regression_log.jsonl", ".git", "*.egg-info",
)


def _load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        txt = f.read().strip()
    return json.loads(txt) if txt else {}


def copy_kit(project, force):
    dest = os.path.join(project, DEST_NAME)
    if os.path.realpath(dest) == os.path.realpath(KIT_SRC):
        sys.exit("❌ 目標等於 canonical kit 自身，無需導入。")
    if os.path.exists(dest):
        if not force:
            print(f"⚠️  已存在 {dest}（略過複製；要覆蓋加 --force）")
            return dest, False
        shutil.rmtree(dest)
    shutil.copytree(KIT_SRC, dest, ignore=IGNORE)
    print(f"✅ 複製 kit → {dest}")
    return dest, True


def install_command(project):
    src = os.path.join(KIT_SRC, "commands", "sop-flow.md")
    if not os.path.exists(src):
        print("⚠️  找不到 commands/sop-flow.md，略過 slash command")
        return
    cmd_dir = os.path.join(project, ".claude", "commands")
    os.makedirs(cmd_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(cmd_dir, "sop-flow.md"))
    print(f"✅ slash command → {os.path.join(cmd_dir, 'sop-flow.md')}（輸入 /sop-flow 觸發）")


def merge_hooks(project):
    snippet = _load_json(os.path.join(KIT_SRC, "hooks", "settings.snippet.json"))
    new_hooks = snippet.get("hooks")
    if not new_hooks:
        print("⚠️  snippet 無 hooks 區段，略過 hook 安裝")
        return
    claude_dir = os.path.join(project, ".claude")
    os.makedirs(claude_dir, exist_ok=True)
    settings_path = os.path.join(claude_dir, "settings.json")
    settings = _load_json(settings_path)
    hooks = settings.setdefault("hooks", {})
    added = 0
    for event, entries in new_hooks.items():
        existing = hooks.setdefault(event, [])
        seen = {json.dumps(e, sort_keys=True, ensure_ascii=False) for e in existing}
        for e in entries:
            key = json.dumps(e, sort_keys=True, ensure_ascii=False)
            if key not in seen:
                existing.append(e)
                seen.add(key)
                added += 1
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"✅ 合併 hooks → {settings_path}（新增 {added} 條：SessionStart 依賴檢查 + Stop 自動回歸）")


def export_claude_skills(project):
    """順便把每個已登記的 skill 產成「對話可觸發的 runner skill」到 <project>/.claude/skills/。"""
    sys.path.insert(0, KIT_SRC)
    try:
        import export_claude_skill as ex
        reg = _load_json(os.path.join(KIT_SRC, "tests", "registry.json"))
        names = list(reg.get("skills", {}).keys())
        for n in names:
            ex.export_one(n, project=project)
        print(f"✅ 產出 {len(names)} 支對話可觸發的 runner skill → "
              f"{os.path.join(project, '.claude', 'skills')}")
    except SystemExit as e:
        print(f"⚠️  runner skill 匯出略過：{e}")


def main():
    ap = argparse.ArgumentParser(description="一鍵把 agentic-sop-kit 導入目標專案")
    ap.add_argument("--project", required=True, help="目標專案根目錄")
    ap.add_argument("--force", action="store_true", help="覆蓋既有的 <project>/agentic-sop-kit/")
    ap.add_argument("--no-hooks", action="store_true", help="只複製 kit + slash command，不裝 hooks")
    ap.add_argument("--with-claude-skills", action="store_true",
                    help="順便把已登記的 skill 產成對話可觸發的 runner skill 到 .claude/skills/")
    args = ap.parse_args()

    project = os.path.abspath(os.path.expanduser(args.project))
    if not os.path.isdir(project):
        sys.exit(f"❌ 目標專案不存在：{project}")

    print(f"→ 導入 agentic-sop-kit 至：{project}")
    print(f"  canonical 來源：{KIT_SRC}")
    copy_kit(project, args.force)
    install_command(project)
    if args.no_hooks:
        print("ℹ️  --no-hooks：略過 hook 安裝")
    else:
        merge_hooks(project)
    if args.with_claude_skills:
        export_claude_skills(project)

    print("\n下一步（在目標專案）：")
    print(f"  python3 {DEST_NAME}/check_deps.py        # 驗依賴（缺項明確報錯）")
    print(f"  python3 {DEST_NAME}/workflow/run.py       # 跑通範例流程（DRAFT）")
    print("  再用 templates/ 依拆解規則加你的 skill；詳見 kit 的 SOP.md / README.md。")
    print("✅ 導入完成。產出一律 DRAFT、需人核准；hooks 已就緒做自動回歸把關。")


if __name__ == "__main__":
    main()
