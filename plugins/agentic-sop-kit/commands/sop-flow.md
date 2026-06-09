---
description: Run the agentic-sop-kit workflow (extract→compute→report) and report the DRAFT result.
---

執行轉換 kit 的編排流程並回報。

> 前置：本指令操作「目前專案」的 `agentic-sop-kit/`。若該專案還沒有，先用本 plugin 內附的 kit 佈署一次：
> `python3 "${CLAUDE_PLUGIN_ROOT}/kit/bootstrap.py" --project "$CLAUDE_PROJECT_DIR"`
> （或指向你機器上的 canonical kit：`python3 ~/.claude/agentic-sop-kit/bootstrap.py --project "$CLAUDE_PROJECT_DIR"`）。

1. 先跑依賴檢查：`python3 agentic-sop-kit/check_deps.py`（缺項會明確列出 → 先請使用者補齊，不要硬跑）。
2. 跑流程：`python3 agentic-sop-kit/workflow/run.py`（可加 `--input <檔>` 換輸入）。$ARGUMENTS
3. 讀新產生的 `agentic-sop-kit/runs/<run_id>/report.md` 與 `run_manifest.json`，向使用者摘要結果。
4. 產出是 **DRAFT** → 提醒使用者需人覆核、永不自動歸檔。
5. 若某步 `"state":"FAILED"`（如缺依賴），**據實回報 manifest 的 error**，不得佯稱成功。
