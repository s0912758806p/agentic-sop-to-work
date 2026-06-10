# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Example AI skill (stand-in): echoes the input's `source` values into `claims` WITH a trace entry for
each (the no-fabrication pattern). Swap run() for a real LLM call — but KEEP the trace_gate so any value
the model invents (not traceable to the input) is blocked."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import kit  # noqa: E402

DEPS = [{"kind": "python", "min": "3.8"}]
WHO = "ai_claims"


def run(inp, out):
    src = kit.read_artifact(inp).get("data", {}).get("source", [])
    trace = [{"value": str(v), "source": os.path.basename(inp), "locator": f"source[{i}]"}
             for i, v in enumerate(src)]
    kit.write_artifact(kit.artifact("claims@1", WHO, {"claims": list(src)}, trace), out)


if __name__ == "__main__":
    kit.skill_main(DEPS, WHO, run)
