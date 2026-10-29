# SPDX-License-Identifier: MIT
"""hooks.json checks: valid JSON + referenced scripts exist (HARD); SessionStart wired +
Stop always-exit-0 heuristic (SOFT, strict). hooks/ is optional — absent dir is clean.
Both hook forms are understood: shell form (one `command` string) and exec form (`command` is
the executable, `args` a list of strings, no shell) — scripts are looked up in either."""
import json
import os
import re
from ..model import Finding

_PYREF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/(\S+?\.py)")


def check(plugin_dir, strict):
    name = os.path.basename(os.path.normpath(plugin_dir))
    hpath = os.path.join(plugin_dir, "hooks", "hooks.json")
    if not os.path.exists(hpath):
        return []
    try:
        with open(hpath, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        return [Finding("hooks:json", "hooks", "HARD", name, "hooks/hooks.json",
                        f"invalid JSON: {e}")]
    findings = []
    events = data.get("hooks", {})
    if strict and "SessionStart" not in events:
        findings.append(Finding("hooks:sessionstart", "hooks", "SOFT", name, "hooks/hooks.json",
                                "no SessionStart health-check wired"))
    for ev, entries in events.items():
        for entry in entries:
            for h in entry.get("hooks", []):
                cmd = h.get("command", "")
                args = h.get("args")
                if args is not None and not (isinstance(args, list)
                                             and all(isinstance(a, str) for a in args)):
                    findings.append(Finding(f"hooks:args:{ev}", "hooks", "HARD", name,
                                            "hooks/hooks.json",
                                            f"{ev} hook: exec-form `args` must be a list of strings"))
                    args = None
                for rel in _PYREF.findall(" ".join([cmd] + (args or []))):
                    spath = os.path.join(plugin_dir, rel)
                    if not os.path.exists(spath):
                        findings.append(Finding(f"hooks:missing:{rel}", "hooks", "HARD", name,
                                                "hooks/hooks.json", f"hook references missing script {rel}"))
                    elif strict and ev == "Stop":
                        with open(spath, encoding="utf-8") as f:
                            src = f.read()
                        if "exit(0)" not in src and "return 0" not in src:
                            findings.append(Finding(f"hooks:exit0:{rel}", "hooks", "SOFT", name, rel,
                                                    "Stop hook should always exit 0 (signal via stdout JSON)"))
    return findings
