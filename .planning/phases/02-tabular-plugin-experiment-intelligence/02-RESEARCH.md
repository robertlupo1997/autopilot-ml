# Phase 2: Tabular Plugin + Experiment Intelligence - Research

**Researched:** 2026-03-19
**Domain:** Tabular ML plugin implementation + experiment intelligence subsystems
**Confidence:** HIGH

## Summary

Phase 2 implements two tightly coupled subsystems: (1) the first real DomainPlugin (`TabularPlugin`) that proves the Phase 1 plugin architecture works for classification/regression on CSV/Parquet data, and (2) the experiment intelligence features (baselines, diagnostics, stagnation branching, multi-draft, diff-aware iteration, results tracking) that make the autonomous loop smart. Both subsystems exist as proven patterns in the old `src/automl/` codebase (v1-v3), so this is a disciplined port into the new `mlforge` architecture -- not greenfield exploration.

The Phase 1 foundation provides: `DomainPlugin` Protocol (`plugins.py`), `Config` dataclass (`config.py`), `SessionState` with `consecutive_reverts`/`best_commit` tracking (`state.py`), `GitManager` with branch/commit/revert/tag ops (`git_ops.py`), `JournalEntry` with JSONL persistence (`journal.py`), Jinja2 template rendering (`templates/`), and hook engine (`hooks.py`). Phase 2 builds directly on all of these.

**Primary recommendation:** Organize into 3 plans: (1) TabularPlugin with prepare.py/train.py generation, baselines, and CLAUDE.md protocol; (2) Experiment intelligence engine -- diagnostics, multi-draft, stagnation, diff-aware; (3) Integration wiring -- experiment results tracking and end-to-end validation that all subsystems work together.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TABL-01 | Tabular plugin handles classification/regression on CSV/Parquet | TabularPlugin class implementing DomainPlugin Protocol; `load_data` with Parquet support; task type inference |
| TABL-02 | Plugin supports sklearn/XGBoost/LightGBM with Optuna search | Algorithm families dict from old `drafts.py`; Optuna integration in train.py template |
| TABL-03 | Leakage prevention: shift-first temporal features, walk-forward CV | Temporal validation utilities; shift-first pattern in CLAUDE.md rules |
| TABL-04 | Plugin generates domain-specific CLAUDE.md protocol | `template_context()` returns tabular-specific domain_rules; Jinja2 rendering via Phase 1 infrastructure |
| TABL-05 | Frozen prepare.py + mutable train.py generation | `scaffold()` writes prepare.py (frozen data pipeline) and train.py (mutable experiment script) |
| INTL-01 | Baseline establishment: naive + domain-specific baselines | `baselines.py` module with DummyClassifier/DummyRegressor strategies; runs at scaffold time |
| INTL-02 | Dual-baseline gate rejects experiments below both baselines | Gate function comparing metric against both baseline scores; integrated into keep/revert logic |
| INTL-03 | Diagnostics engine: worst predictions, bias, correlations | `diagnostics.py` module adapted from old `forecast.diagnose()`; generalized for classification/regression |
| INTL-04 | Branch-on-stagnation after 3 consecutive reverts | `stagnation.py` using `SessionState.consecutive_reverts` + `GitManager.create_run_branch()` |
| INTL-05 | Multi-draft start: 3-5 diverse solutions, pick best | `drafts.py` module adapted from old `automl.drafts`; algorithm families + selection logic |
| INTL-06 | Diff-aware: git diff in journal between experiments | Journal enhancement showing `git diff HEAD~1` output in experiment entries |
| INTL-08 | Results tracking in structured experiment log | Journal module already provides JSONL tracking; enhance with commit hash, timestamp, status fields |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | >=1.5 | Classification/regression models, cross-validation, preprocessing, dummy baselines | Industry standard for tabular ML; already used in old codebase |
| pandas | >=2.0 | Data loading (CSV/Parquet), feature types, data profiling | Standard tabular data manipulation; read_parquet built-in |
| numpy | >=2.0 | Array operations for metrics, diagnostics | Foundation for scikit-learn ecosystem |
| xgboost | >=2.0 | Gradient boosted trees (classification + regression) | Top performer for tabular data; multi-draft family |
| lightgbm | >=4.0 | Gradient boosted trees (fast training) | Complementary to XGBoost; different tree-building strategy |
| optuna | >=4.0 | Hyperparameter optimization | Modern Bayesian optimization; integrates well with sklearn |
| gitpython | >=3.1 | Branch-on-stagnation, diff-aware iteration | Already in Phase 1 deps |
| jinja2 | >=3.1 | CLAUDE.md template rendering | Already in Phase 1 deps |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyarrow | >=15.0 | Parquet file reading | Required for `pd.read_parquet()`; TABL-01 Parquet support |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Optuna | Hyperopt | Optuna has better pruning, cleaner API, active maintenance |
| pyarrow | fastparquet | pyarrow is faster and more widely used |
| DummyClassifier/Regressor | Custom baselines | sklearn dummies are proven, tested, and cover all standard strategies |

