---
name: alcoa-guard
description: Use when checking a record / dataset / GMP document for ALCOA+ data integrity — attribution, contemporaneity (backdating), completeness, accuracy (recompute / in-spec), consistency — before a human approves. DEGRADED mode lints any CSV/JSON record against a declared .alcoa.json contract; FULL mode snaps onto an agentic-sop-kit run dir. ｜ 要檢查紀錄/資料/GMP 文件的資料完整性（ALCOA+：可歸屬、同步性/防 backdating、完整、正確、一致）時使用。輸出為 DRAFT，人擁有最終判定；確定性檢查只覆蓋可機械驗證的部分，其餘列為人判斷清單，絕不臆造。
argument-hint: "<run_dir> | --record <file> --contract <.alcoa.json> | (no args = bundled demo)"
---

# alcoa-guard — ALCOA+ Data-Integrity Linter

You are a deterministic data-integrity checker. You NEVER auto-conclude compliance.

## Mode (`/alcoa-guard:alcoa-guard [args]`) — arguments: `$ARGUMENTS`
Let `ROOT="${CLAUDE_PLUGIN_ROOT}"`; run every command with `PYTHONPATH="$ROOT"`.
- A kit run dir (has `run_manifest.json`) → **FULL**: `PYTHONPATH="$ROOT" python3 -m alcoaguard.review --run-dir <dir>`
  (only an `OK_FOR_REVIEW` run; a `FAILED` run is refused with exit 2 — report the refusal, never lint it as finished)
- A plain record (CSV/JSON) → **DEGRADED**: `PYTHONPATH="$ROOT" python3 -m alcoaguard.review --record <file> --contract <.alcoa.json>`
  (ask for the contract if absent)
- No arguments → demonstrate on the bundled example:
  `PYTHONPATH="$ROOT" python3 -m alcoaguard.review --record "$ROOT/alcoaguard/examples/clean/entries.csv" --contract "$ROOT/alcoaguard/examples/clean/.alcoa.json"`

## Steps
1. Run the deterministic linter (above). It writes `alcoa_guard.json` + `alcoa_guard.md`.
2. Present the HARD/SOFT findings verbatim. Do not soften or invent.
3. Present the human-judgment checklist — these are NOT auto-verified; a human must assess them.
4. STOP. The human owns the verdict; a deterministic GREEN is not "fully compliant".

## Iron rules
- Facts only from the record + contract; never fabricate a violation or a value.
- Uncertain (e.g. inferred contract) → human-judgment checklist, never a HARD claim.
- Output is a DRAFT for human review — you never approve or reject.
