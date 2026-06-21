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
- 任一步 `"state":"FAILED"` → **封頂自動修復（fix-loop，最多 3 次）**，再不行才交人：
  1. 讀 manifest 的 `failure{step,gate_type,message,artifact}` 分類：**輸入問題／生成層輸出**（schema/trace 等）→ 修輸入或重生該段，**用相同 `--run-id` 重跑**（引擎對同 run-id 計數、超過 `--max-fix-retries 3` 會自行拒跑＝程式封頂）；**工具碼/recompute/cmd bug** → 診斷並提修正建議、不盲跑、不偷改輸出，交人；**判斷/受控步驟** → 不自動修，交人。
  2. `stalled:true`（原地打轉：`stall_reason` = idle/thrash）→ **STOP，回報卡住的 gate、重複的 `repeated_signature`、撞了 `stall_rounds` 圈**，不得佯稱成功、不得換 `--run-id` 規避。
  3. `fix_exhausted:true` 或不可自動修 → **STOP，據實回報每次嘗試與原因**，不得佯稱成功。
  4. **永不為過關竄改輸出**（閘門查真相）；最終一律 **DRAFT、需人核准**，永不自動歸檔。
- 事實只來自輸入與工具輸出；缺值標【待補】，絕不臆造。
