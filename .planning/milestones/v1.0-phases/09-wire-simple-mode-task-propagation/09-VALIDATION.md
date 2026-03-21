---
phase: 09
slug: wire-simple-mode-task-propagation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-20
validated: 2026-03-20
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml (pytest section) |
| **Quick run command** | `python3 -m pytest tests/mlforge/test_cli.py tests/mlforge/test_tabular.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/mlforge/ -q` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/test_cli.py tests/mlforge/test_tabular.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/mlforge/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | UX-01 | unit | `python3 -m pytest tests/mlforge/test_cli.py -x -k simple` | Yes (3 tests: task, csv_path, target_column propagation) | green |
| 09-01-02 | 01 | 1 | UX-01, TABL-03 | unit | `python3 -m pytest tests/mlforge/test_tabular.py -x -k "classification or regression or task or temporal or default"` | Yes (5 tests: classifier models, regressor models, evaluate task, temporal comment, default task) | green |
| 09-01-03 | 01 | 1 | UX-01 | regression | `python3 -m pytest tests/mlforge/ -q` | Yes (466 tests full suite) | green |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. All 8 new tests (3 CLI + 5 tabular) were added as part of plan execution and are passing.*

---

## Test Coverage Detail

### CLI Tests (tests/mlforge/test_cli.py)

| Test | Requirement | Behavior Verified |
|------|-------------|-------------------|
| `test_auto_detection_sets_task_in_plugin_settings` | UX-01 | Simple mode propagates profile.task to plugin_settings["task"] |
| `test_auto_detection_sets_csv_path_in_plugin_settings` | UX-01 | Simple mode sets csv_path to filename only (not full path) |
| `test_auto_detection_sets_target_column_in_plugin_settings` | UX-01 | Simple mode sets target_column from user-specified target |

### Tabular Tests (tests/mlforge/test_tabular.py)

| Test | Requirement | Behavior Verified |
|------|-------------|-------------------|
| `test_scaffold_classification_has_classifier_models` | UX-01 | Classification task renders RandomForestClassifier + LogisticRegression |
| `test_scaffold_regression_has_regressor_models` | UX-01 | Regression task renders RandomForestRegressor + Ridge |
| `test_scaffold_evaluate_uses_task_variable` | TABL-03 | evaluate() call uses correct task string, not hardcoded "regression" |
| `test_scaffold_date_column_temporal_comment` | TABL-03 | Date column triggers temporal_split awareness comment |
| `test_scaffold_default_task_is_classification` | UX-01 | Expert mode (empty plugin_settings) defaults to classification |

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s (actual: ~3s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete (2026-03-20)
