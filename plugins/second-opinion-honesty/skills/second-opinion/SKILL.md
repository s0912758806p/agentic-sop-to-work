---
name: second-opinion
description: Use when asked to get a second opinion on a finished DRAFT, fact-check or double-check a report's claims against its evidence, sanity-check before sign-off, or red-team an output for fabrication / overreach / invented IDs — even without the word "honesty". Works on an agentic-sop-kit run dir (FULL, uses the run's trace) or any plain document (DEGRADED, you supply the inputs). ｜ 要對一份已完成的 DRAFT 取得「第二意見」、在核准前查核報告主張是否有輸入佐證、抓臆造／灌水／過度宣稱／捏造編號時使用；吃 agentic-sop-kit 的 run 目錄（FULL，用 trace）或任何純文件（DEGRADED，需自備輸入）。不適用：稽核 agent 架構有沒有拆好／是不是 mega-agent（改用 agentic-workflow-audit）；審查原始碼品質／bug／資安（改用 /code-review）。本 skill 只查「這次產出的主張 vs. 證據」誠實度，只產 DRAFT，核准永遠人擁有。
argument-hint: "<run_dir> | <doc> --inputs <file...> | (no args = bundled demo)"
---

# Second Opinion — adversarial honesty reviewer

An **independent, skeptical second reader** for a finished DRAFT. It checks whether every
claim is backed by its evidence and hands back a findings report — which is itself a DRAFT.
A human decides.

## When to use / not use
- **Use** when: "get a second opinion on this report", "is this draft trustworthy / honest",
  "double-check the numbers before I sign", "red-team this output", "did it make anything up?"
- **Not** for **architecture** ("is my workflow decomposed / a mega-agent?") → `agentic-workflow-audit`.
- **Not** for **source-code quality / bugs / security** → `/code-review`, `/security-review`.
  Second Opinion reads a **produced artifact's claims vs its cited evidence**, in any domain.

## What it catches (domain-neutral)
- **#1** wrong PASS/FAIL or spec-limit verdicts, and aggregates that don't recompute.
- **#2** numbers with no matching source token (fabrication / transcription error).
- **#3** invented identifiers / dates / names with no provenance (should be `【待補】`).
- **#4** conclusions the data don't support (overreach) — advisory.

## How it works (two layers; the guarantees are in CODE, not this prose)
1. **Deterministic layer** (stdlib, hermetic): catches `#1/#2/#3`. In FULL mode these are
   **HARD** at confidence 1.0 (the kit `trace` is authoritative); in DEGRADED mode they are
   **SOFT** at 0.5 (provenance reconstructed from supplied inputs).
2. **Advisory LLM layer** (you): catches `#4` and fuzzy `#1`. It is **capped**
   (`SECONDOP_MAX_LLM_PASSES`, default 1) and every finding is **clamped to SOFT / advisory /
   confidence ≤ 0.5**, **dropped** unless it cites a verbatim draft span (or `NO SOURCE`), and
   **suppressed** if it re-litigates a slot the deterministic layer already settled.

## To run it (`/second-opinion-honesty:second-opinion [args]`)
The skill orchestrates the deterministic pass → your capped advisory pass → the
code-enforced fold-in → the human STOP. Modes:
- `<run_dir>` — FULL (an agentic-sop-kit run dir that finished `OK_FOR_REVIEW`;
  a `FAILED` run is refused with exit 2 — report that, never review it as finished)
- `<doc> --inputs <file...>` — DEGRADED (any document)
- no arguments — the bundled cross-domain demo

You are an **independent, skeptical second reader**: attack the DRAFT, never approve or
reject it.