**Installation (additions to pyproject.toml):**
```toml
dependencies = [
    "gitpython>=3.1",
    "jinja2>=3.1",
    "scikit-learn>=1.5",
    "pandas>=2.0",
    "numpy>=2.0",
    "xgboost>=2.0",
    "lightgbm>=4.0",
    "optuna>=4.0",
    "pyarrow>=15.0",
]
```

## Architecture Patterns

### Recommended Project Structure
```
src/mlforge/
├── __init__.py              # existing
├── config.py                # existing (Phase 1)
├── state.py                 # existing (Phase 1)
├── git_ops.py               # existing (Phase 1)
├── journal.py               # existing (Phase 1) -- enhanced with diff field
├── plugins.py               # existing (Phase 1)
├── checkpoint.py            # existing (Phase 1)
├── hooks.py                 # existing (Phase 1)
├── templates/
│   ├── __init__.py          # existing (Phase 1) -- enhanced
│   ├── base_claude.md.j2    # existing (Phase 1)
│   ├── base_experiments.md.j2  # existing (Phase 1)
│   └── tabular_train.py.j2 # NEW: train.py template for tabular domain
├── tabular/                 # NEW: tabular domain plugin package
│   ├── __init__.py          # TabularPlugin class
│   ├── prepare.py           # frozen data pipeline (load, split, preprocess, evaluate)
│   └── baselines.py         # baseline computation (naive + domain-specific)
├── intelligence/            # NEW: experiment intelligence package
│   ├── __init__.py
│   ├── diagnostics.py       # error analysis (worst predictions, bias, correlations)
│   ├── drafts.py            # multi-draft generation and selection
│   └── stagnation.py        # branch-on-stagnation logic
└── results.py               # NEW: structured results tracking
```

### Pattern 1: TabularPlugin as DomainPlugin Implementation
**What:** A concrete class satisfying the `DomainPlugin` Protocol via structural subtyping.
**When to use:** Any domain-specific ML plugin.
**Example:**
```python
# Source: Phase 1 DomainPlugin Protocol + old automl patterns
class TabularPlugin:
    name: str = "tabular"
    frozen_files: list[str] = ["prepare.py"]

    def scaffold(self, target_dir: Path, config: Config) -> None:
        """Write frozen prepare.py and mutable train.py to target_dir."""
        # Copy prepare.py from mlforge.tabular.prepare source
        # Render train.py from Jinja2 template with config values
        ...

    def template_context(self, config: Config) -> dict:
        """Return tabular-specific domain rules for CLAUDE.md."""
        task = config.plugin_settings.get("task", "classification")
        return {
            "domain_rules": [
                "Use scikit-learn compatible estimators",
                "Do not modify prepare.py -- it is frozen",
                f"Task type: {task}",
                "Higher metric values are always better (sklearn convention)",
                "Must beat BOTH baselines before keeping an experiment",
                ...
            ],
            "extra_sections": [...],
        }

    def validate_config(self, config: Config) -> list[str]:
        """Validate tabular-specific config settings."""
        ...
```

