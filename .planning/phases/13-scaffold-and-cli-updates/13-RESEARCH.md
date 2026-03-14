# Phase 13: Scaffold and CLI Updates - Research

**Researched:** 2026-03-14
**Domain:** argparse CLI extension, scaffold branching logic, forecasting program.md template, pandas frequency inference
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCAF-01 | CLI accepts `--date-column` flag to enable forecasting mode | argparse `add_argument("--date-column", default=None)` pattern; existing flag tests in `test_cli.py` show the established test pattern for new flags |
| SCAF-02 | Scaffold generates forecasting-specific `train.py`, `CLAUDE.md`, and `program.md` when date column specified | `scaffold_experiment()` already has all three files; Phase 13 adds a branch on `date_col` to select `train_template_forecast.py` and `claude_forecast.md.tmpl` instead of their v1.0 equivalents |
| SCAF-03 | `program.md` includes data summary with time range, frequency, and naive baseline scores | `load_data(date_col=...)` returns a DatetimeIndex — time range is `X.index[0]` / `X.index[-1]`; pandas `.infer_freq()` gives frequency string; `get_forecasting_baselines()` from frozen `forecast.py` gives naive + seasonal_naive MAPE |
</phase_requirements>

---

## Summary

Phase 13 is a surgical extension to two existing files: `cli.py` and `scaffold.py`. No new source modules are needed. The work divides cleanly into three areas: (1) add `--date-column` to the argparse parser in `cli.py` and pass it through to `scaffold_experiment`; (2) add a `date_col` parameter to `scaffold_experiment()` and branch its internals to select the forecasting template and CLAUDE.md when `date_col` is provided; (3) extend `scaffold.py` with a `_format_forecast_summary()` helper and a new `render_program_md_forecast()` path (or extend the existing `render_program_md`) to include time range, inferred frequency, and naive/seasonal-naive MAPE.

The most important design constraint is **strict opt-in**: when `--date-column` is absent, `scaffold_experiment()` must produce output that is byte-identical to the current v1.0 scaffold — no behavior change for the non-forecasting path. This preserves all existing tests in `test_scaffold.py` and `test_cli.py` without modification.

The second key insight is that all the building blocks already exist. `load_data(date_col=...)` returns a DatetimeIndex-indexed DataFrame. `get_forecasting_baselines(y, n_splits=5, period=4)` returns `{"naive": float, "seasonal_naive": float}`. `train_template_forecast.py` and `claude_forecast.md.tmpl` were created in Phase 12. The scaffold simply needs to wire these together under the `date_col` branch. The only genuinely new logic is time-range extraction and frequency inference from the DatetimeIndex.

**Primary recommendation:** Add `date_col: str | None = None` to `scaffold_experiment()`. Branch on it to select templates and compute forecast-specific summary. Keep v1.0 path entirely unchanged. Add `--date-column` to argparse and pass it through. Write focused tests for the new CLI flag and the forecasting scaffold path.

---

## Standard Stack

### Core (all already installed / available)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| argparse | stdlib | `--date-column` flag | Already used in `cli.py`; same `add_argument` pattern as `--resume` and `--agents` |
| pandas DatetimeIndex | 3.0.1 (installed) | Time range extraction and frequency inference | `load_data(date_col=...)` returns DatetimeIndex; `.infer_freq()` available on the index |
| automl.forecast.get_forecasting_baselines | Phase 11 (frozen) | Compute naive + seasonal_naive MAPE for program.md | Takes `y` array, `n_splits`, `period`; returns `{"naive": float, "seasonal_naive": float}` |
| automl.train_template_forecast | Phase 12 (created) | Source for forecasting `train.py` | Already exists at `src/automl/train_template_forecast.py`; scaffold copies and substitutes config vars |
| automl.templates.claude_forecast.md.tmpl | Phase 12 (created) | Source for forecasting `CLAUDE.md` | Already exists at `src/automl/templates/claude_forecast.md.tmpl`; `render_claude_md_forecast()` (to be added) reads it |

