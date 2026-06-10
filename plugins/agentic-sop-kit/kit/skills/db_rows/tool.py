# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Example DB skill (stand-in): emits query rows + a precomputed total. Swap run() for a real psql/SQL
query; keep a recompute_gate so the reported total is re-derived and verified."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import kit  # noqa: E402

DEPS = [{"kind": "python", "min": "3.8"}]
WHO = "db_rows"


def run(inp, out):
    rows = [10, 20, 30]
    kit.write_artifact(kit.artifact("rows@1", WHO, {"rows": rows, "total": sum(rows)}, []), out)


if __name__ == "__main__":
    kit.skill_main(DEPS, WHO, run)
