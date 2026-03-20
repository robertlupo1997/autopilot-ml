---
phase: 10
slug: fix-runtime-wiring-bugs
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-20
validated: 2026-03-20
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml (pytest section) |
| **Quick run command** | `python3 -m pytest tests/mlforge/test_engine.py tests/mlforge/test_swarm.py tests/mlforge/test_cli.py -x -q` |
| **Full suite command** | `python3 -m pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/test_engine.py tests/mlforge/test_swarm.py tests/mlforge/test_cli.py -x -q`
- **After every plan wave:** Run `python3 -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | INTL-01, INTL-02 | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestIntelligenceIntegration::test_compute_baselines_called_before_loop -x` | ✅ | ✅ green |
| 10-01-02 | 01 | 1 | INTL-05 | unit | `python3 -m pytest tests/mlforge/test_cli.py -x -k "enable_drafts"` | ✅ | ✅ green |
| 10-01-03 | 01 | 1 | SWARM-01 | unit | `python3 -m pytest tests/mlforge/test_swarm.py::TestBuildAgentCommand -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/mlforge/test_cli.py` — `TestEnableDraftsFlag` (2 tests) for `--enable-drafts` flag (INTL-05)
- [x] `tests/mlforge/test_engine.py` — `test_compute_baselines_called_before_loop` uses function-based prepare.py with CSV (INTL-01, INTL-02)
- [x] `tests/mlforge/test_swarm.py` — `TestBuildAgentCommand` asserts `"--cwd" not in cmd` (SWARM-01)

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved

---

## Validation Audit 2026-03-20

| Metric | Count |
|--------|-------|
| Gaps found | 3 |
| Resolved | 3 |
| Escalated | 0 |

All Wave 0 tests were committed during phase execution (commits `20fad63` RED, `d63d5e1` GREEN). No new tests needed — all requirements have automated verification covering the exact behavioral changes.
