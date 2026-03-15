---
phase: 12
slug: forecast-template-and-mutable-zone-2
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-14
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (installed) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_train_template_forecast.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_train_template_forecast.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | FEAT-01 | unit (text/AST) | `uv run pytest tests/test_train_template_forecast.py::TestTrainTemplateForecastStructure::test_engineer_features_starter_features -x` | ✅ | ✅ green |
| 12-01-02 | 01 | 1 | FEAT-01 | unit (text) | `uv run pytest tests/test_train_template_forecast.py::TestTrainTemplateForecastStructure::test_shift_before_rolling -x` | ✅ | ✅ green |
| 12-01-03 | 01 | 1 | FEAT-02 | unit (text) | `uv run pytest tests/test_train_template_forecast.py::TestTrainTemplateForecastStructure::test_objective_calls_walk_forward -x` | ✅ | ✅ green |
| 12-01-04 | 01 | 1 | OPTA-01 | unit (text) | `uv run pytest tests/test_train_template_forecast.py::TestTrainTemplateForecastStructure::test_optuna_create_study -x` | ✅ | ✅ green |
| 12-01-05 | 01 | 1 | OPTA-03 | unit (text) | `uv run pytest tests/test_train_template_forecast.py::TestTrainTemplateForecastStructure::test_objective_calls_walk_forward -x` | ✅ | ✅ green |
| 12-01-06 | 01 | 1 | FEAT-03 | unit (text) | `uv run pytest tests/test_train_template_forecast.py::TestClaudeForecastTemplate::test_feature_cap_rule -x` | ✅ | ✅ green |
| 12-01-07 | 01 | 1 | OPTA-02 | unit (text) | `uv run pytest tests/test_train_template_forecast.py::TestClaudeForecastTemplate::test_trial_budget_rule -x` | ✅ | ✅ green |
| 12-01-08 | 01 | 1 | BASE-03b | unit (text) | `uv run pytest tests/test_train_template_forecast.py::TestClaudeForecastTemplate::test_dual_baseline_rule -x` | ✅ | ✅ green |
| 12-02-01 | 02 | 1 | FEAT-04 | unit (string match) | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude::test_settings_deny_forecast -x` | ✅ | ✅ green |
| 12-02-02 | 02 | 1 | FEAT-04 | unit (string match) | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude::test_scaffold_hook_denies_forecast_py -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Note: Task 12-02-02 was listed in the plan as `test_guard_hook_frozen_forecast` but the implemented test is `test_scaffold_hook_denies_forecast_py` (consistent with existing naming conventions in test_scaffold.py). Both names cover the same FEAT-04 requirement.*

---

## Wave 0 Requirements

- [x] `tests/test_train_template_forecast.py` — 17 structural text/AST inspection tests (FEAT-01..04, OPTA-01..03, BASE-03b)
- [x] `tests/test_scaffold.py::TestScaffoldDotClaude::test_settings_deny_forecast` — FEAT-04 deny list check

*Existing `tests/test_scaffold.py::TestScaffoldDotClaude::test_scaffold_hook_denies_forecast_py` covers guard-frozen.sh check.*

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
| Total task IDs | 10 |
| Tests found | 10/10 |
| Tests passing | 10/10 |
| Gaps filled | 0 (all pre-existing) |
| Gaps remaining | 0 |

All 10 task requirements covered by pre-existing tests: 17 structural inspection tests in `tests/test_train_template_forecast.py` (classes `TestTrainTemplateForecastStructure` and `TestClaudeForecastTemplate`) and 2 tests in `tests/test_scaffold.py` (`test_settings_deny_forecast`, `test_scaffold_hook_denies_forecast_py`). Additional Phase 12-02 coverage from `TestScaffoldForecast::test_scaffold_pyproject_has_optuna` and `test_scaffold_copies_forecast_py`. Full suite: 330 passed.
