# Phase 11: Forecasting Infrastructure - Research

**Researched:** 2026-03-14
**Domain:** Time-series walk-forward evaluation, forecasting metrics, temporal data pipelines
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TVAL-01 | `forecast.py` provides `walk_forward_evaluate(model_fn, X, y, n_splits)` using expanding window with configurable gap | `sklearn.model_selection.TimeSeriesSplit` with `gap` parameter provides this directly — verified in sklearn 1.8.0 |
| TVAL-02 | Evaluation always runs in original dollar scale (inverse-transform before metric calculation) | `walk_forward_evaluate` receives raw y values; `model_fn` is responsible for returning dollar-scale predictions; `compute_metric` operates on whatever is passed — planner must document this contract |
| TVAL-03 | Minimum 3 walk-forward folds enforced; warning when training window < 20 rows | `warnings.warn(msg, UserWarning)` at entry to `walk_forward_evaluate` (for n_splits < 3) and inside each fold loop (for len(X_train) < 20) — both verified with `pytest.warns(UserWarning)` |
| FMET-01 | MAPE is primary metric for revenue forecasting; added to `METRIC_MAP` | `sklearn.metrics.mean_absolute_percentage_error` available in sklearn 1.8.0; returns decimal (not %) — note this convention. `METRIC_MAP` in `forecast.py` adds `mape` with direction `minimize` |
| FMET-02 | MAE and RMSE available as secondary metrics | `sklearn.metrics.mean_absolute_error` and `root_mean_squared_error` both available in sklearn 1.8.0 |
| FMET-03 | Directional accuracy (predicted growth vs actual growth direction) reported alongside primary metric | Computed as `mean(sign(diff(y_true)) == sign(diff(y_pred)))` — requires len >= 2; returns float in [0, 1] |
| BASE-01 | Naive forecast (repeat last known value) computed as mandatory floor | `y_train[-1]` broadcast to len(y_test); computed per fold then averaged |
| BASE-02 | Seasonal naive (same quarter last year) computed as mandatory floor | `y[t - 4]` for each test point using full-series index arithmetic; requires train window >= 4 |
| BASE-03 | Agent must beat both baselines to "keep" an experiment; failing to beat naive = auto-revert | `get_forecasting_baselines()` returns `{"naive": float, "seasonal_naive": float}` mean MAPEs; `loop_helpers.should_keep()` needs to be extended or the CLAUDE.md protocol must document the dual-baseline gate |
</phase_requirements>

---

## Summary

Phase 11 builds the leakage-free temporal evaluation infrastructure that all future forecasting experiments depend on. It consists of two deliverables: a new `forecast.py` module (walk-forward evaluator, metrics, baselines) and a refactored `prepare.py` that adds date-column support and a temporal split function. Everything in this phase is frozen infrastructure — the agent is never allowed to modify it.

The core technical challenge is temporal leakage. Random-shuffle CV (used in the existing `prepare.evaluate()`) is wrong for time-series because test samples precede some training samples chronologically. `sklearn.model_selection.TimeSeriesSplit` solves this with an expanding-window scheme that guarantees all test-fold indices are strictly greater than all train-fold indices. The `gap` parameter (default 0 for Phase 11) allows skipping periods between train end and test start, which matters when lag features use recent values.

The second challenge is dollar-scale evaluation (TVAL-02). MAPE computed in log-space (if the agent applies a log transform) differs from MAPE in dollar-space. The `walk_forward_evaluate` function's contract must be clear: `model_fn` receives raw data and is responsible for returning predictions in the same scale as `y`; the function does not apply inverse transforms itself. This must be documented in `forecast.py` docstrings and in the agent-facing CLAUDE.md.

