---
phase: 13
slug: scaffold-and-cli-updates
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-14
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (installed) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_cli.py tests/test_scaffold.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_cli.py tests/test_scaffold.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | SCAF-01 | unit | `uv run pytest tests/test_cli.py::TestCliDateColumnFlag -x -q` | ✅ | ✅ green |
| 13-01-02 | 01 | 1 | SCAF-02 | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting -x -q` | ✅ | ✅ green |
| 13-01-03 | 01 | 1 | SCAF-02 | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldStandardPathUnchanged -x -q` | ✅ | ✅ green |
| 13-01-04 | 01 | 1 | SCAF-03 | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting::test_forecast_program_md_naive_mape -x -q` | ✅ | ✅ green |
| 13-01-05 | 01 | 1 | SCAF-03 | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting::test_forecast_program_md_seasonal_naive_mape -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_cli.py` — `TestCliDateColumnFlag` class added (4 tests)
- [x] `tests/test_scaffold.py` — `TestScaffoldForecasting` (9 tests) and `TestScaffoldStandardPathUnchanged` (1 test) classes added

*No new test files needed — all new tests are in existing test files.*

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

## Validation Audit

**Audit date:** 2026-03-15
**Auditor:** GSD Nyquist Auditor

| Metric | Value |
|--------|-------|
| Total task IDs | 5 |
| Tests found | 5/5 |
| Tests passing | 5/5 |
| Gaps filled | 0 (all pre-existing) |
| Gaps remaining | 0 |

All 5 task requirements covered by pre-existing tests: `TestCliDateColumnFlag` (4 tests: `test_date_column_in_help`, `test_date_column_default_none`, `test_date_column_passed_through`, `test_agents_with_date_column_rejected`) in `tests/test_cli.py`; `TestScaffoldForecasting` (9 tests) and `TestScaffoldStandardPathUnchanged` (1 test) in `tests/test_scaffold.py`. Full suite: 330 passed.