### No New Dependencies

All required libraries are already installed. Phase 13 adds zero new package dependencies.

---

## Architecture Patterns

### Recommended Change Set

```
src/automl/
├── cli.py               # ADD: --date-column flag; pass date_col to scaffold_experiment
├── scaffold.py          # ADD: date_col param to scaffold_experiment; branching logic;
│                        #      _format_forecast_summary(); render_claude_md_forecast()
│                        #      or extend templates/__init__.py
└── templates/
    └── __init__.py      # ADD: render_claude_md_forecast() function (reads claude_forecast.md.tmpl)

tests/
├── test_cli.py          # ADD: TestCliDateColumnFlag class (mirrors TestCliAgentsFlag pattern)
└── test_scaffold.py     # ADD: TestScaffoldForecasting class (mirrors TestScaffoldCreatesAllFiles)
```

No new source modules. No new template files.

### Pattern 1: argparse Optional String Flag

**What:** `--date-column` is an optional string flag that defaults to `None`.

**Established pattern in cli.py** (mirror `--goal` which also defaults to `""`):
```python
# Source: src/automl/cli.py (verified)
parser.add_argument(
    "--date-column",
    default=None,
    help=(
        "Name of the date column to enable forecasting mode. "
        "When provided, scaffolds a forecasting experiment with "
        "train.py from the forecast template and baselines pre-computed "
        "in program.md. Without this flag, standard ML mode is used."
    ),
)
```

argparse stores hyphenated flags as underscored attributes: `args.date_column` (not `args.date-column`).

Pass-through in `cli.py` to scaffold:
```python
# In main(), after parsing args:
project_dir = scaffold_experiment(
    data_path=args.data_path,
    target_column=args.target_column,
    metric=args.metric,
    goal=args.goal,
    output_dir=args.output_dir,
    time_budget=args.time_budget,
    date_col=args.date_column,   # NEW: pass through, None by default
)
```

### Pattern 2: scaffold_experiment() Branching on date_col

**What:** Add `date_col: str | None = None` parameter; branch all template selection and summary computation on it.

**Key design constraint:** When `date_col is None`, execution must be identical to Phase 12. The branch adds only; it never modifies the existing code path.

```python
# Source: src/automl/scaffold.py structure (verified)
def scaffold_experiment(
    data_path: str | Path,
    target_column: str,
    metric: str,
    goal: str,
    output_dir: str | Path | None = None,
    time_budget: int = 60,
    date_col: str | None = None,   # NEW
) -> Path:
    ...
    # Step 1: load data (already passes date_col=None; now forward it)
    X, y, task = load_data(str(csv_path), target_column, date_col=date_col)

    # Metric validation:
    # When date_col provided, metric is "mape" -> not in prepare.py METRIC_MAP.
    # Need to bypass validate_metric for forecasting mode OR add mape to METRIC_MAP.
    # See Pitfall 1 below for the correct approach.

    # Steps 1-3 (copy prepare.py, forecast.py, generate train.py):
    if date_col is not None:
        # FORECASTING PATH
        _spec = importlib.util.find_spec("automl.train_template_forecast")
        template_source = _spec.origin
        template_content = Path(template_source).read_text()
        train_content = template_content
        train_content = train_content.replace('CSV_PATH = "data.csv"', f'CSV_PATH = "{csv_path.name}"')
        train_content = train_content.replace('TARGET_COLUMN = "target"', f'TARGET_COLUMN = "{target_column}"')
        train_content = train_content.replace('DATE_COLUMN = "date"', f'DATE_COLUMN = "{date_col}"')
        # Note: METRIC and TIME_BUDGET already default to "mape" and 120 in the forecast template
        (out / "train.py").write_text(train_content)
    else:
        # STANDARD PATH (unchanged v1.0 logic)
        _spec = importlib.util.find_spec("automl.train_template")
        ...

    # Step 4: summary and baselines
    if date_col is not None:
        summary_str = _format_forecast_summary(X, y)
        baselines_str = _format_forecast_baselines(y.values)
    else:
        preprocessor = build_preprocessor(X)
        X_processed = preprocessor.transform(X)
        baselines = get_baselines(X_processed, y, _sklearn_metric, task)
        summary = get_data_summary(X, y, task)
        summary_str = _format_summary(summary)
        baselines_str = _format_baselines(baselines)

    # Step 5: render program.md (same render_program_md call works for both paths)
    program_md = render_program_md(...)
    (out / "program.md").write_text(program_md)

    # Step 6: render CLAUDE.md
    if date_col is not None:
        claude_md = render_claude_md_forecast()   # reads claude_forecast.md.tmpl
    else:
        claude_md = render_claude_md()            # reads claude.md.tmpl (unchanged)
    (out / "CLAUDE.md").write_text(claude_md)
```