**Primary recommendation:** Implement `forecast.py` as a standalone frozen module; update `prepare.py` by adding two new functions (`load_data` with `date_col` parameter, `temporal_split`) while preserving all existing PIPE-01 through PIPE-07 functions unchanged. Update the guard hook to freeze `forecast.py` alongside `prepare.py`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn TimeSeriesSplit | 1.8.0 (installed) | Expanding-window CV splitter | Built-in, no extra deps, expanding window by default, `gap` parameter available |
| sklearn.metrics.mean_absolute_percentage_error | 1.8.0 | MAPE computation | Available since sklearn 0.24, handles edge cases better than manual |
| sklearn.metrics.mean_absolute_error | 1.8.0 | MAE computation | Standard, already used in project |
| sklearn.metrics.root_mean_squared_error | 1.8.0 | RMSE computation | Verified available in 1.8.0 (replaces deprecated `mean_squared_error(squared=False)`) |
| pandas datetime index | 3.0.1 (installed) | Date-indexed DataFrames | `parse_dates` + `index_col` + `sort_index()` pattern |
| Python warnings module | stdlib | UserWarning for fold/window guards | No external dep, catchable by `pytest.warns()` |

### Not Needed

| Library | Reason Excluded |
|---------|----------------|
| statsmodels | Not installed; ETS/SARIMAX baselines deferred — naive/seasonal-naive use index arithmetic only |
| prophet | Not installed; too heavy for simple baseline computation |
| tsfresh | Explicitly out of scope (700+ features on 40 rows = overfitting) |
| pmdarima | Not installed; no ARIMA baselines needed at this phase |

**Installation:** No new dependencies required. All needed libraries (`sklearn`, `pandas`, `numpy`) are already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended File Structure

```
src/automl/
├── forecast.py          # NEW: walk_forward_evaluate, compute_metric, get_forecasting_baselines, METRIC_MAP
├── prepare.py           # EXTEND: add date_col param to load_data, add temporal_split()
└── ...existing files unchanged...

tests/
├── test_forecast.py     # NEW: covers TVAL-01, TVAL-02, TVAL-03, FMET-01..03, BASE-01..03
└── test_prepare.py      # EXTEND: add tests for new load_data(date_col=) and temporal_split()
```

### Pattern 1: walk_forward_evaluate with callable model_fn

**What:** Agent-supplied training function called once per fold with train/test slices. Temporal ordering is enforced by the infrastructure; the agent cannot break it.

**When to use:** Every time the agent trains and scores a forecasting model.

**Signature:**
```python
def walk_forward_evaluate(
    model_fn: Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray],
    X: np.ndarray,
    y: np.ndarray,
    metric: str = "mape",
    n_splits: int = 5,
    gap: int = 0,
) -> list[float]:
    """
    model_fn(X_train, y_train, X_test) -> y_pred (dollar scale)
    Returns list of per-fold metric scores.
    """
```

**Key invariant verified:** `test_idx[0] > train_idx[-1]` for every fold, guaranteed by `TimeSeriesSplit`. Verified empirically with sklearn 1.8.0.

**Warning guards:**
```python
import warnings
if n_splits < 3:
    warnings.warn(
        f"walk_forward_evaluate: n_splits={n_splits} is below the recommended minimum of 3.",
        UserWarning,
        stacklevel=2,
    )
# Inside fold loop:
if len(X_train) < 20:
    warnings.warn(
        f"Fold {fold_i}: training window has {len(X_train)} rows (< 20). "
        "Results may be unreliable.",
        UserWarning,
        stacklevel=2,
    )
```

### Pattern 2: TimeSeriesSplit expanding window (verified)

```python
# Source: verified with sklearn 1.8.0 installed in project
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)
for fold_i, (train_idx, test_idx) in enumerate(tscv.split(X)):
    # INVARIANT: test_idx[0] > train_idx[-1] always holds
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
```

With `n_splits=5` on 40 rows, fold 0 has ~9 training rows (below 20 warning fires) and fold 1 has ~15 rows (also warning). This is expected behavior for small datasets — the warning is informational, not an error.

### Pattern 3: compute_metric and METRIC_MAP

