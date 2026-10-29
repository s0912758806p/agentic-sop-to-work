# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Golden run-dir comparison: the engine's on-disk output is a CONTRACT (second-opinion and
alcoa-guard read it), so a refactor must leave it byte-identical.

tests/golden/<scenario>/ holds every non-hidden file a run wrote, captured from the
engine BEFORE the v1.11.0 split of run.py (i.e. main @ v1.10.1). Scenarios cover the
bundled flow, every workflow/examples/*.json, and each manifest shape the runner can
emit (gate failure, fix_exhausted, stall, already_stalled, topology_invalid, back-edge
stall / revisits exhausted, unreadable branch artifact) — JSON key ORDER included.

Run-specific text is normalised before comparing: the temp out-base → <BASE>, the kit dir
→ <KIT>, and the interpreter version that fe.json's `python3 --version` prints. Line
endings compare as "\n" on both sides: the kit writes text mode (CRLF on Windows) and a
Windows checkout may turn the goldens into CRLF too — neither is a contract change. On
Windows the path separator is normalised to "/" as well, for the same reason.
Regenerate ONLY for an intended contract change: python3 test_golden.py --regen
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = os.path.join(KIT, "workflow", "run.py")
EX = os.path.join(KIT, "workflow", "examples")
GOLDEN = os.path.join(KIT, "tests", "golden")

EMIT = ("import json,argparse\n"
        "a=argparse.ArgumentParser();a.add_argument('--in');a.add_argument('--out');x=a.parse_args()\n"
        "json.dump({'schema':'t@1','produced_by':%r,'data':%r,'trace':[]}, open(x.out,'w'))\n")


def _tool(d, name, data):
    p = os.path.join(d, name + ".py")
    with open(p, "w", encoding="utf-8") as f:
        f.write(EMIT % (name, data))
    return p


def _flow(d, name, steps, input_default):
    p = os.path.join(d, name + ".flow.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"name": name, "input_default": input_default, "steps": steps}, f)
    return p


def _fixtures(d):
    """name -> (flow_path, [extra args per invocation]) — the LAST invocation's run dir is compared."""
    emit = _tool(d, "emit", {"id": 1})
    loop = _tool(d, "loop", {"again": True})
    gate = {"type": "schema_gate", "args": {"required": ["id", "name"]}}
    failing = _flow(d, "always-fails", [
        {"skill": "emit", "tool": emit, "in": "$INPUT", "out": "$RUN/a.json", "gate": gate}], emit)
    backedge = _flow(d, "back-edge", [
        {"skill": "loop", "tool": loop, "in": "$INPUT", "out": "$RUN/l.json"},
        {"branch": "$RUN/l.json", "cases": [
            {"when": {"path": "again", "op": "==", "value": True}, "goto": "loop",
             "back": True, "max_revisits": 1},
            {"default": True, "goto": "done"}]},
        {"skill": "done", "tool": emit, "in": "$INPUT", "out": "$RUN/d.json"}], loop)
    unreachable = _flow(d, "unreachable", [
        {"skill": "emit", "tool": emit, "in": "$INPUT", "out": "$RUN/a.json"},
        {"branch": "$RUN/a.json", "cases": [{"default": True, "goto": "tail"}]},
        {"skill": "dead", "tool": emit, "in": "$INPUT", "out": "$RUN/dead.json"},
        {"skill": "tail", "tool": emit, "in": "$INPUT", "out": "$RUN/t.json"}], emit)
    missing = _flow(d, "missing-branch-artifact", [
        {"skill": "emit", "tool": emit, "in": "$INPUT", "out": "$RUN/a.json"},
        {"branch": "$RUN/nope.json", "cases": [{"default": True, "goto": "tail"}]},
        {"skill": "tail", "tool": emit, "in": "$INPUT", "out": "$RUN/t.json"}], emit)
    no0 = ["--stall-window", "0"]
    return {
        "fail_gate": (failing, [no0]),
        "fail_exhausted": (failing, [no0 + ["--max-fix-retries", "0"]] * 2),
        "fail_stall": (failing, [[]] * 2),
        "fail_already_stalled": (failing, [[]] * 3),
        "fail_topology": (unreachable, [[]]),
        "fail_backedge_exhausted": (backedge, [no0]),
        "fail_backedge_stall": (backedge, [[]]),
        "fail_branch_artifact": (missing, [[]]),
    }


def _scenarios(d):
    out = {"flow": (os.path.join(KIT, "workflow", "flow.json"), [[]])}
    for fn in sorted(os.listdir(EX)):
        if fn.endswith(".json"):
            out["example_" + fn[:-5]] = (os.path.join(EX, fn), [[]])
    out.update(_fixtures(d))
    return out


def _normalise(text, base, sep=os.sep):
    for root, tag in ((base, "<BASE>"), (KIT, "<KIT>")):
        for form in (root, json.dumps(root)[1:-1]):
            text = text.replace(form, tag)
    if sep == "\\":
        # Windows joins run paths with "\" (JSON-escaped as "\\"); the goldens use "/".
        text = text.replace("\\\\", "/").replace("\\", "/")
    return re.sub(r"Python \d+\.\d+\.\d+\S*", "Python <VER>", text)


def _collect(run_dir, base):
    files = {}
    for fn in sorted(os.listdir(run_dir)):
        p = os.path.join(run_dir, fn)
        if fn.startswith(".") or not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8") as f:
            files[fn] = _normalise(f.read(), base)
    return files


def _hermetic_env():
    """Knobs from the caller's environment (e.g. the Stop-hook meta-test exports
    SOPKIT_MAX_FIX_RETRIES=2) would change manifest values: run on defaults only."""
    return {k: v for k, v in os.environ.items()
            if not k.startswith(("SOPKIT_", "CLAUDE_PLUGIN_OPTION_", "CLAUDE_PLUGIN_DATA"))}


def produce():
    """{scenario: {filename: normalised text}} from the engine in this tree."""
    result = {}
    env = _hermetic_env()
    base = tempfile.mkdtemp()
    try:
        fx = os.path.join(base, "fixtures")
        os.makedirs(fx)
        for name, (flow, invocations) in _scenarios(fx).items():
            for extra in invocations:
                subprocess.run([sys.executable, RUN, "--flow", flow, "--out-base", base,
                                "--run-id", name, *extra], capture_output=True, text=True, env=env)
            result[name] = _collect(os.path.join(base, name), base)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return result


def _load_golden():
    out = {}
    for name in sorted(os.listdir(GOLDEN)):
        d = os.path.join(GOLDEN, name)
        if os.path.isdir(d):
            out[name] = {}
            for fn in sorted(os.listdir(d)):
                with open(os.path.join(d, fn), encoding="utf-8") as f:   # universal newlines
                    out[name][fn] = f.read()
    return out


class GoldenRunDirs(unittest.TestCase):
    def test_windows_paths_normalise_to_the_golden_form(self):
        base = "C:\\t\\x"
        raw = json.dumps({"out": base + "\\fail_gate/a.json"}) + "\n" + base + "\\flow/report.md"
        self.assertEqual(_normalise(raw, base, sep="\\"),
                         '{"out": "<BASE>/fail_gate/a.json"}\n<BASE>/flow/report.md')

    def test_run_dirs_match_golden(self):
        golden = _load_golden()
        self.assertTrue(golden, "tests/golden/ is empty (fail-closed) — regenerate on purpose")
        now = produce()
        self.assertEqual(sorted(now), sorted(golden), "scenario set drifted from tests/golden/")
        for name in golden:
            with self.subTest(scenario=name):
                self.assertEqual(sorted(now[name]), sorted(golden[name]), f"{name}: file set changed")
                for fn, text in golden[name].items():
                    self.assertEqual(now[name][fn], text, f"{name}/{fn} is not byte-identical")


def regen():
    shutil.rmtree(GOLDEN, ignore_errors=True)
    for name, files in produce().items():
        d = os.path.join(GOLDEN, name)
        os.makedirs(d)
        for fn, text in files.items():
            with open(os.path.join(d, fn), "w", encoding="utf-8", newline="") as f:
                f.write(text)
    print(f"regenerated {GOLDEN}")


if __name__ == "__main__":
    if "--regen" in sys.argv:
        regen()
    else:
        unittest.main(verbosity=2)
