---
description: Lint a record / dataset / kit run for ALCOA+ data integrity (attribution, contemporaneity, completeness, accuracy, consistency). Deterministic findings + a human-judgment checklist; the report is a DRAFT, the human owns the verdict.
argument-hint: "<run_dir> | --record <file> --contract <.alcoa.json>"
---

# /alcoa-guard

Invoke the alcoa-guard linter on `$ARGUMENTS`.

1. If the path is a kit run dir → `python3 -m alcoaguard.review --run-dir <dir>` (FULL).
2. If it is a record file → `python3 -m alcoaguard.review --record <file> --contract <.alcoa.json>` (DEGRADED; ask for the contract if absent).
3. With no args → run the bundled `clean` example to demonstrate.

Present the findings + human-judgment checklist verbatim, then STOP for human review.