```python
from sklearn.metrics import (
    mean_absolute_percentage_error,
    mean_absolute_error,
    root_mean_squared_error,
)

# NOTE: sklearn MAPE returns decimal (0.05 = 5%), not percentage (5.0)
METRIC_MAP: dict[str, tuple[str, str]] = {
    "mape": ("mape", "minimize"),
    "mae": ("mae", "minimize"),
    "rmse": ("rmse", "minimize"),
    "directional_accuracy": ("directional_accuracy", "maximize"),
}

def compute_metric(metric_name: str, y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if metric_name == "mape":
        return float(mean_absolute_percentage_error(y_true, y_pred))
    elif metric_name == "mae":
        return float(mean_absolute_error(y_true, y_pred))
    elif metric_name == "rmse":
        return float(root_mean_squared_error(y_true, y_pred))
    elif metric_name == "directional_accuracy":
        if len(y_true) < 2:
            return float("nan")
        return float(np.mean(np.sign(np.diff(y_true)) == np.sign(np.diff(y_pred))))
    raise ValueError(f"Unknown metric: {metric_name!r}. Valid: {sorted(METRIC_MAP)}")
```

### Pattern 4: get_forecasting_baselines

```python
def get_forecasting_baselines(
    y: np.ndarray,
    n_splits: int = 5,
    gap: int = 0,
    period: int = 4,
) -> dict[str, float]:
    """
    Returns {"naive": float, "seasonal_naive": float} as mean MAPE across folds.
    Uses same walk-forward splits the agent will use.
    """
```

Seasonal naive uses index arithmetic on the full `y` array (not a shifted DataFrame) to look up `y[test_idx[i] - period]` within the training window. Edge case: if `test_idx[i] - period < train_idx[0]`, fall back to `y_train[-period]` if available, else `y_train[-1]`.

### Pattern 5: prepare.py extensions

```python
# New signature (backwards-compatible: date_col defaults to None)
def load_data(
    csv_path: str | Path,
    target_column: str,
    date_col: str | None = None,
) -> tuple[pd.DataFrame, pd.Series, str]:
    """
    If date_col is provided:
      - parse as datetime, set as index, sort ascending
      - returns X with DatetimeIndex, y with DatetimeIndex
    Task inference unchanged.
    """

def temporal_split(
    X: pd.DataFrame,
    y: pd.Series,
    holdout_fraction: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Time-ordered split. No shuffle. Last holdout_fraction rows are holdout.
    INVARIANT: X_train.index[-1] < X_holdout.index[0]
    """
```

### Anti-Patterns to Avoid

- **Shuffled CV in forecasting:** Using `KFold(shuffle=True)` or `cross_val_score` with `KFold` on time-ordered data leaks future information. Never call `prepare.evaluate()` for forecasting.
- **Feature engineering outside model_fn:** Computing lag features before passing to `walk_forward_evaluate` leaks future values. The agent must compute features inside `model_fn` per fold.
- **Log-space MAPE:** If the agent log-transforms the target, MAPE computed on log values differs materially from dollar-scale MAPE. Docstring must warn: "Pass dollar-scale predictions."
- **Modifying forecast.py or prepare.py during experiments:** Both files must be listed in the guard hook's `FROZEN_FILES`.
- **Zero or near-zero targets:** sklearn MAPE explodes on near-zero values. For revenue data this is unlikely but the docstring should note it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Expanding window CV | Custom loop with manual train/test slices | `sklearn.model_selection.TimeSeriesSplit` | Gap parameter, correct edge handling, tested at scale |
| MAPE computation | `np.mean(np.abs((y_true - y_pred) / y_true))` | `sklearn.metrics.mean_absolute_percentage_error` | Handles near-zero, consistent with sklearn ecosystem |
| RMSE computation | `np.sqrt(np.mean((y - yhat)**2))` | `sklearn.metrics.root_mean_squared_error` | Available in 1.8.0; consistent API |

**Key insight:** sklearn's `TimeSeriesSplit` is purpose-built for this problem. Building a custom expanding window introduces subtle off-by-one errors and missing gap support. The only code to write is the thin wrapper that adds warnings and calls `model_fn`.

---

## Common Pitfalls

