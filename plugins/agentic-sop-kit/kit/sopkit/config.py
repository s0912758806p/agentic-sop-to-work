# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""The single reader of every SOPKIT_* environment variable (and of the plugin's userConfig).

Each value is read at CALL time, never at import time: before v1.11.0 `SOPKIT_ROOT` and
`SOPKIT_SCHEMA_DIR` were frozen when lib/kit.py / lib/schema.py were first imported, so
setting them later in the same process silently did nothing.

Pure stdlib, imports nothing from the kit — the hooks use it too, and a hook must keep
working even when the rest of the engine is broken.

    SOPKIT_ROOT                    kit root (default: the directory holding sopkit/)
    SOPKIT_SCHEMA_DIR              typed-edge declarations (default: <root>/workflow/schemas)
    SOPKIT_MAX_FIX_RETRIES         fix-loop / Stop-hook retry ceiling (3)
    SOPKIT_STALL_WINDOW            identical failures that count as a stall (2; 0 disables)
    SOPKIT_STATE_KEEP_RUNS         run dirs kept by run.py --prune (20)
    SOPKIT_STATE_KEEP_LOG          regression_log.jsonl lines kept (200; floor 50 in loop.state)
    SOPKIT_HEALTH_SLOWDOWN_FACTOR  slowdown advisory threshold (2.0)
    SOPKIT_HEALTH_FLAKY_WINDOW     recent runs inspected for flakiness (10)

Three knobs are also plugin userConfig options (.claude-plugin/plugin.json): max_fix_retries,
stall_window, keep_runs. Claude Code hands them to hooks as CLAUDE_PLUGIN_OPTION_<KEY>, and
the sop-flow skill forwards them to run.py the same way. Precedence: SOPKIT_* env >
CLAUDE_PLUGIN_OPTION_* > default. An option value that does not parse (empty, or a literal
`${user_config.x}` left unsubstituted in a bootstrap-generated project command) is ignored.

Default run dir (runs_base): --out-base > $CLAUDE_PLUGIN_DATA/runs when this kit IS the
installed plugin's kit (its parent holds .claude-plugin/plugin.json and CLAUDE_PLUGIN_DATA
is set) > <kit>/runs. <kit>/runs inside an installed plugin is deprecated: the plugin cache
is replaced on every update, taking the runs with it. A bootstrapped project's kit keeps
<project>/agentic-sop-kit/runs — that is project data, not cache.
"""
import os

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _env(name, default, cast):
    raw = os.environ.get(name)
    return cast(raw) if raw not in (None, "") else default


def _option(key, cast):
    """Plugin userConfig value, or None when absent / unsubstituted / unparsable."""
    raw = (os.environ.get("CLAUDE_PLUGIN_OPTION_" + key.upper()) or "").strip()
    if not raw or "${" in raw:
        return None
    try:
        return cast(float(raw)) if cast is int else cast(raw)
    except ValueError:
        return None


def _knob(env, option, default, cast):
    if os.environ.get(env) not in (None, ""):
        return cast(os.environ[env])
    v = _option(option, cast)
    return default if v is None else v


def kit_root():
    return os.environ.get("SOPKIT_ROOT") or _PKG_ROOT


def schema_dir():
    return os.environ.get("SOPKIT_SCHEMA_DIR") or os.path.join(kit_root(), "workflow", "schemas")


def max_fix_retries():
    return _knob("SOPKIT_MAX_FIX_RETRIES", "max_fix_retries", 3, int)


def stall_window():
    return _knob("SOPKIT_STALL_WINDOW", "stall_window", 2, int)


def keep_runs():
    return _knob("SOPKIT_STATE_KEEP_RUNS", "keep_runs", 20, int)


def keep_log():
    return _env("SOPKIT_STATE_KEEP_LOG", 200, int)


def health_slowdown_factor():
    return _env("SOPKIT_HEALTH_SLOWDOWN_FACTOR", 2.0, float)


def health_flaky_window():
    return _env("SOPKIT_HEALTH_FLAKY_WINDOW", 10, int)


def in_installed_plugin():
    """True when this kit is the kit/ of a plugin (not a bootstrapped project copy)."""
    parent = os.path.dirname(os.path.abspath(kit_root()))
    return os.path.isfile(os.path.join(parent, ".claude-plugin", "plugin.json"))


def runs_base(out_base=None):
    """(base dir for run dirs, deprecation notice or None). See the module docstring."""
    if out_base:
        return out_base, None
    if in_installed_plugin():
        data = os.environ.get("CLAUDE_PLUGIN_DATA")
        if data and "${" not in data:
            return os.path.join(data, "runs"), None
        legacy = os.path.join(kit_root(), "runs")
        return legacy, ("DEPRECATED: writing runs into the plugin cache (" + legacy + "), which is "
                        "replaced on every plugin update. Pass --out-base, or run through the plugin "
                        "so $CLAUDE_PLUGIN_DATA/runs is used. ｜ run 寫在 plugin 快取，更新即消失（v2.0 移除）")
    return os.path.join(kit_root(), "runs"), None
