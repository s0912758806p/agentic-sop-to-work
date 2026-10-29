# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Meta-test: the plugin hooks (../hooks/*.py) and the project hooks bootstrap used to install
must never BOTH fire. Before v1.10.1 a bootstrapped project with the plugin installed ran
verify.py twice per stop and shared tests/.retry_count, halving the retry cap.

Contract under test:
  • plugin Stop hook no-ops when the project's .claude/settings(.local).json already
    registers stop_regression.py; otherwise it runs the project's verify.py.
  • plugin SessionStart hook no-ops when the project already registers check_deps.py.
  • bootstrap.py no longer writes hooks into the project (the plugin hook owns them);
    --with-hooks keeps the manual path for users without the plugin.

The project's verify.py / check_deps.py are replaced by marker writers, so "did it run" is
observed directly instead of inferred from output. Not registered (it lives beside the
plugin, which a bootstrapped project does not have); CI runs it explicitly.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_HOOKS = os.path.join(os.path.dirname(KIT), "hooks")
sys.path.insert(0, KIT)  # kit root → sopkit
from sopkit.kit import copy_kit  # noqa: E402

MARKER_SCRIPT = ("import os, sys\n"
                 "open(os.path.join(os.path.dirname(os.path.abspath(__file__)), %r), 'w').close()\n"
                 "sys.exit(0)\n")


def _settings(proj, hooks, name="settings.json"):
    d = os.path.join(proj, ".claude")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        json.dump({"hooks": hooks}, f)


def _cmd(command):
    return [{"matcher": "", "hooks": [{"type": "command", "command": command}]}]