### Pattern 2: Frozen prepare.py as Importable Module
**What:** The frozen `prepare.py` is a self-contained module that train.py imports. It contains `load_data`, `split_data`, `build_preprocessor`, `evaluate`, `get_baselines`, `get_data_summary`, and `validate_metric`.
**When to use:** Every tabular experiment scaffold.
**Key insight:** The old `src/automl/prepare.py` is the proven reference. The new version should be adapted (not copied verbatim) to work with the mlforge architecture, but the function signatures and behavior are well-established.

### Pattern 3: Dual-Baseline Gate
**What:** Every experiment result must beat BOTH the naive baseline AND the domain-specific baseline to be kept. This is enforced at the protocol level (CLAUDE.md rules) and can be checked programmatically.
**When to use:** Keep/revert decision logic.
**Example:**
```python
def passes_baseline_gate(
    metric_value: float,
    baselines: dict[str, float],
    direction: str,
) -> bool:
    """Return True only if metric beats ALL baselines."""
    for baseline_score in baselines.values():
        if direction == "maximize" and metric_value <= baseline_score:
            return False
        if direction == "minimize" and metric_value >= baseline_score:
            return False
    return True
```

### Pattern 4: Multi-Draft with Algorithm Families
**What:** Generate 3-5 diverse train.py variants using different model families (LogisticRegression/Ridge, RandomForest, XGBoost, LightGBM, SVM/ElasticNet), evaluate all, pick the best as the starting point.
**When to use:** Session initialization, before the iterative loop.
**Key insight:** The old `src/automl/drafts.py` has the complete implementation: `ALGORITHM_FAMILIES`, `DraftResult`, `generate_draft_train_py`, `select_best_draft`. Port these directly.

### Pattern 5: Branch-on-Stagnation
**What:** After N consecutive reverts (N=3 per requirements), create a new git branch from the best-ever commit and try a fundamentally different approach.
**When to use:** Triggered by `SessionState.consecutive_reverts >= 3`.
**Example:**
```python
def trigger_stagnation_branch(
    git_manager: GitManager,
    state: SessionState,
    new_family: str,
) -> str:
    """Branch from best-ever commit for exploration."""
    branch_name = f"explore-{new_family}"
    # Checkout best commit, create branch
    git_manager.repo.git.checkout(state.best_commit)
    git_manager.repo.create_head(branch_name).checkout()
    state.consecutive_reverts = 0  # Reset counter
    return branch_name
```

### Pattern 6: Diagnostics Engine (Generalized from Forecasting)
**What:** Analyze prediction errors to tell the agent WHERE the model fails. Reports worst predictions, bias direction, feature importance/correlations.
**When to use:** After every evaluation, results are included in journal and CLAUDE.md context.
**Key insight:** The old `forecast.diagnose()` does: worst_periods, bias, error_growth_correlation, seasonal_pattern. For tabular, adapt to: worst_samples, bias_direction, feature_correlations (correlation between feature values and prediction error).

