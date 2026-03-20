---
phase: 04-e2e-validation-ux
verified: 2026-03-20T02:00:00Z
status: human_needed
score: 8/9 must-haves verified
human_verification:
  - test: "Run `mlforge <real-dataset>.csv 'predict <target>'` against a real tabular CSV dataset and observe that the session scaffolds, iterates at least one experiment, checkpoints, and produces a RETROSPECTIVE.md"
    expected: "Session runs end-to-end, produces best_model.joblib (or None if no kept experiment), generates RETROSPECTIVE.md, prints Auto-detected task/metric summary, and exits cleanly"
    why_human: "Requires a live `claude -p` subprocess and a real dataset -- cannot be verified programmatically without running the full agent loop"
---

# Phase 4: E2E Validation + UX Verification Report

**Phase Goal:** The full tabular pipeline is validated end-to-end on real data, and user experience features (simple/expert modes, artifact export, run summaries) are complete
**Verified:** 2026-03-20T02:00:00Z
**Status:** human_needed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Simple mode auto-detects classification vs regression from target column statistics | VERIFIED | `profile_dataset()` in `profiler.py` lines 113-116: `if is_numeric and n_unique > 20: task = "regression"` else classification |
| 2 | Simple mode selects appropriate metric (accuracy/f1_weighted for classification, r2 for regression) | VERIFIED | `profiler.py` lines 119-132: binary->accuracy, multi-class->f1_weighted, regression->r2, all direction="maximize" |
| 3 | Simple mode detects date columns and sets temporal config for leakage prevention | VERIFIED | `profiler.py` `_detect_date_columns()` + `cli.py` lines 138-139: `config.plugin_settings["date_column"] = profile.date_columns[0]` |
| 4 | Expert mode accepts custom CLAUDE.md path, custom frozen files, and custom mutable files | VERIFIED | `cli.py` lines 72-89: `--custom-claude-md`, `--custom-frozen`, `--custom-mutable` flags added; wired to Config at lines 116-121 |
| 5 | Dataset profiling reports n_rows, n_features, numeric/categorical splits, missing data pct, and date columns | VERIFIED | `DatasetProfile` dataclass in `profiler.py` lines 16-29; all fields populated in `profile_dataset()` |
| 6 | Best model artifact is copied to artifacts/ with metadata.json sidecar after session ends | VERIFIED | `export.py` lines 35-58: `shutil.copy2`, metadata includes all required fields, returns `artifacts_dir` |
| 7 | Metadata includes metric name, value, direction, best commit, experiment count, total cost, timestamp | VERIFIED | `export.py` lines 46-54: all 7 required metadata fields present, `exported_at` uses `datetime.now(timezone.utc).isoformat()` |
| 8 | Run retrospective generates markdown report with summary table, successful approaches, failed approaches, and recommendations | VERIFIED | `retrospective.py` 88 lines; all 4 sections present with conditional recommendations (0 keeps, high revert rate, otherwise) |
| 9 | A complete mlforge run on real tabular data scaffolds, iterates, checkpoints, resumes, and produces a best model that beats both baselines | UNCERTAIN | No E2E run directory found in repo; unit tests pass (310/310) but live agent invocation cannot be verified programmatically |