### Pattern 3: Forecast Summary (time range + frequency)

**What:** `_format_forecast_summary(X, y)` extracts DatetimeIndex info for program.md.

**pandas APIs (verified against pandas 3.0.1):**

```python
# Source: pandas documentation, verified against installed 3.0.1
import pandas as pd

def _format_forecast_summary(X: pd.DataFrame, y: pd.Series) -> str:
    """Format forecasting data summary with time range and inferred frequency."""
    lines = []
    rows = len(X)
    lines.append(f"- **Shape:** {rows} rows x {X.shape[1] + 1} columns (including target)")

    # Time range from DatetimeIndex
    start = X.index[0]
    end = X.index[-1]
    lines.append(f"- **Time range:** {start.date()} to {end.date()}")

    # Inferred frequency
    inferred = pd.infer_freq(X.index)
    freq_label = inferred if inferred is not None else "irregular (could not infer)"
    lines.append(f"- **Inferred frequency:** {freq_label}")

    # Target stats
    lines.append(
        f"- **Target stats:** mean={float(y.mean()):.2f}, "
        f"std={float(y.std()):.2f}, "
        f"min={float(y.min()):.2f}, max={float(y.max()):.2f}"
    )
    return "\n".join(lines)
```

**pandas.infer_freq() behavior (verified):**
- Quarterly start (QS): returns `"QS"` or `"QS-JAN"`
- Monthly start (MS): returns `"MS"`
- Daily (D): returns `"D"`
- Annual start (YS): returns `"YS-JAN"`
- Returns `None` when frequency cannot be inferred (irregular spacing)
- Requires at least 3 data points to infer frequency

### Pattern 4: Forecast Baselines for program.md

**What:** `_format_forecast_baselines(y_arr)` calls the frozen `get_forecasting_baselines()`.

```python
# Source: src/automl/forecast.py (verified, frozen module)
import automl.forecast as _forecast_module

def _format_forecast_baselines(y_arr: np.ndarray) -> str:
    """Compute and format naive + seasonal_naive MAPE baselines."""
    from automl.forecast import get_forecasting_baselines
    baselines = get_forecasting_baselines(y_arr, n_splits=5, period=4)
    lines = [
        f"- **Naive MAPE:** {baselines['naive']:.4f} ({baselines['naive']*100:.1f}%)",
        f"- **Seasonal Naive MAPE:** {baselines['seasonal_naive']:.4f} "
        f"({baselines['seasonal_naive']*100:.1f}%)",
    ]
    return "\n".join(lines)
```

**MAPE decimal convention reminder:** `get_forecasting_baselines()` returns decimal MAPE (0.05 = 5%, not 5.0). The format string must convert for human readability.

### Pattern 5: render_claude_md_forecast() in templates/__init__.py

**What:** Add a new `render_claude_md_forecast()` function that reads `claude_forecast.md.tmpl`. The template is static (no substitutions), just like `render_claude_md()`.

```python
# Extend src/automl/templates/__init__.py
def render_claude_md_forecast() -> str:
    """Render forecast CLAUDE.md loop protocol (static, no substitution)."""
    with open(os.path.join(_TEMPLATE_DIR, "claude_forecast.md.tmpl")) as f:
        return f.read()
```