### Anti-Patterns to Avoid
- **Coupling plugin to engine:** The TabularPlugin should NOT import from the run engine or CLI. It provides scaffold + template context + config validation only.
- **Heavy ML deps at import time:** Guard imports of sklearn, xgboost, lightgbm behind the plugin so `mlforge` core can be imported without ML libraries.
- **Modifying SessionState schema without migration:** The checkpoint schema_version pattern from Phase 1 must be maintained.
- **Hardcoding metric direction:** Always use `config.direction` -- some metrics maximize, others minimize.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Baseline models | Custom mean/mode predictors | `sklearn.dummy.DummyClassifier/DummyRegressor` | Handles stratified, most_frequent, mean, median strategies correctly |
| Cross-validation | Manual fold splitting | `sklearn.model_selection.cross_val_score` with `StratifiedKFold`/`KFold` | Handles stratification, shuffling, scoring correctly |
| Preprocessing | Custom imputation/encoding | `sklearn.compose.ColumnTransformer` + `Pipeline` | Handles column type detection, fit/transform separation |
| Parquet reading | Custom binary parser | `pandas.read_parquet` with pyarrow | Handles all Parquet versions, compression codecs |
| Hyperparameter search | Grid search loops | Optuna with `study.optimize()` | Bayesian optimization, pruning, distributed support |
| Correlation analysis | Manual Pearson computation | `numpy.corrcoef` | Numerically stable, handles edge cases |
| Feature importance | Custom permutation code | `sklearn.inspection.permutation_importance` | Handles scoring, cross-validation, random state |

**Key insight:** The ML toolchain (sklearn, xgboost, lightgbm, optuna) is mature and battle-tested. Every "simple" ML utility has edge cases that the libraries handle. The plugin's value is in orchestration, not reimplementation.

## Common Pitfalls

### Pitfall 1: Import-Time ML Dependencies
**What goes wrong:** Importing `mlforge` fails if sklearn/xgboost/lightgbm are not installed, even when the user only wants the core engine.
**Why it happens:** Plugin modules import ML libraries at the top level.
**How to avoid:** Lazy imports inside TabularPlugin methods, or guard with try/except at the plugin module level. The plugin registry only loads plugins when they are explicitly registered.
**Warning signs:** `ImportError` when running `mlforge --help` without ML deps installed.

### Pitfall 2: Metric Direction Confusion
**What goes wrong:** The dual-baseline gate or keep/revert logic uses wrong comparison direction (> vs <).
**Why it happens:** Some metrics maximize (accuracy, r2), others minimize (rmse, mae, mape). The old codebase uses sklearn's convention where all scoring strings produce "higher is better" values (e.g., `neg_root_mean_squared_error`).
**How to avoid:** Use sklearn scoring strings consistently. Store `direction` in config and baselines. The gate function must accept `direction` parameter.
**Warning signs:** Good models being reverted, bad models being kept.

### Pitfall 3: Stagnation Counter Reset
**What goes wrong:** `consecutive_reverts` is not reset after a keep, or is not reset after branching.
**Why it happens:** Multiple code paths (keep, revert, branch, crash) each need to update the counter correctly.
**How to avoid:** Centralize counter updates in a single function. Keep resets to zero, revert increments, branch resets to zero.
**Warning signs:** Premature stagnation branching, or never-triggering stagnation.

### Pitfall 4: Multi-Draft Select with Wrong Direction
**What goes wrong:** `select_best_draft` always picks max, but for minimize metrics (rmse, mae) the best is the minimum.
**Why it happens:** The old `drafts.py` always uses `max()` because the old codebase normalizes all metrics to "higher is better" via sklearn neg_ convention.
**How to avoid:** Either continue using sklearn neg_ convention (simplest), or pass `direction` to `select_best_draft`. The old codebase's approach of using sklearn scoring strings is simpler.
**Warning signs:** Worst draft selected as starting point for minimize metrics.

### Pitfall 5: Parquet vs CSV Detection
**What goes wrong:** `load_data` is called with a Parquet file but tries `pd.read_csv()`.
**Why it happens:** File extension not checked.
**How to avoid:** Check file suffix: `.parquet` or `.pq` uses `pd.read_parquet()`, otherwise `pd.read_csv()`.
**Warning signs:** `ParserError` on Parquet files.

### Pitfall 6: Diagnostics on Classification vs Regression
**What goes wrong:** Diagnostics designed for regression (worst predictions, bias magnitude) produce meaningless results for classification.
**Why it happens:** Classification predictions are class labels or probabilities, not continuous values.
**How to avoid:** Different diagnostic strategies per task type. Classification: confusion matrix, per-class accuracy, most confused class pairs. Regression: worst predictions, bias direction, error-magnitude correlation.
**Warning signs:** Diagnostics showing "bias magnitude: 0.02" for a classification task (meaningless).

