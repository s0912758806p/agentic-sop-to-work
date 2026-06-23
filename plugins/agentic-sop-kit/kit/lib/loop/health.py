# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Deterministic runtime-health reader for the regression loop (Loop Engineering cut #2).

Pure functions over already-parsed inputs — NO file I/O, NO LLM. The caller
(tests/verify.py) owns reading the registry / regression log / baseline and acting:
  H1 coverage (HARD)     — registered-test count dropped below the persisted baseline.
  A2 slowdown (advisory) — median total_seconds of recent full runs rose >= factor x prior baseline.
  A3 flaky (advisory)    — a test flips pass/fail within the recent window.
"""
import statistics


def count_registered_tests(registry):
    """Distinct test files declared in the registry (skills' tests union integration tests)."""
    paths = set()
    for s in (registry.get("skills") or {}).values():
        paths.update(s.get("tests", []))
    paths.update((registry.get("integration") or {}).get("tests", []))
    return len(paths)


def check_coverage(current, baseline):
    """H1 (HARD): registered-test count regressed below baseline. None on first run / no regression."""
    if baseline is None or current >= baseline:
        return None
    return {"signal": "coverage", "current": current, "baseline": baseline,
            "message": f"registered tests dropped {baseline} -> {current} | test coverage shrank"}


def _all_run_seconds(entries):
    """total_seconds for full-run ('all') entries, in order — the only comparable runs."""
    out = []
    for e in entries:
        if e.get("trigger") == "all":
            secs = (e.get("metrics") or {}).get("total_seconds")
            if isinstance(secs, (int, float)):
                out.append(secs)
    return out


def check_slowdown(entries, recent=3, base=5, factor=2.0):
    """A2 (advisory): recent full-run median >= factor x the prior baseline median."""
    secs = _all_run_seconds(entries)
    if len(secs) < recent + base:
        return None
    r_med = statistics.median(secs[-recent:])
    b_med = statistics.median(secs[-(recent + base):-recent])
    if b_med > 0 and r_med >= factor * b_med:
        return {"signal": "slowdown", "recent_median_s": round(r_med, 3),
                "baseline_median_s": round(b_med, 3),
                "message": f"full-run time {b_med:.2f}s -> {r_med:.2f}s (>= {factor}x) | slowdown"}
    return None


def check_flaky(entries, window=10):
    """A3 (advisory): a test path shows both pass and fail within the recent window."""
    seen = {}
    for e in entries[-window:]:
        for rec in (e.get("unit", []) + e.get("integration", [])):
            t, p = rec.get("test"), rec.get("passed")
            if t is None or p is None:
                continue
            seen.setdefault(t, set()).add(bool(p))
    flaky = sorted(t for t, outcomes in seen.items() if len(outcomes) > 1)
    if not flaky:
        return None
    return {"signal": "flaky", "tests": flaky,
            "message": f"{len(flaky)} flaky test(s): {', '.join(flaky)} | unstable tests"}


def assess_health(registry, log_entries, baseline, *, recent=3, base=5, factor=2.0, window=10):
    """Run all checks. Returns {'hard': [...], 'advisory': [...]}. Pure; deterministic."""
    hard, advisory = [], []
    cov = check_coverage(count_registered_tests(registry), baseline)
    if cov:
        hard.append(cov)
    for finding in (check_slowdown(log_entries, recent, base, factor),
                    check_flaky(log_entries, window)):
        if finding:
            advisory.append(finding)
    return {"hard": hard, "advisory": advisory}