### Pattern 6: Metric Validation in Forecasting Mode

**Critical issue:** `validate_metric("mape", "regression")` will raise `ValueError` because `"mape"` is not in `prepare.py`'s `METRIC_MAP`. The forecasting template hardcodes `METRIC = "mape"` and uses `forecast.py`'s own `METRIC_MAP` — not `prepare.py`'s.

**Correct approach:** In `scaffold_experiment()`, skip `validate_metric()` when `date_col is not None`. The forecasting path does not use `prepare.py`'s metric system at all.

```python
# In scaffold_experiment():
if date_col is not None:
    # Forecasting mode: metric validated implicitly by forecast.py
    # MAPE is the only supported metric in forecasting mode
    direction = "minimize"
    _sklearn_metric = None   # unused in forecasting path
else:
    _sklearn_metric, direction = validate_metric(metric, task)
```

Alternatively, enforce that `metric == "mape"` when `date_col` is provided and raise a clear `ValueError` if not.

### Anti-Patterns to Avoid

- **Modifying the v1.0 path:** Do not refactor existing `scaffold_experiment()` logic. Add branches only.
- **Calling validate_metric("mape", ...):** "mape" is not in `prepare.py`'s `METRIC_MAP`. Skip validation in forecasting mode.
- **Calling get_baselines() in forecasting path:** `get_baselines()` uses `DummyRegressor`/`DummyClassifier` — wrong for time-series. Use `get_forecasting_baselines()` instead.
- **Calling build_preprocessor() on DatetimeIndex data:** `build_preprocessor()` uses sklearn's `ColumnTransformer` which does not understand DatetimeIndex. In forecasting mode, skip the preprocessor entirely — features are built from `y` inside `model_fn`.
- **Passing `--date-column` to swarm path:** The swarm code path calls `load_data(args.data_path, args.target_column)` — no `date_col`. When `--date-column` is provided with `--agents > 1`, the swarm path would need the same pass-through. Check whether swarm + forecasting is in scope for Phase 13 (likely NOT — treat as unsupported for now, document limitation).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Naive/seasonal baselines for program.md | Manual `y[-1]` computation | `get_forecasting_baselines()` from frozen `forecast.py` | Frozen module guarantees same fold boundaries as agent's walk-forward CV |
| Frequency inference | Date arithmetic on index diff | `pd.infer_freq(X.index)` | Handles QS, MS, D, W, etc. correctly; returns None for irregular |
| MAPE display | `mean(abs(y - y_hat) / y)` | Already in baselines dict from `get_forecasting_baselines()` | No hand-rolling needed at all — just format the returned values |
| Template substitution | Custom string.Template or regex | Simple `str.replace()` | Existing scaffold pattern uses `content.replace(...)` — proven, consistent |

---

## Common Pitfalls

### Pitfall 1: validate_metric("mape", ...) Raises ValueError

**What goes wrong:** `prepare.py`'s `METRIC_MAP` does not include `"mape"`. Calling `validate_metric("mape", "regression")` raises `ValueError: Unknown metric 'mape'`. This would break `scaffold_experiment()` immediately when `--date-column` is provided.

**Why it happens:** `prepare.py` is a frozen module designed for v1.0 classification/regression. Adding `"mape"` to it would require modifying a frozen file.

**How to avoid:** Branch before calling `validate_metric()`. When `date_col is not None`, skip it entirely and hardcode `direction = "minimize"`. The forecasting path uses `forecast.py`'s own metric system.

**Warning signs:** `ValueError: Unknown metric 'mape'` in scaffold test for forecasting mode.

### Pitfall 2: DATE_COLUMN substitution in train_template_forecast.py

**What goes wrong:** `train_template_forecast.py` has `DATE_COLUMN = "date"` hardcoded. If scaffold forgets to substitute this, experiments will try to read a column named `"date"` regardless of what the user passed.