**Score:** 8/9 truths verified (1 requires human)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mlforge/profiler.py` | DatasetProfile + profile_dataset() + _detect_date_columns() | VERIFIED | 150 lines, substantive; all three symbols present and implemented |
| `src/mlforge/cli.py` | Simple/expert mode flags + profiler integration | VERIFIED | 201 lines; `--custom-claude-md` on line 73, `profile_dataset` imported and called at line 135 |
| `tests/mlforge/test_profiler.py` | Unit tests for profiler auto-detection and temporal detection | VERIFIED | 205 lines; 20+ tests across TestRegressionDetection, TestClassificationDetection, TestDateDetection, TestDataCharacteristics |
| `src/mlforge/export.py` | export_artifact() with joblib copy + metadata JSON | VERIFIED | 58 lines; substantive implementation with shutil.copy2 and json metadata |
| `src/mlforge/retrospective.py` | generate_retrospective() returning markdown string | VERIFIED | 88 lines; structured markdown with all required sections and edge case handling |
| `tests/mlforge/test_export.py` | Unit tests for artifact export | VERIFIED | 87 lines; 5 tests covering all required behaviors |
| `tests/mlforge/test_retrospective.py` | Unit tests for retrospective generation | VERIFIED | 148 lines; 7+ tests including zero-experiment edge case and high revert rate |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/mlforge/cli.py` | `src/mlforge/profiler.py` | `profile_dataset()` call in simple mode | WIRED | Imported at line 22, called at line 135; result drives `config.metric`, `config.direction`, `config.plugin_settings["date_column"]` |
| `src/mlforge/cli.py` | `src/mlforge/scaffold.py` | `scaffold_experiment` receives config with profiler-derived values | WIRED | Imported at line 23, called at line 171; config carries profiler-populated metric/direction/plugin_settings |
| `src/mlforge/profiler.py` | `src/mlforge/config.py` | Profiler results populate Config fields (metric, direction, date_column) | WIRED (via CLI) | Profiler returns DatasetProfile; CLI (not profiler directly) writes to Config -- correct architecture per research doc; config.py has all three fields at lines 33-35 |
| `src/mlforge/engine.py` | `src/mlforge/export.py` | `engine.run()` calls `export_artifact()` after loop | WIRED | Imported at line 18; called at line 88 inside `finally` block after checkpoint save |
| `src/mlforge/engine.py` | `src/mlforge/retrospective.py` | `engine.run()` calls `generate_retrospective()` after loop | WIRED | Imported at line 23; called at line 94; result written to `RETROSPECTIVE.md` at line 97-98 |
| `src/mlforge/retrospective.py` | `src/mlforge/results.py` | reads ResultsTracker.summary() and get_by_status() | WIRED | `ResultsTracker` imported at line 10; `tracker.summary()` called at line 27; `get_by_status("keep")` and `get_by_status("revert")` at lines 28-29 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| UX-01 | 04-01-PLAN.md | Simple mode auto-detects task type, selects metrics, runs with minimal input | SATISFIED | `profile_dataset()` + CLI simple mode branch (no `--metric`); auto-detects and prints task/metric to stdout |
| UX-02 | 04-01-PLAN.md | Expert mode accepts custom CLAUDE.md, frozen/mutable zones | SATISFIED | `--custom-claude-md`, `--custom-frozen`, `--custom-mutable` CLI flags; scaffold respects custom CLAUDE.md (copy not render) and custom frozen/mutable lists |
| UX-03 | 04-02-PLAN.md | Best model artifact exported with metadata after session | SATISFIED | `export_artifact()` copies joblib + writes 7-field metadata.json to artifacts/ |
| UX-04 | 04-01-PLAN.md | Dataset profiling analyzes schema, feature types, target distribution, temporal patterns | SATISFIED | `DatasetProfile` with n_rows, n_features, numeric_features, categorical_features, date_columns, target_stats, missing_pct |
| UX-05 | 04-02-PLAN.md | Run retrospective summarizes approaches tried, failures, cost, recommendations | SATISFIED | `generate_retrospective()` produces markdown with summary table, successful/failed approaches, conditional recommendations |
| GUARD-06 | 04-02-PLAN.md | Run summary generated at session end | SATISFIED | Retrospective wired to `engine.run()` finally block; always written to RETROSPECTIVE.md at session end |
| TABL-03 | 04-01-PLAN.md | Leakage prevention: shift-first temporal features, walk-forward CV | SATISFIED (infrastructure) | Date column detection in profiler wires to `config.plugin_settings["date_column"]`; `tabular/prepare.py` has `temporal_split()` and `validate_no_leakage()`; E2E agent invocation needed to confirm runtime behavior |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | - | - | No TODO/FIXME/placeholder comments, empty returns, or stub implementations found in any phase-4 files |

### Human Verification Required

#### 1. E2E Run on Real Dataset

**Test:** Obtain a tabular CSV dataset (e.g., Iris, Titanic, or any CSV with a clear target column). Run `mlforge <dataset>.csv "predict <target>"` and observe the full session.

**Expected:**
- Prints "Auto-detected: classification/regression task, metric=..., N rows, M features"
- Creates experiment directory, scaffolds CLAUDE.md, experiments.md, train.py, prepare.py
- Spawns at least one `claude -p` experiment iteration
- Saves checkpoint to `.mlforge/` subdirectory
- On session end: writes RETROSPECTIVE.md with # mlforge Run Retrospective header
- If any experiment was kept: artifacts/best_model.joblib and artifacts/metadata.json exist

**Why human:** Requires live `claude -p` agent subprocess with API access and a real dataset. Success Criterion #1 from ROADMAP.md -- "A complete mlforge run on a real tabular dataset scaffolds, iterates, checkpoints, resumes, and produces a best model that beats both baselines" -- cannot be verified with static code analysis.

### Gaps Summary

No automated gaps found. All 7 requirements have verified implementation. The single human verification item (Success Criterion #1: full E2E run on real data) is a runtime/integration concern explicitly flagged as manual-only in `04-VALIDATION.md`. The infrastructure to support it -- scaffold, engine loop, profiler, export, retrospective -- is fully implemented and wired.

---

_Verified: 2026-03-20T02:00:00Z_
_Verifier: Claude (gsd-verifier)_