## Code Examples

### Tabular Plugin Class
```python
# Source: Phase 1 DomainPlugin Protocol + old automl reference code
from pathlib import Path
from mlforge.config import Config
from mlforge.plugins import DomainPlugin

class TabularPlugin:
    name: str = "tabular"
    frozen_files: list[str] = ["prepare.py"]

    def scaffold(self, target_dir: Path, config: Config) -> None:
        # 1. Write frozen prepare.py
        prepare_source = Path(__file__).parent / "prepare.py"
        (target_dir / "prepare.py").write_text(prepare_source.read_text())

        # 2. Render mutable train.py from template
        from mlforge.templates import get_template_env
        env = get_template_env()
        template = env.get_template("tabular_train.py.j2")
        train_content = template.render(
            csv_path=config.plugin_settings.get("csv_path", "data.csv"),
            target_column=config.plugin_settings.get("target_column", "target"),
            metric=config.metric,
            time_budget=config.plugin_settings.get("time_budget", 60),
        )
        (target_dir / "train.py").write_text(train_content)

    def template_context(self, config: Config) -> dict:
        task = config.plugin_settings.get("task", "classification")
        rules = [
            "Use scikit-learn compatible estimators (sklearn, xgboost, lightgbm)",
            "Do not modify prepare.py -- it is frozen infrastructure",
            "train.py is the ONLY mutable file -- all experiments go here",
            "Must beat BOTH baselines before keeping an experiment",
            "Commit before running -- enables clean revert on failure",
            "ALWAYS redirect output to run.log: > run.log 2>&1",
            "Read experiments.md before each iteration for accumulated knowledge",
        ]
        if task == "classification":
            rules.append("Use StratifiedKFold for cross-validation to handle class imbalance")
        else:
            rules.append("Use KFold for cross-validation (regression does not need stratification)")

        return {"domain_rules": rules, "extra_sections": []}

    def validate_config(self, config: Config) -> list[str]:
        errors = []
        valid_metrics = {"accuracy", "auc", "roc_auc", "f1", "f1_weighted",
                         "precision", "recall", "log_loss", "rmse", "mae", "r2", "mse"}
        if config.metric not in valid_metrics:
            errors.append(f"Unknown tabular metric: {config.metric}. Valid: {sorted(valid_metrics)}")
        return errors

# Verify protocol conformance
assert isinstance(TabularPlugin(), DomainPlugin)
```

### Baseline Computation
```python
# Source: old automl.prepare.get_baselines adapted for mlforge
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold

def compute_baselines(X, y, scoring: str, task: str) -> dict[str, dict[str, float]]:
    if task == "classification":
        strategies = {
            "most_frequent": DummyClassifier(strategy="most_frequent"),
            "stratified": DummyClassifier(strategy="stratified", random_state=42),
        }
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    else:
        strategies = {
            "mean": DummyRegressor(strategy="mean"),
            "median": DummyRegressor(strategy="median"),
        }
        cv = KFold(n_splits=5, shuffle=True, random_state=42)

    baselines = {}
    for name, model in strategies.items():
        scores = cross_val_score(model, X, y, scoring=scoring, cv=cv)
        baselines[name] = {"score": float(scores.mean()), "std": float(scores.std())}
    return baselines
```

