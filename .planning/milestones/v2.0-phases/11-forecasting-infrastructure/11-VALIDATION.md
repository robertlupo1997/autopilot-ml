---
phase: 11
slug: forecasting-infrastructure
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-14
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed in dev group) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths = ["tests"] |
| **Quick run command** | `uv run pytest tests/test_forecast.py tests/test_prepare.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_forecast.py tests/test_prepare.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | TVAL-01 | unit | `uv run pytest tests/test_forecast.py::TestWalkForwardEvaluate -x` | ✅ | ✅ green |
| 11-01-02 | 01 | 1 | TVAL-02 | unit | `uv run pytest tests/test_forecast.py::TestWalkForwardEvaluate::test_dollar_scale_contract -x` | ✅ | ✅ green |
| 11-01-03 | 01 | 1 | TVAL-03 | unit | `uv run pytest tests/test_forecast.py::TestWalkForwardEvaluate::test_low_folds_warning -x` | ✅ | ✅ green |
| 11-01-04 | 01 | 1 | FMET-01 | unit | `uv run pytest tests/test_forecast.py::TestComputeMetric -x` | ✅ | ✅ green |
| 11-01-05 | 01 | 1 | FMET-02 | unit | `uv run pytest tests/test_forecast.py::TestComputeMetric -x` | ✅ | ✅ green |
| 11-01-06 | 01 | 1 | FMET-03 | unit | `uv run pytest tests/test_forecast.py::TestComputeMetric::test_directional_accuracy -x` | ✅ | ✅ green |
| 11-01-07 | 01 | 1 | BASE-01 | unit | `uv run pytest tests/test_forecast.py::TestBaselines -x` | ✅ | ✅ green |
| 11-01-08 | 01 | 1 | BASE-02 | unit | `uv run pytest tests/test_forecast.py::TestBaselines -x` | ✅ | ✅ green |
| 11-01-09 | 01 | 1 | BASE-03a | unit | `uv run pytest tests/test_forecast.py::TestBaselines::test_same_splits -x` | ✅ | ✅ green |
| 11-02-01 | 02 | 1 | TVAL-01 | unit | `uv run pytest tests/test_prepare.py::TestLoadDataForecast -x` | ✅ | ✅ green |
| 11-02-02 | 02 | 1 | TVAL-01 | unit | `uv run pytest tests/test_prepare.py::TestTemporalSplit -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_forecast.py` — stubs for TVAL-01..03, FMET-01..03, BASE-01..03
- [x] `src/automl/forecast.py` — module exists and all tests import successfully
- [x] Shared fixture `quarterly_revenue_series` — 40-row synthetic quarterly data in conftest.py

*Existing infrastructure covers framework needs — pytest already in dev dependencies.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved

---

## Validation Audit

**Audit date:** 2026-03-15
**Auditor:** GSD Nyquist Auditor

| Metric | Value |
|--------|-------|
| Total task IDs | 11 |
| Tests found | 11/11 |
| Tests passing | 11/11 |
| Gaps filled | 0 (all pre-existing) |
| Gaps remaining | 0 |

All 11 task requirements were covered by pre-existing tests in `tests/test_forecast.py` (21 tests across `TestWalkForwardEvaluate`, `TestComputeMetric`, `TestMetricMap`, `TestBaselines`) and `tests/test_prepare.py` (`TestLoadDataForecast` + `TestTemporalSplit`, 9 tests). Full suite: 330 passed.
