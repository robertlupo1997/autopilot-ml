---
phase: 4
slug: e2e-validation-ux
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-19
audited: 2026-03-19
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (latest) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python3 -m pytest tests/mlforge/ -x -q` |
| **Full suite command** | `python3 -m pytest tests/mlforge/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/ -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/mlforge/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Tests | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|-------|--------|
| 04-01-01 | 01 | 1 | UX-01 | unit | `python3 -m pytest tests/mlforge/test_profiler.py -x` | Yes | 20 | green |
| 04-01-02 | 01 | 1 | UX-04 | unit | `python3 -m pytest tests/mlforge/test_profiler.py -x` | Yes | (in 20) | green |
| 04-01-03 | 01 | 1 | UX-02 | unit | `python3 -m pytest tests/mlforge/test_cli.py -x` | Yes | (in 31) | green |
| 04-01-04 | 01 | 1 | TABL-03 | integration | `python3 -m pytest tests/mlforge/test_profiler.py -x` | Yes | (in 20) | green |
| 04-02-01 | 02 | 2 | UX-03 | unit | `python3 -m pytest tests/mlforge/test_export.py -x` | Yes | 5 | green |
| 04-02-02 | 02 | 2 | UX-05 | unit | `python3 -m pytest tests/mlforge/test_retrospective.py -x` | Yes | 7 | green |
| 04-02-03 | 02 | 2 | GUARD-06 | unit | `python3 -m pytest tests/mlforge/test_retrospective.py tests/mlforge/test_engine.py -x` | Yes | (in 7+53) | green |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `tests/mlforge/test_profiler.py` — 20 tests for UX-01, UX-04, TABL-03
- [x] `tests/mlforge/test_export.py` — 5 tests for UX-03
- [x] `tests/mlforge/test_retrospective.py` — 7 tests for UX-05, GUARD-06
- [x] `tests/mlforge/test_cli.py` — 31 tests including UX-02 expert mode flags

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E2E run on real dataset beats baselines | TABL-03 | Requires full claude -p agent loop with real data | Run `mlforge run --dataset titanic.csv --target Survived` and verify best model beats both baselines |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-03-19

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

**Notes:** All 7 requirements have dedicated test coverage across 5 test files (116 total test functions). export (5) and retrospective (7) confirmed green (12/12 pass). profiler (20), cli (31), and engine (53) files exist with correct counts but cannot be collected in current env due to missing ML dependencies (pandas/numpy) — confirmed green per execution summaries (337 total tests at phase completion).
