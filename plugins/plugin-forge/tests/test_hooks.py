import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge.rules import hooks

def _hooks(d, obj):
    os.makedirs(os.path.join(d, "hooks"), exist_ok=True)
    with open(os.path.join(d, "hooks", "hooks.json"), "w", encoding="utf-8") as f:
        if isinstance(obj, str):
            f.write(obj)
        else:
            json.dump(obj, f)

class TestHooks(unittest.TestCase):
    def test_no_hooks_dir_is_ok(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(hooks.check(d, strict=False), [])

    def test_invalid_json_is_hard(self):
        with tempfile.TemporaryDirectory() as d:
            _hooks(d, "{ not json")
            out = hooks.check(d, strict=False)
            self.assertTrue(any(f.severity == "HARD" and "invalid JSON" in f.detail for f in out))

    def test_strict_warns_no_sessionstart(self):
        with tempfile.TemporaryDirectory() as d:
            _hooks(d, {"hooks": {"Stop": [{"matcher": "", "hooks": []}]}})
            out = hooks.check(d, strict=True)
            self.assertTrue(any(f.severity == "SOFT" and "SessionStart" in f.detail for f in out))

    def test_referenced_missing_script_is_hard(self):
        with tempfile.TemporaryDirectory() as d:
            _hooks(d, {"hooks": {"SessionStart": [{"matcher": "startup", "hooks": [
                {"type": "command", "command": 'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/nope.py"'}]}]}})
            out = hooks.check(d, strict=False)
            self.assertTrue(any("nope.py" in f.detail and f.severity == "HARD" for f in out))

    def _exec(self, d, args, ev="SessionStart"):
        _hooks(d, {"hooks": {ev: [{"matcher": "", "hooks": [
            {"type": "command", "command": "python3", "args": args}]}]}})

    def test_exec_form_script_is_checked(self):
        with tempfile.TemporaryDirectory() as d:
            self._exec(d, ["${CLAUDE_PLUGIN_ROOT}/hooks/missing.py"])
            out = hooks.check(d, strict=False)
            self.assertTrue(any(f.severity == "HARD" and "missing.py" in f.detail for f in out))
            with open(os.path.join(d, "hooks", "missing.py"), "w", encoding="utf-8") as f:
                f.write("import sys\nsys.exit(0)\n")
            self.assertEqual(hooks.check(d, strict=True), [])

    def test_exec_form_args_must_be_string_list(self):
        with tempfile.TemporaryDirectory() as d:
            self._exec(d, "not-a-list")
            out = hooks.check(d, strict=False)
            self.assertTrue(any(f.severity == "HARD" and "args" in f.detail for f in out))

    def test_exec_form_stop_hook_exit0_heuristic(self):
        with tempfile.TemporaryDirectory() as d:
            self._exec(d, ["${CLAUDE_PLUGIN_ROOT}/hooks/stop.py"], ev="Stop")
            with open(os.path.join(d, "hooks", "stop.py"), "w", encoding="utf-8") as f:
                f.write("print('x')\n")
            out = hooks.check(d, strict=True)
            self.assertTrue(any(f.severity == "SOFT" and "exit 0" in f.detail for f in out))

if __name__ == "__main__":
    unittest.main()