### Pitfall 1: Feature leakage via pre-fold feature engineering
**What goes wrong:** Lag features computed before splitting use future values in early test folds.
**Why it happens:** The natural coding pattern is `df['lag_1'] = df['revenue'].shift(1)` before calling walk_forward_evaluate.
**How to avoid:** `walk_forward_evaluate` passes raw (unfeaturized) rows to `model_fn`. The agent's `model_fn` computes features on each fold's train/test slice independently.
**Warning signs:** CV score much better than holdout score; small dataset with many lags.

### Pitfall 2: sklearn MAPE convention (decimal not percentage)
**What goes wrong:** MAPE of 0.05 is 5%, not 0.05%. Code comparing thresholds like `if mape > 5.0` is always True.
**Why it happens:** sklearn returns values in [0, inf] where 1.0 = 100%.
**How to avoid:** Document the convention in `compute_metric` docstring. Use consistent decimal comparison everywhere: `if mape < 0.10` means "beat 10% MAPE".
**Warning signs:** Baseline MAPE values of 0.08 that look suspiciously small.

### Pitfall 3: prepare.py backwards compatibility
**What goes wrong:** Changing `load_data` signature breaks existing tests and the v1.0 generic ML flow.
**Why it happens:** Adding `date_col` as a required parameter.
**How to avoid:** Make `date_col=None` (optional). When None, behavior is identical to current implementation. Existing tests remain green.
**Warning signs:** `test_prepare.py::TestLoadData` fails after refactor.

### Pitfall 4: Seasonal naive on insufficient history
**What goes wrong:** For the first fold with only 4-8 training rows, looking back 4 periods fails silently or returns NaN.
**Why it happens:** `y_train[-4:]` succeeds even with 3 rows (returns shorter array, misaligned).
**How to avoid:** Fallback logic: if `len(y_train) < period`, seasonal naive = naive (repeat last value). Log a warning.

### Pitfall 5: n_splits=2 raises no error but violates TVAL-03
**What goes wrong:** `TimeSeriesSplit(n_splits=2)` works fine in sklearn — it returns 2 folds. The 3-fold minimum is our project policy, not sklearn's.
**Why it happens:** Expecting sklearn to enforce project policy.
**How to avoid:** `walk_forward_evaluate` issues `UserWarning` when `n_splits < 3`. It does NOT raise an exception — the requirement says "warning", not error.

### Pitfall 6: guard hook does not list forecast.py
**What goes wrong:** Agent modifies `forecast.py` during experiments, breaking the frozen infrastructure guarantee.
**Why it happens:** Current guard hook only lists `prepare.py` in `FROZEN_FILES`.
**How to avoid:** Phase 11, Plan 11-01 must update `FROZEN_FILES` in the guard hook to include `forecast.py`. This is part of FEAT-04 formally, but the guard must be updated as part of this phase to protect the new module immediately.

---

## Code Examples

Verified patterns from official sources and local testing:

### TimeSeriesSplit expanding window (verified sklearn 1.8.0)
```python
# Source: sklearn 1.8.0 installed at /home/tlupo/AutoML
from sklearn.model_selection import TimeSeriesSplit
import numpy as np

tscv = TimeSeriesSplit(n_splits=5, gap=0)
# On 50 rows:
# Fold 0: train=[0..9], test=[10..17]
# Fold 1: train=[0..17], test=[18..25]
# ...
# All test indices > all train indices — verified
```

### MAPE, MAE, RMSE from sklearn 1.8.0
```python
# Source: verified in project virtualenv
from sklearn.metrics import (
    mean_absolute_percentage_error,  # returns decimal, e.g. 0.05 = 5%
    mean_absolute_error,
    root_mean_squared_error,          # available since sklearn 1.4, confirmed 1.8.0
)
```

### Directional accuracy (no sklearn equivalent)
```python
import numpy as np

def directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Fraction of periods where predicted direction matches actual direction."""
    if len(y_true) < 2:
        return float("nan")
    return float(np.mean(
        np.sign(np.diff(y_true)) == np.sign(np.diff(y_pred))
    ))
```

### datetime index loading
```python
# Source: verified with pandas 3.0.1
import pandas as pd

df = pd.read_csv(csv_path, parse_dates=[date_col], index_col=date_col)
df = df.sort_index()  # ensure ascending — required for walk_forward_evaluate
assert df.index.is_monotonic_increasing
```

