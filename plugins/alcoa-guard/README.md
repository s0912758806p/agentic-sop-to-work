# alcoa-guard

Deterministic **ALCOA+ data-integrity linter** — a companion in the agentic-sop-to-work suite.
Checks the mechanically-verifiable slice of ALCOA+ in code; surfaces the human-judgment slice
as a checklist it never auto-concludes. Runs standalone (`--record … --contract …`) or snaps
onto an agentic-sop-kit run (`--run-dir …`). Output is a DRAFT — a human owns the verdict.

**Install** (Claude Code):
```
/plugin marketplace add s0912758806p/agentic-sop-to-work
/plugin install alcoa-guard@agentic-sop-to-work
/reload-plugins
```
Requires Python 3.8+ as `python3` (stdlib only).

```bash
python3 -m alcoaguard.review --record entries.csv --contract .alcoa.json
python3 -m alcoaguard.review --run-dir <kit-run-dir>
```

- **Invoke** as `/alcoa-guard:alcoa-guard [args]` — a skill (no `commands/` since v0.3.0) that also
  auto-triggers on intent.
- **Output** lands in `<base>/<run_id>/` (FULL) or `<base>/degraded/`, never inside the reviewed run
  dir. `<base>` is `${CLAUDE_PLUGIN_DATA}/.alcoa-guard-runs` when Claude Code sets it (persists
  across plugin updates), else `./.alcoa-guard-runs`; `--out-base <dir>` names the exact output dir.
- **FULL mode reads only finished runs.** The run dir is read through
  `alcoaguard/_core/run_contract.py`, the suite's single definition of a kit run dir (vendored
  from the repo's `shared/sopcore/` — never edit `_core/`, edit the source and run
  `tools/sync_core.py`). A run not in `OK_FOR_REVIEW` (e.g. `FAILED`) is refused with exit 2.
- **`【待補】` is a finding here.** A required field still holding the placeholder is not
  Complete. (second-opinion-honesty deliberately does the opposite and skips it as an honest
  blank; both read the same marker from `_core/markers.py`.)
- **Recompute** (Accurate) uses the suite's shared arithmetic: an empty list fails, sums use
  `math.fsum`, and a mismatch reads `recomputed <op>=X vs stated Y`.