@unittest.skipUnless(os.path.isdir(PLUGIN_HOOKS), "plugin hooks/ not beside this kit")
class PluginHooksDedupe(unittest.TestCase):
    def setUp(self):
        self.proj = tempfile.mkdtemp()
        self.kit = os.path.join(self.proj, "agentic-sop-kit")
        copy_kit(KIT, self.kit)
        with open(os.path.join(self.kit, "tests", "verify.py"), "w", encoding="utf-8") as f:
            f.write(MARKER_SCRIPT % ".verify_ran")
        with open(os.path.join(self.kit, "check_deps.py"), "w", encoding="utf-8") as f:
            f.write(MARKER_SCRIPT % ".check_deps_ran")

    def tearDown(self):
        shutil.rmtree(self.proj, ignore_errors=True)

    def _hook(self, name):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.proj)
        return subprocess.run([sys.executable, os.path.join(PLUGIN_HOOKS, name)],
                              input=json.dumps({"stop_hook_active": False}),
                              env=env, cwd=self.proj, capture_output=True, text=True)

    def _ran(self, marker):
        return os.path.exists(os.path.join(self.kit, "tests", marker)) or \
            os.path.exists(os.path.join(self.kit, marker))

    def test_stop_runs_when_project_has_no_hook(self):
        r = self._hook("stop_gate.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self._ran(".verify_ran"), "plugin Stop hook should run the project's verify")

    def test_stop_noops_when_project_registers_stop_regression(self):
        _settings(self.proj, {"Stop": _cmd(
            'python3 "$CLAUDE_PROJECT_DIR/agentic-sop-kit/hooks/stop_regression.py"')})
        r = self._hook("stop_gate.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self._ran(".verify_ran"), "double-run: project hook already covers Stop")

    def test_stop_noops_on_local_settings_too(self):
        _settings(self.proj, {"Stop": _cmd("python3 agentic-sop-kit/hooks/stop_regression.py")},
                  name="settings.local.json")
        self._hook("stop_gate.py")
        self.assertFalse(self._ran(".verify_ran"))

    def test_session_runs_when_project_has_no_hook(self):
        r = self._hook("session_check.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self._ran(".check_deps_ran"))

    def test_session_noops_when_project_registers_check_deps(self):
        _settings(self.proj, {"SessionStart": _cmd(
            'python3 "$CLAUDE_PROJECT_DIR/agentic-sop-kit/check_deps.py"')})
        self._hook("session_check.py")
        self.assertFalse(self._ran(".check_deps_ran"), "double-run: project hook already covers SessionStart")

    def test_unreadable_settings_do_not_suppress_the_gate(self):
        d = os.path.join(self.proj, ".claude")
        os.makedirs(d)
        with open(os.path.join(d, "settings.json"), "w", encoding="utf-8") as f:
            f.write("{not json")
        self._hook("stop_gate.py")
        self.assertTrue(self._ran(".verify_ran"), "a broken settings file must not silently disable the gate")



@unittest.skipUnless(os.path.isdir(PLUGIN_HOOKS), "plugin hooks/ not beside this kit")
class PythonVersionGuard(unittest.TestCase):
    """The hook entry scripts no-op with a clear message on a too-old interpreter."""

    def test_old_python_noops_with_message(self):
        for name in ("stop_gate.py", "session_check.py"):
            path = os.path.join(PLUGIN_HOOKS, name)
            code = ("import sys\nsys.version_info = (3, 7, 0, 'final', 0)\n"
                    f"sys.argv = [{path!r}]\n__file__ = {path!r}\n"
                    f"exec(compile(open({path!r}, encoding='utf-8').read(), {path!r}, 'exec'))\n")
            r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                               env=dict(os.environ, CLAUDE_PROJECT_DIR=tempfile.gettempdir()))
            self.assertEqual(r.returncode, 0, name + r.stderr)
            self.assertIn("Python >= 3.8", r.stderr, name)
            self.assertEqual(r.stdout, "", name)

    def test_hooks_json_uses_exec_form(self):
        with open(os.path.join(PLUGIN_HOOKS, "hooks.json"), encoding="utf-8") as f:
            hooks = json.load(f)["hooks"]
        for event, entries in hooks.items():
            for e in entries:
                for h in e["hooks"]:
                    self.assertIn("args", h, f"{event}: use exec form (command + args), no shell quoting")
                    self.assertNotIn(" ", h["command"], event)


class BootstrapNoLongerWritesHooks(unittest.TestCase):
    def setUp(self):
        self.proj = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.proj, ignore_errors=True)

    def _bootstrap(self, *extra):
        return subprocess.run([sys.executable, os.path.join(KIT, "bootstrap.py"),
                               "--project", self.proj, *extra], capture_output=True, text=True)

    def _hooks(self):
        p = os.path.join(self.proj, ".claude", "settings.json")
        if not os.path.exists(p):
            return {}
        with open(p, encoding="utf-8") as f:
            return json.load(f).get("hooks", {})

    def test_default_writes_no_hooks(self):
        r = self._bootstrap()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._hooks(), {}, "the plugin hook owns Stop/SessionStart now")

    def test_with_hooks_keeps_manual_path(self):
        r = self._bootstrap("--with-hooks")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("stop_regression.py", json.dumps(self._hooks()))

    def test_command_is_generated_from_the_plugin_skill(self):
        skill = os.path.join(os.path.dirname(KIT), "skills", "sop-flow", "SKILL.md")
        if not os.path.exists(skill):
            self.skipTest("plugin skills/ not beside this kit")
        r = self._bootstrap()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(os.path.join(self.proj, ".claude", "commands", "sop-flow.md"), encoding="utf-8") as f:
            cmd = f.read()
        with open(skill, encoding="utf-8") as f:
            src = f.read()
        self.assertTrue(cmd.startswith("---\ndescription:"), cmd[:80])
        self.assertNotIn("disable-model-invocation", cmd)
        self.assertIn("GENERATED", cmd)
        body = src.split("\n---\n", 1)[1]
        self.assertIn(body, cmd, "the command body must be the skill body, verbatim")

    def test_no_hooks_flag_still_accepted(self):
        r = self._bootstrap("--no-hooks")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._hooks(), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