**How to avoid:** Add `.replace('DATE_COLUMN = "date"', f'DATE_COLUMN = "{date_col}"')` to the forecasting branch template substitution code. Verify in tests that `DATE_COLUMN` in the generated `train.py` matches the `--date-column` argument.

**Warning signs:** `KeyError: 'date'` when running `uv run python train.py` after scaffold.

### Pitfall 3: METRIC and TIME_BUDGET in forecast template

**What goes wrong:** `train_template_forecast.py` has `METRIC = "mape"` and `TIME_BUDGET = 120`. The existing substitution logic uses `content.replace('METRIC = "accuracy"', f'METRIC = "{metric}"')` — this won't match the forecast template's `METRIC = "mape"`.

**How to avoid:** In the forecasting branch, use the correct source string: `.replace('METRIC = "mape"', f'METRIC = "{metric}"')`. Since forecasting always uses MAPE, this substitution may be a no-op, but it should still be present for correctness. For `TIME_BUDGET`, the forecast template uses `TIME_BUDGET = 120` (not `60` like the v1.0 template) — substitute accordingly.

**Warning signs:** `train.py` in forecasting experiment has `METRIC = "accuracy"` or `TIME_BUDGET = 60`.

### Pitfall 4: pd.infer_freq() Needs 3+ Points

**What goes wrong:** `pd.infer_freq(index)` returns `None` when called on fewer than 3 timestamps, even if the spacing is regular. This shouldn't happen with real data but could trip up tests using minimal fixtures.

**How to avoid:** Always handle `None` return: `freq_label = inferred or "irregular"`. Use the `sample_forecast_csv` fixture (40 rows) in tests — it has enough points for reliable inference.

### Pitfall 5: Swarm Path Not Updated for date_col

**What goes wrong:** In `cli.py`, after scaffolding, if `args.agents > 1`, the swarm path calls `load_data(args.data_path, args.target_column)` without `date_col`. This would silently load data without the DatetimeIndex.

**How to avoid:** For Phase 13, document that `--agents N` combined with `--date-column` is not supported. Either guard it with a clear error or accept it as a known limitation. The simplest guard: check for the combination and return an error early.

```python
if args.agents > 1 and args.date_column is not None:
    print("Error: --agents is not supported with --date-column in this version.", file=sys.stderr)
    return 1
```

### Pitfall 6: build_preprocessor() Called on DatetimeIndex X

**What goes wrong:** `build_preprocessor(X)` iterates over column dtypes. When `X` has only a DatetimeIndex and non-numeric feature columns, the transformer may fail or produce unexpected output. In the `sample_forecast_csv` fixture, `X` has `feature1` and `feature2` — so the preprocessor would succeed but its output is meaningless for forecasting.

**How to avoid:** In the forecasting path, do not call `build_preprocessor()` or `get_baselines()` at all. These are v1.0 primitives that are not used in forecasting experiments.

---

## Code Examples

### Full scaffold_experiment() Signature Change

```python
# Source: src/automl/scaffold.py (current signature + proposed extension)
def scaffold_experiment(
    data_path: str | Path,
    target_column: str,
    metric: str,
    goal: str,
    output_dir: str | Path | None = None,
    time_budget: int = 60,
    date_col: str | None = None,    # NEW: None = standard mode, str = forecasting mode
) -> Path:
```

### cli.py Addition

```python
# Source: src/automl/cli.py (proposed addition, mirrors existing flag patterns)
parser.add_argument(
    "--date-column",
    default=None,
    help=(
        "Name of the date column to enable forecasting mode. "
        "Scaffolds a forecasting experiment with time-series templates "
        "and pre-computed naive/seasonal-naive MAPE baselines in program.md."
    ),
)

# In the scaffold_experiment() call:
project_dir = scaffold_experiment(
    data_path=args.data_path,
    target_column=args.target_column,
    metric=args.metric,
    goal=args.goal,
    output_dir=args.output_dir,
    time_budget=args.time_budget,
    date_col=args.date_column,   # args stores --date-column as date_column
)
```

### Forecast program.md Content Example

