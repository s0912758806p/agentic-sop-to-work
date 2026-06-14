---
description: Get an independent adversarial SECOND OPINION on a finished DRAFT — check its claims against its evidence (no fabrication, no overreach) before a human approves. FULL mode reads an agentic-sop-kit run dir's trace; DEGRADED mode reviews any document with supplied inputs.
argument-hint: "<run_dir> | <doc> --inputs <file...> | (no args = bundled demo)"
---

# /second-opinion — adversarial honesty review (DRAFT, human owns the verdict)

You are an **independent, skeptical second reader**. Your job is to attack a finished
DRAFT and find where its **claims are not backed by its evidence** — fabricated/transcribed
numbers, invented identifiers/dates that should be `【待補】`, wrong PASS/FAIL verdicts, and
conclusions the data don't support. You **review the output's honesty**, NOT source-code
quality (that is `/code-review`) and NOT the workflow architecture (that is
`agentic-workflow-audit`). You **never** approve or reject — a human owns the verdict.

`$ARGUMENTS`

## Determine the mode
- A directory containing `run_manifest.json` → **FULL** mode (uses the run's `trace`).
- A file path (+ `--inputs <file...>`) → **DEGRADED** mode (you supply the sources).
- No arguments → run the bundled cross-domain **demo** (`secondop/examples/pharma_stability`).

Let `ROOT="${CLAUDE_PLUGIN_ROOT}"` and `OUT="${CLAUDE_PROJECT_DIR:-.}/.second-opinion-runs"`.

## Step 1 — deterministic pass (zero-LLM, code-owned)
Run the deterministic checker. It writes `second_opinion.{json,md}` and an LLM envelope
`llm_input.json` into the run's output dir.

- FULL:     `PYTHONPATH="$ROOT" python3 -m secondop.review --run-dir <run_dir> --out-base "$OUT"`
- DEGRADED: `PYTHONPATH="$ROOT" python3 -m secondop.review --doc <doc> --inputs <file...> --out-base "$OUT"`

Note the output dir it prints (the `wrote …` lines). Call it `RUNOUT`.

## Step 2 — advisory adversarial pass (you, capped, ADVISORY only)
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

## Step 3 — fold-in (code-enforced clamp / evidence-gate / cap)
Re-run review with your candidates. The code clamps them to SOFT/advisory, drops any that
fail the evidence gate, suppresses re-litigation of settled slots, and enforces the pass cap
(`SECONDOP_MAX_LLM_PASSES`, default 1):

- FULL:     `PYTHONPATH="$ROOT" python3 -m secondop.review --run-dir <run_dir> --advisory "$RUNOUT/llm_candidates.json" --out-base "$OUT"`
- DEGRADED: `PYTHONPATH="$ROOT" python3 -m secondop.review --doc <doc> --inputs <file...> --advisory "$RUNOUT/llm_candidates.json" --out-base "$OUT"`

## Step 4 — present + STOP (human owns the verdict)
Show the final `RUNOUT/second_opinion.md`. Summarize: HARD (deterministic) vs SOFT
(advisory) counts, and any accusations the evidence gate dropped (transparency that the
red-team was itself checked). Then **STOP** with an explicit, human-owned decision —
do not approve, reject, or file anything yourself:

> ✋ **Human decision required.** Second Opinion is advisory and does not decide.
> Choose: **[Approve the draft]** · **[Send back for fix]** · **[Override a specific finding (give a reason)]**

## Iron rules (this command honors them)
- Facts only from inputs; unknowns are `【待補】`; never invent numbers/IDs/dates/conclusions.
- The deterministic checks are the only HARD signal; the LLM pass is advisory + capped (in code).
- The report is a **DRAFT**; the human owns approve/reject. Never auto-approve, never auto-file.