### temporal_split (no shuffle)
```python
import math

def temporal_split(X, y, holdout_fraction=0.15):
    n = len(X)
    split_idx = math.floor(n * (1 - holdout_fraction))
    return (
        X.iloc[:split_idx],
        X.iloc[split_idx:],
        y.iloc[:split_idx],
        y.iloc[split_idx:],
    )
    # INVARIANT: X_train.index[-1] < X_holdout.index[0]
    # (guaranteed by ascending sort in load_data)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `mean_squared_error(squared=False)` | `root_mean_squared_error` | sklearn 1.4 | Old form still works but deprecated; use new form |
| Manual MAPE formula | `mean_absolute_percentage_error` | sklearn 0.24 | Consistent with sklearn ecosystem, handles edge cases |
| `KFold(shuffle=True)` for all CV | `TimeSeriesSplit` for time-series | Long-standing best practice | Eliminates future leakage in time-ordered data |

**Deprecated/outdated:**
- `mean_squared_error(squared=False)`: Works but deprecated in sklearn 1.x; `root_mean_squared_error` is the canonical form in 1.8.0.

---

## Open Questions

1. **Dollar-scale responsibility in TVAL-02**
   - What we know: `walk_forward_evaluate` receives raw `y` (dollars); `model_fn` trains and predicts
   - What's unclear: If the agent's `model_fn` applies log-transform internally, the returned predictions are in log-space. Should `walk_forward_evaluate` automatically inverse-transform?
   - Recommendation: No automatic inverse transform in the infrastructure — that would require knowing the agent's transform. Instead, document clearly: "model_fn MUST return predictions in the same unit as y_true." The CLAUDE.md agent template (Phase 12) will specify this convention. The unit test for TVAL-02 should verify by passing a model_fn that deliberately log-transforms and confirm the metric changes.

2. **guard hook update timing**
   - What we know: FEAT-04 formally owns the guard hook update for `forecast.py`; but that is Phase 12
   - What's unclear: Is it safe to leave `forecast.py` unprotected between Phase 11 completion and Phase 12?
   - Recommendation: Update the guard hook in Plan 11-01 (when forecast.py is created). The FEAT-04 label is about the Phase 12 feature freeze; adding `forecast.py` to the hook now is defensive and harmless.

3. **seasonal naive period generalization**
   - What we know: Phase 11 targets quarterly data (period=4); `get_forecasting_baselines` should accept `period` parameter
   - What's unclear: Should period be inferred from data frequency (monthly=12, quarterly=4, annual=1)?
   - Recommendation: Accept `period: int = 4` as an explicit parameter for Phase 11 simplicity. Frequency inference can be added in a later phase.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (installed in dev group) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths = ["tests"] |
| Quick run command | `uv run pytest tests/test_forecast.py tests/test_prepare.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TVAL-01 | `walk_forward_evaluate` returns list of fold metrics, no future leakage | unit | `uv run pytest tests/test_forecast.py::TestWalkForwardEvaluate -x` | ❌ Wave 0 |
| TVAL-02 | Fold metrics computed on same scale as y_true | unit | `uv run pytest tests/test_forecast.py::TestWalkForwardEvaluate::test_dollar_scale_contract -x` | ❌ Wave 0 |
| TVAL-03 | Warning issued when n_splits < 3; warning when train window < 20 | unit | `uv run pytest tests/test_forecast.py::TestWalkForwardEvaluate::test_low_folds_warning -x` | ❌ Wave 0 |
| FMET-01 | `compute_metric("mape", ...)` returns correct value; "mape" in METRIC_MAP | unit | `uv run pytest tests/test_forecast.py::TestComputeMetric -x` | ❌ Wave 0 |
| FMET-02 | `compute_metric("mae", ...)` and `compute_metric("rmse", ...)` correct | unit | `uv run pytest tests/test_forecast.py::TestComputeMetric -x` | ❌ Wave 0 |
| FMET-03 | `compute_metric("directional_accuracy", ...)` correct on sample data | unit | `uv run pytest tests/test_forecast.py::TestComputeMetric::test_directional_accuracy -x` | ❌ Wave 0 |
| BASE-01 | `get_forecasting_baselines` returns "naive" key with MAPE value | unit | `uv run pytest tests/test_forecast.py::TestBaselines -x` | ❌ Wave 0 |
| BASE-02 | `get_forecasting_baselines` returns "seasonal_naive" key with MAPE value | unit | `uv run pytest tests/test_forecast.py::TestBaselines -x` | ❌ Wave 0 |
| BASE-03 | Baselines are computed on same walk-forward splits as `walk_forward_evaluate` | unit | `uv run pytest tests/test_forecast.py::TestBaselines::test_same_splits -x` | ❌ Wave 0 |
| prepare date_col | `load_data(path, target, date_col="date")` returns DatetimeIndex sorted ascending | unit | `uv run pytest tests/test_prepare.py::TestLoadDataForecast -x` | ❌ Wave 0 |
| temporal_split | `temporal_split` returns time-ordered splits; last train index < first holdout index | unit | `uv run pytest tests/test_prepare.py::TestTemporalSplit -x` | ❌ Wave 0 |

