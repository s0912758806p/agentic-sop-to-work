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
