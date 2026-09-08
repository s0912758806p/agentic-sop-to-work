---
description: Run the agentic-sop-kit workflow (extract→compute→report, or a declared topology) and report the DRAFT result.
---

執行轉換 kit 的編排流程並回報：

1. 先跑依賴檢查：`python3 agentic-sop-kit/check_deps.py`（缺項會明確列出 → 先請使用者補齊，不要硬跑）。
2. 靜態驗證拓撲：`python3 agentic-sop-kit/workflow/run.py --plan`。exit 2 → 據實回報問題、請人修 `flow.json`，不要硬跑。
3. 跑流程：`python3 agentic-sop-kit/workflow/run.py`（可加 `--input <檔>` 換輸入）。$ARGUMENTS
4. 讀新產生的 `agentic-sop-kit/runs/<run_id>/report.md` 與 `run_manifest.json`，向使用者摘要結果。
   有宣告狀態欄位的流程，manifest 會多 `topology`（欄位 owner、退回邊與其上界）與
   `path_taken`（實走路徑、visit 次數、被歸檔的前一次產物）——照它回報，不必另跑指令。
5. 產出是 **DRAFT** → 提醒使用者需人覆核、永不自動歸檔。
6. 若某步 `state":"FAILED"`（如缺依賴），**據實回報 manifest 的 error**，不得佯稱成功。
   `revisit_exhausted` / `topology_invalid` / `stalled` 同樣據實回報並交人——
   不得調高 `max_revisits`、改寬 branch 條件或改動宣告來讓它過關。

> 安裝：把本檔複製到目標專案 `.claude/commands/sop-flow.md`，即可用 `/sop-flow` 觸發。
