---
phase: 12-forecast-template-and-mutable-zone-2
verified: 2026-03-14T00:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 12: Forecast Template and Mutable Zone 2 Verification Report

**Phase Goal:** Agent has a correct starting template and explicit protocol for feature engineering and Optuna, so first drafts are structurally leakage-free
**Verified:** 2026-03-14
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | `train_template_forecast.py` contains `engineer_features()` with lag_1, lag_4, yoy_growth, rolling_mean_4q using shift-first pattern | ✓ VERIFIED | File lines 49-68: all four features present; `s.shift(1).rolling(4).mean()` at line 62 confirms shift-first |
| 2   | Optuna `objective()` calls `walk_forward_evaluate` from frozen forecast module — no custom CV loop | ✓ VERIFIED | `walk_forward_evaluate` called at line 98 inside `objective()` closure; no KFold or manual fold loop anywhere in file |
| 3   | `claude_forecast.md.tmpl` contains numbered rules for shift-first, 15-feature cap, trial budget cap, dual-baseline gate, and MAPE direction | ✓ VERIFIED | Rules 4–9 in template explicitly cover all five: Rule 4 (shift-first), Rule 5 (15-feature cap), Rule 6 (min(50, 2*n_rows)), Rule 7 (no custom CV), Rule 8 (dual-baseline gate), Rule 9 (MAPE lower is better) |
| 4   | Template prints structured output compatible with `parse_run_result.py` (metric_value, json_output lines) | ✓ VERIFIED | Lines 130-148: identical block to `train_template.py` format; `json_output` dict includes `beats_naive` and `beats_seasonal_naive` |
| 5   | `scaffold.py` deny list includes `Edit(forecast.py)` and `Write(forecast.py)` | ✓ VERIFIED | Lines 248-249 of scaffold.py confirmed; test `test_settings_deny_forecast` passes |
| 6   | `scaffold.py` pyproject.toml includes `optuna>=4.0` dependency | ✓ VERIFIED | Line 306 of scaffold.py: `"optuna>=4.0"` in dependencies list; test `test_scaffold_pyproject_has_optuna` passes |
| 7   | `scaffold.py` copies `forecast.py` into experiment directory alongside `prepare.py` | ✓ VERIFIED | Lines 93-95 of scaffold.py: `inspect.getfile(_forecast_module)` + `shutil.copy2`; test `test_scaffold_copies_forecast_py` passes |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/automl/train_template_forecast.py` | Forecast template with engineer_features, Optuna, walk_forward_evaluate | ✓ VERIFIED | 149 lines, importable as `automl.train_template_forecast`; contains `engineer_features`, `objective`, `create_study`, `walk_forward_evaluate`, `get_forecasting_baselines` |
| `src/automl/templates/claude_forecast.md.tmpl` | Forecast-specific CLAUDE.md agent protocol containing dual-baseline gate | ✓ VERIFIED | 154 lines; contains "Dual-baseline gate" language in Rule 8, both `naive` and `seasonal` mentioned, frozen-file rules for `prepare.py` and `forecast.py` |
| `tests/test_train_template_forecast.py` | Structural inspection tests (min 50 lines) | ✓ VERIFIED | 201 lines; 17 tests across two classes — all 17 pass |
| `src/automl/scaffold.py` | Patched scaffold with forecast.py deny, optuna dep, forecast copy | ✓ VERIFIED | Contains `import automl.forecast as _forecast_module` at line 20, forecast copy block at lines 93-95, deny entries at lines 248-249, optuna dep at line 306 |
| `tests/test_scaffold.py` | Tests for forecast.py deny list and optuna dep containing `test_settings_deny_forecast` | ✓ VERIFIED | `test_settings_deny_forecast`, `test_scaffold_hook_denies_forecast_py`, `test_scaffold_pyproject_has_optuna`, `test_scaffold_copies_forecast_py` all present and passing |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `train_template_forecast.py` | `forecast.walk_forward_evaluate` | `from forecast import walk_forward_evaluate` | ✓ WIRED | Line 36 imports it; called at line 98 inside `objective()` and line 121 for final evaluation |
| `train_template_forecast.py` | `forecast.get_forecasting_baselines` | `from forecast import get_forecasting_baselines` | ✓ WIRED | Line 36 imports it; called at line 44; result used in `_result` dict lines 144-146 |
| `train_template_forecast.py` | `optuna.create_study` | `import optuna` | ✓ WIRED | Line 74 imports optuna; `optuna.create_study(direction="minimize")` at line 102; `study.optimize(objective, n_trials=N_TRIALS)` at line 103 |
| `scaffold.py` | `automl.forecast` | `import automl.forecast as _forecast_module` | ✓ WIRED | Line 20 imports module; `inspect.getfile(_forecast_module)` used at line 94 to locate source for copy |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| BASE-03b | 12-01 | Agent must beat both baselines to keep; auto-revert if not | ✓ SATISFIED | Rule 8 in `claude_forecast.md.tmpl` explicitly mandates dual-baseline gate; `beats_naive` and `beats_seasonal_naive` keys in structured output enable agent to check |
| FEAT-01 | 12-01 | Template includes lag_1, lag_4, YoY growth rate, rolling_mean_4q starter features | ✓ SATISFIED | All four features present in `engineer_features()` (lines 59-62) |
| FEAT-02 | 12-01 | Agent can add/modify feature engineering in mutable zone 2 | ✓ SATISFIED | `engineer_features()` is explicitly marked MUTABLE ZONE 2; CLAUDE.md template instructs agent to edit this function |
| FEAT-03 | 12-01 | Feature count capped at 15 in CLAUDE.md guidance | ✓ SATISFIED | Rule 5 in `claude_forecast.md.tmpl`: "Feature count cap: 15. Do not create more than 15 features" |
| FEAT-04 | 12-02 | Guard hook updated to protect both `prepare.py` and `forecast.py` | ✓ SATISFIED | `guard_frozen_hook_content()` in scaffold.py lists `FROZEN_FILES="prepare.py forecast.py"`; deny list has four entries; hook test confirms denial |
| OPTA-01 | 12-01 | Template demonstrates `create_study()` with `trial.suggest_*` | ✓ SATISFIED | `optuna.create_study(direction="minimize")` at line 102; `trial.suggest_float("alpha", ...)` at line 84 |
| OPTA-02 | 12-01 | Trial budget capped at `min(50, 2 * n_rows)` in CLAUDE.md guidance | ✓ SATISFIED | Rule 6 in `claude_forecast.md.tmpl`: "Trial budget: `min(50, 2 * n_rows)`"; also implemented in template at line 79: `N_TRIALS = min(50, 2 * len(y_raw))` |
| OPTA-03 | 12-01 | Optuna objective calls frozen `walk_forward_evaluate()` — no custom CV loop | ✓ SATISFIED | `objective()` calls `walk_forward_evaluate(model_fn, X_input, y_raw, ...)` at line 98; Rule 7 in template: "NEVER write your own CV loop" |

All 8 requirement IDs from plan frontmatter are accounted for. No orphaned requirements — REQUIREMENTS.md traceability table maps all 8 to Phase 12 with status Complete.

### Anti-Patterns Found

None identified. Scanned `train_template_forecast.py`, `claude_forecast.md.tmpl`, `tests/test_train_template_forecast.py`, and `scaffold.py`.

- No TODO/FIXME/placeholder comments in phase artifacts
- No empty return implementations (all functions have real logic)
- No stub handler patterns (engineer_features returns real features; objective performs real optimization)
- `optuna.logging.set_verbosity(optuna.logging.WARNING)` present — [I] log spam suppressed

### Human Verification Required

None. All truths are structurally verifiable through text inspection and test execution. The template is not executed during this phase (that is Phase 14's responsibility).

### Gaps Summary

No gaps. All 7 observable truths verified, all 5 artifacts exist with substantive content and correct wiring, all 8 requirements satisfied, and all 44 tests (17 template + 27 scaffold) pass with 301 total suite tests passing.

---

_Verified: 2026-03-14_
_Verifier: Claude (gsd-verifier)_
