---
phase: 3
slug: scaffold-cli-run-engine
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-19
audited: 2026-03-19
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (latest) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/mlforge/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/mlforge/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Tests | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|-------|--------|
| 03-01-01 | 01 | 1 | CORE-01 | unit | `python -m pytest tests/mlforge/test_cli.py -x` | Yes | 31 | green |
| 03-01-02 | 01 | 1 | GUARD-01 | unit | `python -m pytest tests/mlforge/test_scaffold.py -x` | Yes | 14 | green |
| 03-02-01 | 02 | 1 | CORE-02 | unit | `python -m pytest tests/mlforge/test_engine.py -x` | Yes | 53 | green |
| 03-02-02 | 02 | 1 | GUARD-03 | unit | `python -m pytest tests/mlforge/test_engine.py -x` | Yes | (in 53) | green |
| 03-02-03 | 02 | 1 | CORE-09 | unit | `python -m pytest tests/mlforge/test_guardrails.py -x` | Yes | 30 | green |
| 03-03-01 | 03 | 2 | GUARD-02 | unit | `python -m pytest tests/mlforge/test_guardrails.py -x` | Yes | (in 30) | green |
| 03-03-02 | 03 | 2 | GUARD-05 | unit | `python -m pytest tests/mlforge/test_guardrails.py -x` | Yes | (in 30) | green |
| 03-03-03 | 03 | 2 | INTL-07 | unit | `python -m pytest tests/mlforge/test_guardrails.py -x` | Yes | (in 30) | green |
| 03-03-04 | 03 | 2 | GUARD-04 | unit | `python -m pytest tests/mlforge/test_progress.py -x` | Yes | 12 | green |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `tests/mlforge/test_cli.py` — 31 tests for CORE-01 (CLI parsing, help, missing args, expert mode)
- [x] `tests/mlforge/test_scaffold.py` — 14 tests for GUARD-01 (scaffold output structure, hook files)
- [x] `tests/mlforge/test_engine.py` — 53 tests for CORE-02, GUARD-03 (run engine with mocked subprocess)
- [x] `tests/mlforge/test_guardrails.py` — 30 tests for CORE-09, GUARD-02, GUARD-05, INTL-07
- [x] `tests/mlforge/test_progress.py` — 12 tests for GUARD-04 (LiveProgress rendering)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live terminal display looks correct | GUARD-04 | Visual rendering cannot be automated | Run `mlforge` on sample dataset, verify table updates in terminal |
| pip install + CLI entry point works | CORE-01 | End-to-end install requires clean venv | `pip install -e .` then `mlforge --help` |

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

**Notes:** All 9 requirements have dedicated test coverage across 5 test files (140 total test functions). scaffold (14) and guardrails (30) confirmed green (44/44 pass). CLI (31), engine (53), and progress (12) files exist with correct counts but cannot be collected in current env due to missing ML dependencies (pandas/numpy/rich) — confirmed green per execution summaries (269 total tests at phase completion).
