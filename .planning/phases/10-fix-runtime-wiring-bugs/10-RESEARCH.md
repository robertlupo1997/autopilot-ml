# Phase 10: Fix Runtime Wiring Bugs - Research

**Researched:** 2026-03-20
**Domain:** Python runtime integration bugs (mlforge engine, CLI, swarm)
**Confidence:** HIGH

## Summary

Phase 10 fixes three residual integration bugs found by the v1.0 milestone audit. All three are straightforward wiring issues -- code exists but is either dead, unreachable, or uses invalid flags. No new libraries, patterns, or architectural changes are needed.

**Bug 1 (INTL-01/INTL-02):** `_compute_baselines()` in `engine.py` dynamically loads the scaffolded `prepare.py` via `importlib.util` and looks for module-level `X_train`/`y_train` attributes. But the scaffolded `prepare.py` only defines *functions* (`load_data()`, `split_data()`), not module-level data. Result: `X_train` is always `None`, baselines are never computed, and `state.baselines` stays `None` -- making the dual-baseline gate dead code.

**Bug 2 (INTL-05):** `cli.py` has no `--enable-drafts` argument. `Config.enable_drafts` defaults to `False`. The multi-draft phase in `engine.py` (lines 86-92) is unreachable from the command line.

**Bug 3 (SWARM-01):** `swarm/__init__.py` line 159 passes `--cwd` to `claude`, but `--cwd` is not a valid `claude` CLI flag. The working directory is already correctly set via `subprocess.Popen(cmd, cwd=...)` on line 105.

**Primary recommendation:** Fix all three bugs in a single plan with corresponding test updates.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTL-01 | Baseline establishment runs naive + domain-specific baselines before agent starts experimenting | Fix `_compute_baselines()` to call `prepare.load_data()` + `prepare.split_data()` instead of reading nonexistent module-level variables |
| INTL-02 | Dual-baseline gate requires agent to beat both naive and domain-specific baselines before keeping | Enabled by INTL-01 fix -- once `state.baselines` is populated, the gate logic in `_process_result()` (line 219) works correctly |
| INTL-05 | Multi-draft start generates 3-5 diverse initial solutions | Add `--enable-drafts` CLI flag that sets `config.enable_drafts = True` |
| SWARM-01 | Swarm mode spawns parallel agents in git worktrees | Remove `--cwd` from `_build_agent_command()` return value (subprocess `cwd` kwarg already handles this) |
</phase_requirements>

## Bug Analysis

### Bug 1: Dead Baseline Gate (INTL-01, INTL-02)

**Location:** `src/mlforge/engine.py`, `_compute_baselines()` method (lines 500-528)

**Root cause:** The method uses `importlib.util` to load the scaffolded `prepare.py` and then does:
```python
X_train = getattr(mod, "X_train", None)
y_train = getattr(mod, "y_train", None)
if X_train is None or y_train is None:
    return None
```

But the actual scaffolded `prepare.py` (from `src/mlforge/tabular/prepare.py`) only defines functions: `load_data(path)` and `split_data(df, target_column)`. There are no module-level `X_train`/`y_train` attributes. So the method always returns `None`.

**Fix:** Replace the module-level attribute access with actual function calls:
1. Load the `prepare` module via `importlib.util` (already working)
2. Get `csv_path` and `target_column` from `self.config.plugin_settings`
3. Call `mod.load_data(experiment_dir / csv_path)` to get the DataFrame
4. Call `mod.split_data(df, target_column)` to get `X_train, X_test, y_train, y_test`
5. Pass `X_train`, `y_train` to `compute_baselines()`

**Data available in config:** `config.plugin_settings` contains `csv_path` (filename) and `target_column` from the dataset profiler (set in `cli.py` lines 159-160).

**Edge cases:**
- Missing `csv_path` or `target_column` in plugin_settings: return `None` (graceful skip)
- `load_data()` or `split_data()` raises an exception: catch and return `None`
- The dataset file must exist in `experiment_dir` (the scaffold copies it there)

**Confidence:** HIGH -- verified by reading both `engine.py` and `tabular/prepare.py` source.

### Bug 2: Unreachable Multi-Draft (INTL-05)

**Location:** `src/mlforge/cli.py` -- missing `--enable-drafts` argument

**Root cause:** The `Config` dataclass has `enable_drafts: bool = False` (config.py line 36), and it can be loaded from TOML (`intelligence.enable_drafts`), but there is no CLI flag to set it. Users running `mlforge dataset goal` cannot enable multi-draft from the command line.

**Fix:** Add `--enable-drafts` argument to the argparse parser and wire it:
```python
parser.add_argument("--enable-drafts", action="store_true", help="Enable multi-draft initial exploration")
```
Then in the config wiring section:
```python
if args.enable_drafts:
    config.enable_drafts = True
```

**Confidence:** HIGH -- straightforward argparse addition.

### Bug 3: Invalid --cwd Swarm Flag (SWARM-01)

**Location:** `src/mlforge/swarm/__init__.py`, `_build_agent_command()` method (line 159)

**Current code:**
```python
return ["claude", "-p", prompt, "--cwd", str(wt_path)]
```

