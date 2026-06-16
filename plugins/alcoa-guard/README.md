# alcoa-guard

Deterministic **ALCOA+ data-integrity linter** — a companion in the agentic-sop-to-work suite.
Checks the mechanically-verifiable slice of ALCOA+ in code; surfaces the human-judgment slice
as a checklist it never auto-concludes. Runs standalone (`--record … --contract …`) or snaps
onto an agentic-sop-kit run (`--run-dir …`). Output is a DRAFT — a human owns the verdict.

```bash
python3 -m alcoaguard.review --record entries.csv --contract .alcoa.json
python3 -m alcoaguard.review --run-dir <kit-run-dir>
```
