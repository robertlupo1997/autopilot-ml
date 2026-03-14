---
phase: 12
slug: forecast-template-and-mutable-zone-2
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 12-01-01 | 01 | 1 | FEAT-01 | unit (text/AST) | `uv run pytest tests/test_train_template_forecast.py::test_engineer_features_starter_features -x` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | FEAT-01 | unit (text) | `uv run pytest tests/test_train_template_forecast.py::test_shift_before_rolling -x` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | FEAT-02 | unit (text) | `uv run pytest tests/test_train_template_forecast.py::test_engineer_features_in_template -x` | ❌ W0 | ⬜ pending |
| 12-01-04 | 01 | 1 | OPTA-01 | unit (text) | `uv run pytest tests/test_train_template_forecast.py::test_optuna_suggest_calls -x` | ❌ W0 | ⬜ pending |
| 12-01-05 | 01 | 1 | OPTA-03 | unit (text) | `uv run pytest tests/test_train_template_forecast.py::test_objective_calls_walk_forward -x` | ❌ W0 | ⬜ pending |
| 12-01-06 | 01 | 1 | FEAT-03 | unit (text) | `uv run pytest tests/test_train_template_forecast.py::test_claude_forecast_feature_cap -x` | ❌ W0 | ⬜ pending |
| 12-01-07 | 01 | 1 | OPTA-02 | unit (text) | `uv run pytest tests/test_train_template_forecast.py::test_claude_forecast_trial_budget_cap -x` | ❌ W0 | ⬜ pending |
| 12-01-08 | 01 | 1 | BASE-03b | unit (text) | `uv run pytest tests/test_train_template_forecast.py::test_claude_forecast_dual_baseline_rule -x` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | FEAT-04 | unit (string match) | `uv run pytest tests/test_scaffold.py::test_settings_deny_forecast -x` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 1 | FEAT-04 | unit (string match) | `uv run pytest tests/test_scaffold.py::test_guard_hook_frozen_forecast -x` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_train_template_forecast.py` — stubs for FEAT-01..04, OPTA-01..03, BASE-03b (text/AST inspection tests)
- [ ] `tests/test_scaffold.py::test_settings_deny_forecast` — new test for FEAT-04

*Existing `tests/test_scaffold.py::test_guard_hook_frozen_forecast` covers guard-frozen.sh check (Phase 11).*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
