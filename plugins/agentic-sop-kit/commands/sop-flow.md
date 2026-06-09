---
description: Run the agentic-sop-kit workflow (extract→compute→report) and report the DRAFT result. Works out-of-the-box (bundled demo) even before a project adopts the kit.
---

執行 agentic-sop-kit 的編排流程並回報 DRAFT。**先判斷目前專案是否已導入 kit**：

### 情況 A — 專案已導入（`$CLAUDE_PROJECT_DIR/agentic-sop-kit/` 存在）
跑該專案自己的、受 Stop-hook 閘門保護的流程：
1. 依賴檢查：`python3 agentic-sop-kit/check_deps.py`（缺項明確列出 → 請使用者補齊，勿硬跑）。
2. 跑流程：`python3 agentic-sop-kit/workflow/run.py`（可加 `--input <檔>` 換輸入）。$ARGUMENTS
3. 讀新產生的 `agentic-sop-kit/runs/<run_id>/report.md` 與 `run_manifest.json`，向使用者摘要。

### 情況 B — 尚未導入（開箱即用 demo，免 bootstrap）
直接跑 plugin 內附的範例 kit，輸出寫到專案的 `.agentic-sop-runs/`：
1. 依賴檢查：`python3 "${CLAUDE_PLUGIN_ROOT}/kit/check_deps.py"`。
2. 跑範例：`python3 "${CLAUDE_PLUGIN_ROOT}/kit/workflow/run.py" --out-base "$CLAUDE_PROJECT_DIR/.agentic-sop-runs"`（可加 `--input <檔>`）。$ARGUMENTS
3. 讀 `.agentic-sop-runs/<run_id>/report.md` 與 `run_manifest.json`，向使用者摘要。
4. 告訴使用者：要讓**這個專案**常駐 kit 並受 Stop-hook 回歸閘門保護，跑一次：
   `python3 "${CLAUDE_PLUGIN_ROOT}/kit/bootstrap.py" --project "$CLAUDE_PROJECT_DIR"`（加 `--with-claude-skills` 會順便產出對話可觸發的 runner skills）。

### 兩種情況都適用
- 產出一律是 **DRAFT** → 提醒需人覆核、永不自動歸檔進受控系統。
- 任一步 `"state":"FAILED"`（如缺依賴）→ **據實回報 manifest 的 error / stderr**，不得佯稱成功。
- 事實只來自輸入與工具輸出；缺值標【待補】，絕不臆造。