### Determine the mode
- A directory containing `run_manifest.json` → **FULL** mode (uses the run's `trace`).
- A file path (+ `--inputs <file...>`) → **DEGRADED** mode (you supply the sources).
- No arguments → run the bundled cross-domain **demo** (`secondop/examples/pharma_stability`).

Let `ROOT="${CLAUDE_PLUGIN_ROOT}"` and `OUT="${CLAUDE_PROJECT_DIR:-.}/.second-opinion-runs"` (project-local,
so the optional ack Stop-hook finds the review). Arguments: `$ARGUMENTS`

### Step 1 — deterministic pass (zero-LLM, code-owned)
Run the deterministic checker. It writes `second_opinion.{json,md}` and an LLM envelope
`llm_input.json` into the run's output dir.

- FULL:     `PYTHONPATH="$ROOT" python3 -m secondop.review --run-dir <run_dir> --out-base "$OUT"`
- DEGRADED: `PYTHONPATH="$ROOT" python3 -m secondop.review --doc <doc> --inputs <file...> --out-base "$OUT"`

Note the output dir it prints (the `wrote …` lines). Call it `RUNOUT`.
If it exits 2 on a run dir (not a finished `OK_FOR_REVIEW` run, e.g. `FAILED`), show the
refusal message and STOP — never review a failed run as if it had finished.

### Step 2 — advisory adversarial pass (you, capped, ADVISORY only)
Read `RUNOUT/llm_input.json`. It gives you `draft_text`, `declared_sources`, `claims`,
`already_settled`, `focus`, and `rules`. Acting as an adversary:

- **Focus on `#4` (conclusion overreach) and fuzzy `#1`** (verdicts/limits the deterministic
  layer could not parse). The deterministic layer already owns `#1/#2/#3` where it could.
- **Obey the envelope `rules`**: every finding must quote a **verbatim span from `draft_text`**
  in `claim`, and justify it in `evidence` by citing a `declared_sources` token or stating
  `NO SOURCE`. **Do not** invent input values. **Do not** re-flag anything in `already_settled`.
- Keep `confidence ≤ 0.5` (the code clamps it regardless).

Write your candidate findings to `RUNOUT/llm_candidates.json`, conforming to
`secondop/redteam_schema.json` (an object `{"findings": [...]}`). If you find nothing
beyond what the deterministic layer caught, write `{"findings": []}`.

### Step 3 — fold-in (code-enforced clamp / evidence-gate / cap)
Re-run review with your candidates. The code clamps them to SOFT/advisory, drops any that
fail the evidence gate, suppresses re-litigation of settled slots, and enforces the pass cap
(`SECONDOP_MAX_LLM_PASSES`, default 1):

- FULL:     `PYTHONPATH="$ROOT" python3 -m secondop.review --run-dir <run_dir> --advisory "$RUNOUT/llm_candidates.json" --out-base "$OUT"`
- DEGRADED: `PYTHONPATH="$ROOT" python3 -m secondop.review --doc <doc> --inputs <file...> --advisory "$RUNOUT/llm_candidates.json" --out-base "$OUT"`

### Step 4 — present + STOP (human owns the verdict)
Show the final `RUNOUT/second_opinion.md`. Summarize: HARD (deterministic) vs SOFT
(advisory) counts, and any accusations the evidence gate dropped (transparency that the
red-team was itself checked). Then **STOP** with an explicit, human-owned decision —
do not approve, reject, or file anything yourself:

> ✋ **Human decision required.** Second Opinion is advisory and does not decide.
> Choose: **[Approve the draft]** · **[Send back for fix]** · **[Override a specific finding (give a reason)]**

## Iron rules
- Facts only from inputs; unknowns are `【待補】`; never invent numbers / IDs / dates / conclusions
  — and the red-team itself may not invent **accusations** (the evidence gate enforces this).
- The deterministic checks are the only HARD signal; the LLM pass is advisory + capped, **in code**.
- The report is a **DRAFT**. A human owns approve / reject. Never auto-approve, never auto-file.
- Real enforcement lives in the code (clamp / evidence-gate / cap) and the optional Stop-hook —
  not in this prose.
