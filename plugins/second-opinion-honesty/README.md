# Second Opinion — adversarial honesty reviewer

> An independent second reader for a finished DRAFT. It checks whether every claim is
> backed by its evidence — fabrication, transcription slips, invented IDs, wrong PASS/FAIL,
> conclusions the data don't support — and hands you a findings report that is **itself a
> DRAFT**. A human owns the verdict. Domain-neutral: pharma, frontend, backend, anything.

A companion to **agentic-sop-kit** (it reads that kit's run artifacts), but it installs and
runs independently. Deterministic checks in code + a capped, advisory LLM pass. MIT.

`🌐 English` · [繁體中文](#繁體中文)

```
        FULL  ─ /second-opinion <kit run_dir> ──┐
                                                 ├─▶  deterministic checks (HARD)  ─┐
        DEGRADED ─ /second-opinion <doc> --inputs ┘     +  capped advisory LLM (SOFT) ├─▶  DRAFT report ─▶ ✋ human decides
                                                                                      ┘
```

## What it catches
| # | Defect | Layer |
|---|---|---|
| #1 | wrong PASS/FAIL or spec-limit verdict; aggregate that doesn't recompute | deterministic |
| #2 | a number with no matching source token (fabrication / transcription) | deterministic |
| #3 | an invented identifier / date / name (should be `【待補】`) | deterministic |
| #4 | a conclusion the data don't support (overreach) | advisory LLM |

It does **not** review source-code quality / bugs / security (that's `/code-review`), and it
does **not** audit workflow architecture (that's `agentic-workflow-audit`).

## Two modes
- **FULL** — point at an agentic-sop-kit `run_dir`. Uses the run's `trace`, so #1/#2/#3 are
  **HARD** at confidence 1.0.
- **DEGRADED** — point at any document + supply the source inputs. Provenance is reconstructed
  best-effort, so findings are **SOFT** at 0.5; #1/#4 lean on the advisory layer.

## Install (independent of the kit)
```
/plugin marketplace add s0912758806p/agentic-sop-to-work
/plugin install second-opinion-honesty@agentic-sop-to-work
/reload-plugins
```
Verify: `/help` lists `/second-opinion`. Requires Python 3.8+ as `python3` (stdlib only).

## Use
```
/second-opinion <run_dir>                       # FULL — a kit run dir
/second-opinion <doc> --inputs <file...>        # DEGRADED — any document
/second-opinion                                 # bundled cross-domain demo
```

## Pairing without coupling
The only link to agentic-sop-kit is a **read-only artifact contract**
(`run_manifest.json` + artifacts shaped `{schema, produced_by, data, trace}`). Second Opinion
re-implements that contract for reading; it never imports the kit and never writes into the
kit's run dir. With no kit present it still runs (DEGRADED, or the bundled demo).

## The guarantees live in code, not prose
- The report's `verdict` is the frozen literal `ADVISORY_ONLY` and `human_owns_verdict` is
  always `true` — it **cannot** say "Second Opinion approved this."
- The advisory LLM pass is **capped** (`SECONDOP_MAX_LLM_PASSES`, default 1), every finding is
  **clamped** to SOFT / confidence ≤ 0.5, **dropped** unless it cites a verbatim draft span (or
  `NO SOURCE`), and **suppressed** if it re-litigates a slot the deterministic layer settled.

## Enforce a human acknowledgement (optional — in code, not prose)
By default the human-owned STOP is a prompt the command presents. To make it a hard gate, a
project opts in:
```
mkdir -p .second-opinion && touch .second-opinion/require_ack
```
Now the bundled Stop-hook **blocks the session from ending** until the latest DRAFT run
(`.agentic-sop-runs/<id>/`) has a Second Opinion review **and** a human acknowledged it:
```
python3 -m secondop.ack            # a human runs this after reading the report
```
It enforces THAT a human acknowledged — never WHAT they decided. Anti-loop capped by
`SECONDOP_MAX_ACK_RETRIES` (default 3); a silent no-op in projects that didn't opt in.

## Develop
```
python3 tests/verify.py        # full regression (unit + integration + stdlib-only guard)
```

---

## 繁體中文

> 一個獨立的「第二意見」審查者，針對一份完成的 DRAFT，檢查它的每個**主張是否有證據支撐**
> ——臆造、抄錯、捏造編號、判定錯（PASS/FAIL）、資料不支持的結論——然後給你一份本身也是
> **DRAFT** 的發現報告。**核准永遠由人決定**。領域中立：pharma、前端、後端都能用。

它是 **agentic-sop-kit** 的搭配 plugin（讀取該 kit 的 run 產物），但可**獨立安裝、獨立執行**。
確定性檢查寫在程式裡 + 一層**封頂的 advisory LLM**。MIT 授權。

### 它抓什麼
- **#1** 判定錯（PASS/FAIL、規格上下限）、算不回去的彙總 —— 確定性層
- **#2** 兜不回輸入的數字（臆造／抄錯）—— 確定性層
- **#3** 捏造的編號／日期／姓名（應標 `【待補】`）—— 確定性層
- **#4** 資料不支持的過度結論 —— advisory LLM 層

**不**審原始碼品質／bug／資安（那是 `/code-review`）；**不**稽核工作流架構（那是
`agentic-workflow-audit`）。本 skill 只查「這次產出的主張 vs. 證據」誠實度。

### 兩種模式
- **FULL**：指向 agentic-sop-kit 的 `run_dir`，用 `trace` → #1/#2/#3 為 **HARD**（信心 1.0）。
- **DEGRADED**：指向任意文件 + 自備來源輸入，盡力重建來源 → 全部降為 **SOFT**（0.5）；#1/#4 交給 advisory 層。

### 安裝（不依賴 kit）
```
/plugin marketplace add s0912758806p/agentic-sop-to-work
/plugin install second-opinion-honesty@agentic-sop-to-work
/reload-plugins
```
需 Python 3.8+（`python3`，純標準庫）。

### 使用
```
/second-opinion <run_dir>                       # FULL
/second-opinion <doc> --inputs <file...>        # DEGRADED
/second-opinion                                 # 內建跨領域 demo
```

### 鬆耦合
與 kit 的唯一連結是**唯讀 artifact 契約**（`run_manifest.json` + `{schema,produced_by,data,trace}`）。
Second Opinion 只**重實作**該契約來讀取，**不 import kit**、**不寫進** kit 的 run 目錄；沒裝 kit 也能跑。

### 保證寫在程式裡，不在散文
- 報告的 `verdict` 鎖死為 `ADVISORY_ONLY`、`human_owns_verdict` 恆為 `true` —— schema 上**無法**表達「Second Opinion 核准了」。
- advisory LLM 層**封頂**（`SECONDOP_MAX_LLM_PASSES`，預設 1）；每條發現一律**夾鉗**為 SOFT／信心 ≤ 0.5、**未引用** draft 逐字片段（或 `NO SOURCE`）即**丟棄**、**重提**已定案 slot 即**抑制**。

### 強制人工確認（選用——寫在程式裡，不在散文）
預設那個「人核准」STOP 只是 command 印出來的提示。要把它變成硬閘門，由專案 opt-in：
```
mkdir -p .second-opinion && touch .second-opinion/require_ack
```
之後內建的 Stop-hook 會**擋住 session 收工**，直到最新的 DRAFT run（`.agentic-sop-runs/<id>/`）
有 Second Opinion 覆核**且**有人確認：
```
python3 -m secondop.ack            # 人看完報告後自己跑這個
```
它強制「**有沒有人確認**」，不強制「決定內容」。anti-loop 封頂於 `SECONDOP_MAX_ACK_RETRIES`
（預設 3）；沒 opt-in 的專案完全 no-op。

MIT © s0912758806p
