---
phase: 13-scaffold-and-cli-updates
plan: "01"
subsystem: scaffold-cli
tags: [scaffold, cli, forecasting, templates]
dependency_graph:
  requires: [forecast.py, train_template_forecast.py, claude_forecast.md.tmpl]
  provides: [date_col branching in scaffold_experiment, --date-column CLI flag, render_claude_md_forecast]
  affects: [src/automl/scaffold.py, src/automl/cli.py, src/automl/templates/__init__.py]
tech_stack:
  added: []
  patterns: [TDD red-green, importlib.util.find_spec for template location, pandas infer_freq for frequency detection]
key_files:
  created: []
  modified:
    - src/automl/scaffold.py
    - src/automl/templates/__init__.py
    - src/automl/cli.py
    - tests/test_scaffold.py
    - tests/test_cli.py
decisions:
  - "scaffold_experiment import moved to cli.py module level (not inside try block) to enable patching in tests"
  - "program.md for forecasting built via _render_forecast_program_md() not render_program_md() — avoids 'higher is always better' text from standard template"
  - "_format_forecast_summary() uses X.index (DatetimeIndex) from load_data date_col path for time range and frequency"
metrics:
  duration: 204s
  completed: 2026-03-14
  tasks_completed: 2
  files_modified: 5
---

# Phase 13 Plan 01: Scaffold and CLI Updates Summary

**One-liner:** Wired --date-column CLI flag through cli.py into scaffold_experiment() forecasting branch, generating forecast-specific train.py, CLAUDE.md, and program.md with time range, frequency, and naive/seasonal-naive MAPE baselines.

## What Was Built

Two tasks executed with TDD (red-green per task):

**Task 1: Forecasting scaffold branch**
- Added `render_claude_md_forecast()` to `src/automl/templates/__init__.py` — renders `claude_forecast.md.tmpl` statically
- Extended `scaffold_experiment()` in `src/automl/scaffold.py` with `date_col: str | None = None` parameter
- When `date_col is not None`: uses `train_template_forecast.py` (substituting CSV_PATH, TARGET_COLUMN, DATE_COLUMN, METRIC, TIME_BUDGET), renders `claude_forecast.md.tmpl`, builds a custom `program.md` via `_render_forecast_program_md()`
- When `date_col is None`: unchanged v1.0 path (no regression)
- Added `_format_forecast_summary(X, y)`: shape, time range, inferred frequency, target stats
- Added `_format_forecast_baselines(y_values)`: calls `get_forecasting_baselines()`, formats naive/seasonal MAPE
- Added `_render_forecast_program_md()`: produces forecasting program.md with "minimize" direction and no "higher is always better" language

**Task 2: CLI --date-column flag**
- Added `--date-column` argument to argparse in `cli.py`
- Added swarm+forecasting guard: `--agents > 1` with `--date-column` returns exit code 1 with error message
- Passed `date_col=args.date_column` to `scaffold_experiment()`
- Moved `scaffold_experiment` import to module level (was inside `try` block) for testability

## Test Coverage

- 10 new tests in `TestScaffoldForecasting` + `TestScaffoldStandardPathUnchanged`
- 4 new tests in `TestCliDateColumnFlag`
- All 315 tests pass (249 pre-existing + 14 new)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] scaffold_experiment import at module level for mockability**
- **Found during:** Task 2 (test_date_column_passed_through failed with AttributeError)
- **Issue:** `scaffold_experiment` was imported inside the `try` block in `main()`, making `patch("automl.cli.scaffold_experiment")` fail — the attribute doesn't exist at module level
- **Fix:** Moved `from automl.scaffold import scaffold_experiment` to module-level imports in `cli.py`
- **Files modified:** `src/automl/cli.py`
- **Commit:** 57aed8b

## Success Criteria Status

1. `uv run automl data.csv revenue mape --date-column date` scaffolds a complete forecasting experiment (SCAF-01 + SCAF-02): PASS
2. Generated program.md includes time range, inferred frequency, and naive + seasonal-naive MAPE scores (SCAF-03): PASS
3. Omitting `--date-column` produces v1.0 scaffold unchanged (strict opt-in): PASS
4. `--agents N --date-column` rejected with clear error: PASS
5. All tests pass (existing + new): PASS (315 tests)

## Self-Check: PASSED

All key files exist and all 4 task commits verified:
- 12b37bd: test(13-01) — failing scaffold tests (RED)
- b3fc410: feat(13-01) — forecasting scaffold branch (GREEN Task 1)
- b8f24a5: test(13-01) — failing CLI tests (RED)
- 57aed8b: feat(13-01) — --date-column CLI flag (GREEN Task 2)