### Diagnostics (Regression)
```python
# Source: old automl.forecast.diagnose() generalized for tabular
import numpy as np

def diagnose_regression(y_true, y_pred, feature_names=None, X=None, top_n=5):
    error = y_pred - y_true
    abs_error = np.abs(error)

    # Worst predictions
    sorted_idx = np.argsort(abs_error)[::-1][:top_n]
    worst = [{"index": int(i), "y_true": float(y_true[i]),
              "y_pred": float(y_pred[i]), "abs_error": float(abs_error[i])}
             for i in sorted_idx]

    # Bias direction
    mean_error = float(np.mean(error))
    bias = {"direction": "over" if mean_error > 0 else "under" if mean_error < 0 else "neutral",
            "magnitude": mean_error}

    # Feature-error correlation (if features provided)
    correlations = {}
    if X is not None and feature_names is not None:
        for j, fname in enumerate(feature_names):
            if np.std(X[:, j]) > 0 and np.std(abs_error) > 0:
                correlations[fname] = float(np.corrcoef(X[:, j], abs_error)[0, 1])

    return {"worst_predictions": worst, "bias": bias, "feature_error_correlations": correlations}
```

### Multi-Draft Selection
```python
# Source: old automl.drafts (direct port)
from dataclasses import dataclass

@dataclass
class DraftResult:
    name: str
    metric_value: float | None
    status: str  # "draft-keep" | "draft-discard"
    commit_hash: str
    description: str

def select_best_draft(results: list[DraftResult], direction: str = "maximize") -> DraftResult | None:
    valid = [r for r in results if r.metric_value is not None]
    if not valid:
        return None
    if direction == "maximize":
        return max(valid, key=lambda r: r.metric_value)
    else:
        return min(valid, key=lambda r: r.metric_value)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `automl.prepare` monolith | `mlforge.tabular` package with plugin protocol | Phase 2 (now) | Clean separation of domain from engine |
| Free-form CLAUDE.md text | Jinja2 template with plugin-injected context | Phase 1 | Consistent, testable protocol generation |
| `loop_helpers.LoopState` | `SessionState` + intelligence modules | Phase 1-2 | JSON persistence, crash recovery |
| Manual baseline comparison | Programmatic dual-baseline gate | Phase 2 (now) | Reliable rejection of below-baseline experiments |
| Forecast-only diagnostics | Task-aware diagnostics (classification + regression) | Phase 2 (now) | Diagnostics work for all tabular tasks |

**Deprecated/outdated:**
- Old `automl.loop_helpers.LoopState`: Replaced by `mlforge.state.SessionState` + intelligence modules
- Old `automl.drafts`: Being ported to `mlforge.intelligence.drafts`
- Old `automl.prepare`: Being ported to `mlforge.tabular.prepare`

## Open Questions

1. **Parquet dependency weight**
   - What we know: `pd.read_parquet()` requires pyarrow (or fastparquet). pyarrow is ~200MB installed.
   - What's unclear: Whether to make pyarrow a required dependency or optional extra.
   - Recommendation: Make it a required dependency. Parquet is standard in ML workflows, and the size tradeoff is acceptable for an ML tool that already requires sklearn/xgboost/lightgbm.

2. **Optuna in train.py template vs protocol instruction**
   - What we know: TABL-02 requires Optuna support. The old codebase had Optuna in `train_template_forecast.py`.
   - What's unclear: Should the initial train.py template include Optuna boilerplate, or should the CLAUDE.md protocol instruct the agent to add it?
   - Recommendation: Include minimal Optuna boilerplate in the train.py template (study creation, objective function skeleton). The agent can then modify the search space. This matches the old v2.0 pattern.

3. **Classification diagnostics scope**
   - What we know: INTL-03 says "worst predictions, bias direction, feature correlations." Regression diagnostics are straightforward. Classification is more nuanced.
   - What's unclear: What constitutes "worst predictions" for classification -- highest confidence wrong predictions? Most confused class pairs?
   - Recommendation: For classification, report: most misclassified samples (highest predicted probability for wrong class), per-class accuracy breakdown, and most confused class pairs. Keep it simple.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `python3 -m pytest tests/mlforge/ -x -q` |
| Full suite command | `python3 -m pytest tests/mlforge/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TABL-01 | TabularPlugin handles CSV/Parquet classification + regression | unit | `python3 -m pytest tests/mlforge/test_tabular.py -x` | No -- Wave 0 |
| TABL-02 | Plugin supports sklearn/XGBoost/LightGBM families | unit | `python3 -m pytest tests/mlforge/test_tabular.py::test_algorithm_families -x` | No -- Wave 0 |
| TABL-03 | Leakage prevention: shift-first, walk-forward CV | unit | `python3 -m pytest tests/mlforge/test_tabular.py::test_temporal_validation -x` | No -- Wave 0 |
| TABL-04 | Plugin generates CLAUDE.md with tabular rules | unit | `python3 -m pytest tests/mlforge/test_tabular.py::test_template_context -x` | No -- Wave 0 |
| TABL-05 | Frozen prepare.py + mutable train.py scaffold | unit | `python3 -m pytest tests/mlforge/test_tabular.py::test_scaffold -x` | No -- Wave 0 |
| INTL-01 | Baselines: naive + domain-specific | unit | `python3 -m pytest tests/mlforge/test_baselines.py -x` | No -- Wave 0 |
| INTL-02 | Dual-baseline gate rejects below-baseline | unit | `python3 -m pytest tests/mlforge/test_baselines.py::test_gate -x` | No -- Wave 0 |
| INTL-03 | Diagnostics: worst, bias, correlations | unit | `python3 -m pytest tests/mlforge/test_diagnostics.py -x` | No -- Wave 0 |
| INTL-04 | Branch-on-stagnation after 3 reverts | unit | `python3 -m pytest tests/mlforge/test_stagnation.py -x` | No -- Wave 0 |
| INTL-05 | Multi-draft: 3-5 solutions, pick best | unit | `python3 -m pytest tests/mlforge/test_drafts.py -x` | No -- Wave 0 |
| INTL-06 | Diff-aware: git diff in journal | unit | `python3 -m pytest tests/mlforge/test_journal.py -x` | Partial -- existing tests cover basic JSONL |
| INTL-08 | Results tracking with commit, metric, status | unit | `python3 -m pytest tests/mlforge/test_journal.py -x` | Partial -- existing tests cover basic entries |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/mlforge/ -x -q`
- **Per wave merge:** `python3 -m pytest tests/mlforge/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/mlforge/test_tabular.py` -- covers TABL-01 through TABL-05
- [ ] `tests/mlforge/test_baselines.py` -- covers INTL-01, INTL-02
- [ ] `tests/mlforge/test_diagnostics.py` -- covers INTL-03
- [ ] `tests/mlforge/test_stagnation.py` -- covers INTL-04
- [ ] `tests/mlforge/test_drafts.py` -- covers INTL-05
- [ ] ML dependencies: `pip install scikit-learn pandas numpy xgboost lightgbm optuna pyarrow`

## Sources

### Primary (HIGH confidence)
- Phase 1 source code: `src/mlforge/plugins.py`, `state.py`, `config.py`, `git_ops.py`, `journal.py`, `templates/`, `hooks.py` -- direct inspection of existing interfaces
- Old v1-v3 reference code: `src/automl/prepare.py`, `drafts.py`, `forecast.py`, `loop_helpers.py`, `scaffold.py`, `train_template.py` -- proven patterns to port
- Phase 1 test suite: `tests/mlforge/` (64 tests, all passing) -- established testing patterns

### Secondary (MEDIUM confidence)
- scikit-learn documentation for `DummyClassifier`/`DummyRegressor`, `cross_val_score`, `ColumnTransformer` -- well-known APIs
- Optuna documentation for `study.optimize()` pattern -- established library

### Tertiary (LOW confidence)
- None -- all patterns are either in the existing codebase or well-established ML library APIs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries are from the existing v1-v3 codebase, well-established
- Architecture: HIGH -- plugin protocol is proven in Phase 1, tabular patterns are proven in old codebase
- Pitfalls: HIGH -- identified from actual issues encountered in v1-v3 development
- Diagnostics generalization: MEDIUM -- classification diagnostics are new (not in old forecasting code)

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable domain, all patterns are proven)
