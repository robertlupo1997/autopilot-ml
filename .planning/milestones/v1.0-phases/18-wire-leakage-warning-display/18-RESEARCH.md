# Phase 18: Wire Leakage Warning Display - Research

**Researched:** 2026-03-20
**Domain:** Dataset profiling, leakage detection, CLI display
**Confidence:** HIGH

## Summary

This phase closes the INT-LEAKAGE-WARN gap: `validate_no_leakage()` exists and is tested in `tabular/prepare.py`, the `DatasetProfile.leakage_warnings` field exists, and the CLI already iterates over warnings to print them -- but `profile_dataset()` never calls `validate_no_leakage()`, so the field is always empty.

The fix is a single wiring change: call `validate_no_leakage(df, target_column)` inside `profile_dataset()` and assign the result to `leakage_warnings`. The CLI display code is already complete and requires no changes.

**Primary recommendation:** Add one function call in `profile_dataset()` to wire `validate_no_leakage()` into the profiling pipeline. No new libraries, no architectural changes.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUARD-06 | Run summary generated at session end: key findings, best approach, failed hypotheses, next directions | Leakage warnings in profile contribute to session awareness; profiler populates warnings that surface in CLI output |
| UX-04 | Dataset profiling analyzes schema, feature types, target distribution, and temporal patterns before experiments start | Leakage warnings are part of the profiling output; currently the field exists but is never populated |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | (already installed) | DataFrame operations, correlation computation | Already used by profiler.py and prepare.py |

### Supporting
No additional libraries needed. All required code already exists.

## Architecture Patterns

### Current Data Flow (broken)
```
CLI main() -> profile_dataset(df, target) -> DatasetProfile(leakage_warnings=[])
                                                  ^^ always empty
CLI prints warnings -> nothing to print
```

### Target Data Flow (fixed)
```
CLI main() -> profile_dataset(df, target) -> validate_no_leakage(df, target)
                                          -> DatasetProfile(leakage_warnings=[...])
CLI prints warnings -> shows leakage risk info
```

### Key Files
```
src/mlforge/profiler.py          # profile_dataset() -- needs the wiring change
src/mlforge/tabular/prepare.py   # validate_no_leakage() -- already exists, tested
src/mlforge/cli.py               # display code -- already exists (lines 173-175)
tests/mlforge/test_tabular.py    # validate_no_leakage tests -- already pass
tests/mlforge/test_cli.py        # leakage display tests -- already pass (mock-based)
```

### Pattern: Import from tabular prepare
The profiler is domain-agnostic (`src/mlforge/profiler.py`), while `validate_no_leakage` lives in the tabular-specific `src/mlforge/tabular/prepare.py`. The import should be guarded or lazy to avoid coupling the profiler to a specific plugin. Options:

1. **Direct import with try/except** (recommended): `validate_no_leakage` uses only pandas (no ML deps), so a direct import is safe. Use try/except ImportError for robustness.
2. **Inline the logic**: Copy the leakage checks into profiler.py. Rejected -- duplication.
3. **Move validate_no_leakage to profiler.py**: Would require updating tabular tests. More churn for no benefit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Leakage detection | New detection logic | `validate_no_leakage()` from `tabular/prepare.py` | Already exists, tested, handles name-matching and high-correlation checks |
| CLI display | New display code | Existing `cli.py` lines 173-175 | Already iterates `profile.leakage_warnings` and prints `WARNING:` prefixed lines |

## Common Pitfalls

### Pitfall 1: Import Coupling
**What goes wrong:** Importing `tabular.prepare` in `profiler.py` could pull in heavy ML dependencies.
**Why it happens:** `prepare.py` also has `load_data`, `split_data` functions that import sklearn.
**How to avoid:** `validate_no_leakage` only uses pandas. Use a targeted import: `from mlforge.tabular.prepare import validate_no_leakage`. Since pandas is already imported in profiler.py, this is safe. The sklearn imports in prepare.py are at function level or in other functions.
**Warning signs:** ImportError on `sklearn` when running profiler without ML deps installed.