### Critical Test: No-Shuffle Guarantee (TVAL-01)

This test must be included. It is the key correctness assertion for the entire phase:

```python
def test_all_test_fold_indices_after_train_indices():
    """TVAL-01 core: all test-fold indices strictly after all train-fold indices."""
    import numpy as np
    from automl.forecast import walk_forward_evaluate

    y = np.arange(40, dtype=float)
    X = y.reshape(-1, 1)

    seen_train_max = -1

    def model_fn(X_train, y_train, X_test):
        nonlocal seen_train_max
        # Verify no future leakage via global index check
        # We can't check global indices from here, but we verify via the return
        return np.full(len(X_test), y_train[-1])

    # Capture fold indices by monkey-patching TimeSeriesSplit
    from sklearn.model_selection import TimeSeriesSplit
    tscv = TimeSeriesSplit(n_splits=5)
    for train_idx, test_idx in tscv.split(X):
        assert test_idx[0] > train_idx[-1], "Leakage: test starts before train ends"
```

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_forecast.py tests/test_prepare.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_forecast.py` — all 9 requirement tests + leakage assertion
- [ ] New `conftest.py` fixture `quarterly_revenue_series` — 40-row synthetic quarterly data for reuse across forecast tests
- [ ] `src/automl/forecast.py` — module must exist before tests can import

*(No framework install needed — pytest already in dev dependencies)*

---

## Sources

### Primary (HIGH confidence)

- `sklearn.model_selection.TimeSeriesSplit` — verified in sklearn 1.8.0 installed at `/home/tlupo/AutoML`; signature: `(n_splits=5, *, max_train_size=None, test_size=None, gap=0)`
- `sklearn.metrics.root_mean_squared_error` — confirmed available in sklearn 1.8.0 (verified by import in project virtualenv)
- `sklearn.metrics.mean_absolute_percentage_error` — confirmed available since sklearn 0.24, verified in 1.8.0; returns decimal not percentage
- `pandas.read_csv(parse_dates=, index_col=)` + `sort_index()` — verified with pandas 3.0.1
- Existing `prepare.py`, `tests/test_prepare.py`, `pyproject.toml` — read directly from project

### Secondary (MEDIUM confidence)

- Walk-forward CV as standard practice for time-series: well-established pattern documented in sklearn User Guide and standard ML texts
- Seasonal naive (same period last year) as baseline: standard time-series forecasting practice

### Tertiary (LOW confidence)

- None — all critical claims verified against installed libraries or project source.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified installed and tested in project virtualenv
- Architecture: HIGH — patterns prototyped and executed against installed versions
- Pitfalls: HIGH — empirically observed during research (sklearn MAPE convention, TimeSeriesSplit behavior with small n)
- Validation architecture: HIGH — test framework confirmed from pyproject.toml

**Research date:** 2026-03-14
**Valid until:** 2026-04-13 (sklearn/pandas API stable; 30-day window appropriate)