**Root cause:** `--cwd` is not a valid `claude` CLI flag. The `cwd` is already correctly set via `subprocess.Popen(cmd, cwd=str(self._worktree_paths[i]))` on line 105 of the `run()` method.

**Fix:** Remove `"--cwd", str(wt_path)` from the returned command list:
```python
return ["claude", "-p", prompt]
```

**Test impact:** `tests/mlforge/test_swarm.py` line 181 asserts `"--cwd" in cmd`. This assertion must be removed/inverted to `"--cwd" not in cmd`.

**Confidence:** HIGH -- verified by reading swarm module source.

## Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `src/mlforge/engine.py` | Fix `_compute_baselines()` to call `load_data()` + `split_data()` | 500-528 |
| `src/mlforge/cli.py` | Add `--enable-drafts` argparse argument + wiring | ~90 (new arg), ~133 (wiring) |
| `src/mlforge/swarm/__init__.py` | Remove `--cwd` from `_build_agent_command()` | 159 |
| `tests/mlforge/test_engine.py` | Update `test_compute_baselines_called_before_loop` to use functions | ~684 |
| `tests/mlforge/test_swarm.py` | Change `--cwd` assertion to negative | 181 |

## Common Pitfalls

### Pitfall 1: Dataset File Path Resolution
**What goes wrong:** `load_data()` needs the full path to the CSV, but `csv_path` in plugin_settings is just a filename (set as `dataset_path.name` per decision [Phase 09]).
**How to avoid:** Construct the full path as `self.experiment_dir / csv_path`.

### Pitfall 2: Scaffold Copies Dataset to experiment_dir
**What goes wrong:** Assuming the dataset is in the original location.
**How to avoid:** The scaffold copies the dataset into `target_dir`. Use `self.experiment_dir / csv_path`.

### Pitfall 3: Module-Level Side Effects in prepare.py
**What goes wrong:** `exec_module()` on `prepare.py` imports numpy, pandas, sklearn at module level. This is fine -- these are required ML deps (decision [02-01]).
**How to avoid:** No special handling needed, but wrap in try/except for robustness.

### Pitfall 4: Test Uses Module-Level Variables
**What goes wrong:** The existing test at line 684 creates a `prepare.py` with module-level `X_train`/`y_train`. After the fix, the test needs to provide a `prepare.py` with `load_data()` and `split_data()` functions instead, plus a CSV file for `load_data()` to read.
**How to avoid:** Update the test to write a minimal CSV and a `prepare.py` that defines the two functions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Baseline computation | Custom naive baselines | `compute_baselines()` from `tabular/baselines.py` | Already tested, uses sklearn DummyClassifier/Regressor |
| Data loading | Custom CSV parsing | `prepare.load_data()` + `prepare.split_data()` | Already tested, handles CSV/Parquet, proper train/test split |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml (pytest section) |
| Quick run command | `python3 -m pytest tests/mlforge/test_engine.py tests/mlforge/test_swarm.py tests/mlforge/test_cli.py -x -q` |
| Full suite command | `python3 -m pytest -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTL-01 | `_compute_baselines()` calls `load_data()`+`split_data()` and populates `state.baselines` | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestIntelligenceIntegration::test_compute_baselines_called_before_loop -x` | Exists (needs update) |
| INTL-02 | Baseline gate rejects sub-baseline keeps | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestIntelligenceIntegration -x` | Exists (gate logic unchanged) |
| INTL-05 | `--enable-drafts` CLI flag sets `config.enable_drafts = True` | unit | `python3 -m pytest tests/mlforge/test_cli.py -x -k "enable_drafts"` | Needs new test |
| SWARM-01 | `_build_agent_command()` does NOT include `--cwd` | unit | `python3 -m pytest tests/mlforge/test_swarm.py::TestBuildAgentCommand -x` | Exists (needs assertion flip) |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/mlforge/test_engine.py tests/mlforge/test_swarm.py tests/mlforge/test_cli.py -x -q`
- **Per wave merge:** `python3 -m pytest -x -q`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
- [ ] `tests/mlforge/test_cli.py` -- add test for `--enable-drafts` flag
- [ ] `tests/mlforge/test_engine.py` -- update baseline test to use function-based prepare.py
- [ ] `tests/mlforge/test_swarm.py` -- flip `--cwd` assertion

## Sources

### Primary (HIGH confidence)
- `src/mlforge/engine.py` -- direct source code reading, `_compute_baselines()` lines 500-528
- `src/mlforge/tabular/prepare.py` -- direct source code reading, confirms function-based API (no module-level X_train/y_train)
- `src/mlforge/cli.py` -- direct source code reading, confirms no `--enable-drafts` argument
- `src/mlforge/swarm/__init__.py` -- direct source code reading, confirms `--cwd` on line 159
- `src/mlforge/config.py` -- direct source code reading, confirms `enable_drafts: bool = False` default

## Metadata

**Confidence breakdown:**
- Bug 1 (baseline gate): HIGH -- verified by reading both producer (prepare.py) and consumer (engine.py)
- Bug 2 (enable-drafts): HIGH -- trivial argparse addition, config field already exists
- Bug 3 (--cwd flag): HIGH -- verified by reading swarm module, subprocess already sets cwd

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable codebase, no external dependencies changing)