### Pitfall 2: False Positives on Clean Data
**What goes wrong:** Overly sensitive leakage detection flags normal features as leaky.
**Why it happens:** The 0.99 correlation threshold and name-contains-target checks can match legitimate columns.
**How to avoid:** The existing `validate_no_leakage()` already uses a conservative 0.99 threshold and only flags columns whose name literally contains the target column name. No changes needed to the detection logic.
**Warning signs:** Tests with clean synthetic data producing unexpected warnings.

### Pitfall 3: Non-Tabular Domains
**What goes wrong:** DL/FT datasets may not be DataFrames or may not have meaningful column correlations.
**Why it happens:** `validate_no_leakage` assumes tabular DataFrame structure.
**How to avoid:** The profiler is only called when the CLI loads a CSV/Parquet file. DL image datasets and FT text datasets typically bypass the profiler path. Guard the call: only invoke when `target_column in df.columns` (already checked by cli.py line 160).

## Code Examples

### Current `profile_dataset()` return (profiler.py line 139-150)
```python
return DatasetProfile(
    task=task,
    metric=metric,
    direction=direction,
    n_rows=n_rows,
    n_features=n_features,
    numeric_features=numeric_features,
    categorical_features=categorical_features,
    date_columns=date_columns,
    target_stats=target_stats,
    missing_pct=missing_pct,
    # leakage_warnings NOT SET -- defaults to []
)
```

### Required Change
```python
# Add import at top of profiler.py
from mlforge.tabular.prepare import validate_no_leakage

# Inside profile_dataset(), before the return statement:
leakage_warnings = validate_no_leakage(df, target_column)

# Add to DatasetProfile constructor:
return DatasetProfile(
    ...,
    missing_pct=missing_pct,
    leakage_warnings=leakage_warnings,
)
```

### Existing CLI Display (cli.py lines 173-175, already works)
```python
if profile.leakage_warnings:
    for warning in profile.leakage_warnings:
        print(f"  WARNING: {warning}")
```

### Existing `validate_no_leakage` (prepare.py lines 213-255)
```python
def validate_no_leakage(
    df: pd.DataFrame,
    target_column: str,
    date_column: str | None = None,
) -> list[str]:
    # Checks: column name contains target name, correlation > 0.99
    # Returns list of warning strings, empty if clean
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No leakage warnings | `validate_no_leakage()` exists but unwired | Phase 4 (04-01) | Function exists, field exists, display exists -- just not connected |

## Open Questions

None. The implementation path is straightforward -- one function call wiring.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml |
| Quick run command | `python3 -m pytest tests/mlforge/test_profiler.py -x` |
| Full suite command | `python3 -m pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UX-04 | profile_dataset populates leakage_warnings from validate_no_leakage | unit | `python3 -m pytest tests/mlforge/test_profiler.py -x -k leakage` | Needs new test |
| UX-04 | Clean dataset produces empty leakage_warnings (no false positives) | unit | `python3 -m pytest tests/mlforge/test_profiler.py -x -k leakage` | Needs new test |
| GUARD-06 | CLI displays leakage warnings when present | unit | `python3 -m pytest tests/mlforge/test_cli.py::TestRichProfileDisplay -x` | Exists (mock-based) |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/mlforge/test_profiler.py tests/mlforge/test_cli.py -x`
- **Per wave merge:** `python3 -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/mlforge/test_profiler.py` -- add test for leakage_warnings populated on leaky data
- [ ] `tests/mlforge/test_profiler.py` -- add test for empty leakage_warnings on clean data

*(Note: test_profiler.py may already exist; new test cases needed regardless)*

## Sources

### Primary (HIGH confidence)
- Direct code reading: `src/mlforge/profiler.py` (lines 69-150) -- profile_dataset never calls validate_no_leakage
- Direct code reading: `src/mlforge/tabular/prepare.py` (lines 213-255) -- validate_no_leakage exists and is tested
- Direct code reading: `src/mlforge/cli.py` (lines 173-175) -- display code already handles leakage_warnings
- Test execution: `TestValidateNoLeakage` -- 2 tests pass confirming function works

### Secondary (MEDIUM confidence)
- None needed -- this is pure wiring of existing code

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, all code already exists
- Architecture: HIGH - single function call wiring, both sides already tested
- Pitfalls: HIGH - import safety verified by reading actual prepare.py imports

**Research date:** 2026-03-20
**Valid until:** Indefinite -- this is internal wiring, not dependent on external libraries
