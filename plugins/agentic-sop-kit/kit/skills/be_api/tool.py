# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Example BE skill (stand-in): emits a fixed 'API response'. Swap run() for a real curl/HTTP call;
keep a schema_gate so a malformed response is caught."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import kit  # noqa: E402

DEPS = [{"kind": "python", "min": "3.8"}]
WHO = "be_api"


def run(inp, out):
    kit.write_artifact(kit.artifact("api@1", WHO, {"id": 1, "name": "widget", "price": 9.99}, []), out)


if __name__ == "__main__":
    kit.skill_main(DEPS, WHO, run)