When `date_col="date"` is provided with the `sample_forecast_csv` fixture (40 quarterly rows, 2015-2024):

```markdown
# Program: forecast_data

## Goal

...

## Metric

mape (minimize)

All metrics use the forecast.py convention: lower is always better for MAPE.
0.05 means 5% MAPE.

## Data Description

- **Shape:** 40 rows x 3 columns (including target)
- **Time range:** 2015-01-01 to 2024-10-01
- **Inferred frequency:** QS-JAN
- **Target stats:** mean=1987.45, std=598.23, min=950.12, max=3102.67

## Baselines

- **Naive MAPE:** 0.1823 (18.2%)
- **Seasonal Naive MAPE:** 0.0712 (7.1%)
```

The agent's target: beat both baseline MAPEs to keep any experiment.

### templates/__init__.py Extension

```python
# Source: src/automl/templates/__init__.py (proposed addition)
def render_claude_md_forecast() -> str:
    """Render forecast CLAUDE.md loop protocol (no substitution — static file)."""
    with open(os.path.join(_TEMPLATE_DIR, "claude_forecast.md.tmpl")) as f:
        return f.read()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single scaffold path (v1.0 ML only) | Branching scaffold: standard vs. forecasting | Phase 13 (this phase) | Strict opt-in: `--date-column` required; no behavior change for existing users |
| No time-series templates | `train_template_forecast.py` + `claude_forecast.md.tmpl` | Phase 12 | Templates exist; Phase 13 wires them into the scaffold |
| Dummy baselines (mean/median) in program.md | Walk-forward naive + seasonal-naive MAPE in program.md | Phase 13 | Agent knows the baseline it must beat before starting experiments |

---

## Open Questions

1. **Should metric validation for "mape" be enforced in forecasting mode?**
   - What we know: `validate_metric("mape", ...)` raises `ValueError` — mape is not in `prepare.py`'s `METRIC_MAP`
   - What's unclear: Whether to silently use "mape" always in forecasting mode, or allow user to pass any metric and validate against `forecast.py`'s `METRIC_MAP`
   - Recommendation: Simplest approach — when `date_col` is provided, ignore the user's `metric` argument and always use "mape". Print a note if the user passed a non-mape metric. This matches REQUIREMENTS.md which specifically says "mape" for forecasting.

2. **Should `--agents` + `--date-column` be supported or rejected?**
   - What we know: The swarm path calls `load_data` without `date_col`; swarm templates are not forecast-specific
   - What's unclear: Whether the swarm code path needs forecasting support
   - Recommendation: Return error code 1 with a clear message: "Swarm mode (--agents) is not supported with forecasting mode (--date-column) in v2.0." Phase 14 EVAL requirements do not mention swarm + forecasting.

3. **Should program.md use a different template for forecasting?**
   - What we know: The existing `program.md.tmpl` has a "Metric" section that says "All metrics use the sklearn convention: higher is always better" — this is wrong for MAPE (lower is better)
   - What's unclear: Whether to create a new `program_forecast.md.tmpl` or patch the existing template
   - Recommendation: Create a new `_forecast_program_md()` helper that generates the content directly (without using the template file) for the forecasting path. The existing template is used only for the v1.0 path. This avoids template proliferation and keeps the change contained.

---

## Validation Architecture

Nyquist validation is enabled (`nyquist_validation: true` in `.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (installed) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_cli.py tests/test_scaffold.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCAF-01 | `--date-column` flag accepted by argparse, stored as `args.date_column` | unit | `uv run pytest tests/test_cli.py::TestCliDateColumnFlag -x -q` | Wave 0 |
| SCAF-01 | `--date-column` appears in `--help` output | unit | `uv run pytest tests/test_cli.py::TestCliDateColumnFlag::test_date_column_in_help -x -q` | Wave 0 |
| SCAF-01 | `--date-column` defaults to `None` when omitted | unit | `uv run pytest tests/test_cli.py::TestCliDateColumnFlag::test_date_column_default_none -x -q` | Wave 0 |
| SCAF-02 | Forecasting scaffold produces `train.py` from `train_template_forecast.py` | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting::test_forecast_train_uses_forecast_template -x -q` | Wave 0 |
| SCAF-02 | Forecasting scaffold produces `CLAUDE.md` from `claude_forecast.md.tmpl` | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting::test_forecast_claude_md_uses_forecast_template -x -q` | Wave 0 |
| SCAF-02 | `DATE_COLUMN` in generated `train.py` matches `--date-column` arg | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting::test_forecast_train_date_column_substituted -x -q` | Wave 0 |
| SCAF-02 | Without `--date-column`, scaffold is byte-identical to v1.0 (train.py from standard template) | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldStandardPathUnchanged -x -q` | Wave 0 |
| SCAF-03 | Forecasting `program.md` includes time range (start date, end date) | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting::test_forecast_program_md_time_range -x -q` | Wave 0 |
| SCAF-03 | Forecasting `program.md` includes inferred frequency | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting::test_forecast_program_md_frequency -x -q` | Wave 0 |
| SCAF-03 | Forecasting `program.md` includes naive MAPE score | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting::test_forecast_program_md_naive_mape -x -q` | Wave 0 |
| SCAF-03 | Forecasting `program.md` includes seasonal naive MAPE score | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting::test_forecast_program_md_seasonal_naive_mape -x -q` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_cli.py tests/test_scaffold.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_cli.py` — add `TestCliDateColumnFlag` class (new class in existing file)
- [ ] `tests/test_scaffold.py` — add `TestScaffoldForecasting` class and `TestScaffoldStandardPathUnchanged` class (new classes in existing file)
- [ ] `src/automl/templates/__init__.py` — add `render_claude_md_forecast()` function
- [ ] No new test files needed — all new tests go in existing test files

---

## Sources

### Primary (HIGH confidence)

- `src/automl/cli.py` — verified current argparse structure; `--resume` and `--agents` flag patterns directly applicable to `--date-column`
- `src/automl/scaffold.py` — verified `scaffold_experiment()` signature and all internal steps; confirmed `validate_metric()` is called early; confirmed `build_preprocessor()` and `get_baselines()` are called in v1.0 path
- `src/automl/prepare.py` — verified `METRIC_MAP` does NOT contain `"mape"`; `load_data(date_col=...)` already returns DatetimeIndex; `validate_metric()` raises `ValueError` for unknown metrics
- `src/automl/forecast.py` — verified `get_forecasting_baselines(y, n_splits, gap, period)` returns `{"naive": float, "seasonal_naive": float}` in decimal MAPE
- `src/automl/train_template_forecast.py` — verified exists (Phase 12); has `DATE_COLUMN = "date"`, `METRIC = "mape"`, `TIME_BUDGET = 120` as substitution targets
- `src/automl/templates/claude_forecast.md.tmpl` — verified exists (Phase 12); static file, no substitution needed
- `src/automl/templates/__init__.py` — verified `render_claude_md()` pattern; adding `render_claude_md_forecast()` is one additional function
- `tests/conftest.py` — verified `sample_forecast_csv` fixture exists (40 quarterly rows, 2015-2024, columns: date, feature1, feature2, revenue)
- `tests/test_cli.py` — verified existing flag test patterns (`TestCliResumeFlag`, `TestCliAgentsFlag`)
- `tests/test_scaffold.py` — verified existing scaffold test patterns (`TestScaffoldCreatesAllFiles`, `TestScaffoldTrainConfig`)

### Secondary (MEDIUM confidence)

- pandas 3.0.1 `pd.infer_freq()` — API verified as available; return value of `None` for irregular/insufficient data is documented behavior

### Tertiary (LOW confidence)

None — all findings verified from code inspection of the installed project.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed; no new dependencies
- Architecture: HIGH — branching pattern is clear from existing code; all building blocks verified
- Pitfalls: HIGH — validate_metric/mape issue confirmed by reading prepare.py METRIC_MAP directly

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable domain; all changes are internal to the project)
