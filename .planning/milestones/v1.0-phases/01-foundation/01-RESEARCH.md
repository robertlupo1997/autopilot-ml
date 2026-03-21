# Phase 1: Foundation - Research

**Researched:** 2026-03-09
**Domain:** Frozen data pipeline, mutable modeling template, git state management, experiment logging
**Confidence:** HIGH

## Summary

Phase 1 builds the entire foundation for the AutoML framework: a frozen data pipeline (data loading, splitting, evaluation, preprocessing, baselines), a mutable train.py template, git-based experiment state management, and TSV-based experiment logging. This is modeled directly on Karpathy's autoresearch pattern but adapted from GPU/LLM pretraining to CPU/tabular ML.

The core architectural insight from autoresearch is the separation of concerns: `prepare.py` is frozen (the agent cannot modify it) and contains data loading, splitting, evaluation, and preprocessing. `train.py` is the only mutable file -- it imports from prepare.py and contains model selection, hyperparameters, and training logic. Git provides atomic state management: commit on improvement, reset --hard on failure.

**Primary recommendation:** Build prepare.py as the frozen layer (data loading, train/test split, cross-validated evaluation, preprocessing, baselines, data summary) and train.py as the mutable template that imports from it. Use subprocess for all git operations. Keep everything in pure Python with scikit-learn, pandas, and numpy -- no custom frameworks.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PIPE-01 | Framework accepts any CSV file + target column + evaluation metric | pandas read_csv with type inference; metric name validated against sklearn.metrics |
| PIPE-02 | Data split: time-based if temporal, stratified if classification | sklearn train_test_split with stratify param; TimeSeriesSplit for temporal |
| PIPE-03 | Evaluation via cross-validation with configurable metric | sklearn cross_val_score with scoring parameter; StratifiedKFold auto-selected for classifiers |
| PIPE-04 | Sanity-check baselines (majority class, mean predictor, random) | sklearn DummyClassifier (strategy="most_frequent") and DummyRegressor (strategy="mean") |
| PIPE-05 | Hidden holdout set reserved, agent never sees | Split data into train+val / holdout before anything else; holdout saved separately |
| PIPE-06 | Basic preprocessing (missing values, categorical encoding, type inference) | SimpleImputer + OrdinalEncoder for tree models; pandas dtype inference |
| PIPE-07 | Data preview/summary for agent context | pandas describe(), dtypes, isnull().sum(), shape; correlations with target |
| MODEL-01 | Agent edits single train.py with model selection/hyperparameters | Mutable file pattern from autoresearch; imports frozen functions from prepare.py |
| MODEL-02 | train.py template provides baseline model | LogisticRegression for classification, Ridge for regression as sensible defaults |
| MODEL-03 | train.py imports frozen evaluation and data from prepare.py | Python import pattern: `from prepare import load_data, evaluate, get_baselines` |
| MODEL-04 | train.py prints structured metric output | Key-value format: `metric_name: value\ndirection: maximize` parseable by grep |
| MODEL-05 | Configurable time budget per experiment (default ~60s) | signal.alarm() for Unix timeout or subprocess.run(timeout=) |
| GIT-01 | Each run operates on dedicated branch | `git checkout -b automl/run-<tag>` via subprocess |
| GIT-02 | Successful experiments committed with descriptive messages | `git add train.py && git commit -m "description"` via subprocess |
| GIT-03 | Failed experiments reset to last good commit | `git reset --hard HEAD` via subprocess |
| GIT-04 | results.tsv untracked by git | Add `results.tsv` to .gitignore |
| GIT-05 | Git operations use subprocess + CLI (not GitPython) | subprocess.run(["git", ...], capture_output=True, text=True) |
| LOG-01 | results.tsv tracks commit hash, metric, memory/time, status, description | TSV with header row, append-only |
| LOG-02 | results.tsv is tab-separated and append-only | open("results.tsv", "a") with tab-separated fields |
| LOG-03 | Each experiment's full output captured in run.log | subprocess stdout/stderr redirect to run.log |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | 1.8.x | ML models, cross-validation, metrics, preprocessing, dummy baselines | Industry standard for tabular ML; auto-stratification in cross_val_score |
| pandas | 2.x | CSV loading, type inference, data summary | De facto standard for tabular data |
| numpy | 2.x | Numerical operations | Required by sklearn and pandas |
| xgboost | latest | Gradient boosted trees (used in train.py template) | Best default for tabular ML |
| lightgbm | latest | Alternative gradient boosting (for multi-draft phase) | Fast, memory-efficient alternative to XGBoost |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| signal (stdlib) | - | Timeout enforcement for experiments | Unix-only; MODEL-05 time budget |
| subprocess (stdlib) | - | Git CLI operations | All GIT-* requirements |
| csv (stdlib) | - | TSV reading/writing | LOG-01, LOG-02 results.tsv |
| json (stdlib) | - | Config file handling | Storing experiment config |
| time (stdlib) | - | Timing experiments | LOG-01 memory/time tracking |
| tracemalloc (stdlib) | - | Memory tracking | LOG-01 memory measurement |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| OrdinalEncoder | OneHotEncoder | OHE better for linear models but explodes dimensionality; OrdinalEncoder works well with tree models which dominate tabular ML |
| signal.alarm() | subprocess timeout | signal.alarm is in-process and simpler for self-imposed limits; subprocess timeout is for external processes |
| GitPython | subprocess git | GitPython has memory leaks, opaque errors -- explicitly out of scope per requirements |

**Installation:**
```bash
uv add scikit-learn pandas numpy xgboost lightgbm
```

## Architecture Patterns

### Recommended Project Structure
```
<experiment_dir>/
    prepare.py       # FROZEN: data loading, splitting, evaluation, preprocessing, baselines, summary
    train.py         # MUTABLE: model selection, hyperparameters, training logic
    program.md       # Human domain expertise (Phase 2)
    CLAUDE.md        # Agent loop instructions (Phase 2)
    results.tsv      # Experiment log (untracked by git)
    run.log          # Last experiment output (overwritten each run)
    .gitignore       # Excludes results.tsv, run.log, __pycache__, etc.
    pyproject.toml   # uv project with dependencies
```

### Pattern 1: Frozen/Mutable Separation
**What:** prepare.py exports functions that train.py imports. The agent modifies only train.py.
**When to use:** Always -- this is the core architectural pattern.
**Example:**
```python
# prepare.py (FROZEN -- agent cannot modify)
import pandas as pd
import numpy as np
from sklearn.model_selection import cross_val_score, StratifiedKFold, train_test_split
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.preprocessing import OrdinalEncoder
from sklearn.impute import SimpleImputer

def load_data(csv_path, target_column):
    """Load CSV, split into features/target, return with metadata."""
    df = pd.read_csv(csv_path)
    y = df[target_column]
    X = df.drop(columns=[target_column])
    # Infer task type
    task = "classification" if y.dtype == "object" or y.nunique() <= 20 else "regression"
    return X, y, task

def preprocess(X_train, X_test=None):
    """Handle missing values and encode categoricals. Returns numpy arrays."""
    # Identify column types
    cat_cols = X_train.select_dtypes(include=["object", "category"]).columns
    num_cols = X_train.select_dtypes(include=["number"]).columns
    # ... imputation and encoding ...
    return X_train_processed, X_test_processed, preprocessor

def evaluate(model, X, y, metric, task, cv=5):
    """Cross-validated evaluation with the configured metric."""
    score = cross_val_score(model, X, y, scoring=metric, cv=cv)
    return score.mean(), score.std()

def get_baselines(X, y, metric, task):
    """Compute sanity-check baselines."""
    baselines = {}
    if task == "classification":
        for strategy in ["most_frequent", "stratified"]:
            dummy = DummyClassifier(strategy=strategy)
            score, std = evaluate(dummy, X, y, metric, task)
            baselines[strategy] = {"score": score, "std": std}
    else:
        for strategy in ["mean", "median"]:
            dummy = DummyRegressor(strategy=strategy)
            score, std = evaluate(dummy, X, y, metric, task)
            baselines[strategy] = {"score": score, "std": std}
    return baselines

def get_data_summary(X, y, task):
    """Generate data preview for agent context."""
    summary = {
        "shape": X.shape,
        "dtypes": X.dtypes.value_counts().to_dict(),
        "missing": X.isnull().sum().sum(),
        "target_distribution": y.value_counts().to_dict() if task == "classification" else {
            "mean": y.mean(), "std": y.std(), "min": y.min(), "max": y.max()
        }
    }
    return summary
```

```python
# train.py (MUTABLE -- agent modifies this)
"""
AutoML experiment script. Modify this file to try different models and hyperparameters.
Usage: uv run train.py
"""
import time
import signal
from prepare import load_data, preprocess, evaluate

# --- Configuration (edit these) ---
CSV_PATH = "data.csv"
TARGET_COLUMN = "target"
METRIC = "roc_auc"       # sklearn scoring string
TIME_BUDGET = 60          # seconds

# --- Timeout enforcement ---
def timeout_handler(signum, frame):
    raise TimeoutError(f"Experiment exceeded {TIME_BUDGET}s time budget")
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(TIME_BUDGET)

t_start = time.time()

# --- Load and preprocess ---
X, y, task = load_data(CSV_PATH, TARGET_COLUMN)
X_processed, _, preprocessor = preprocess(X)

# --- Model (edit this section) ---
from sklearn.linear_model import LogisticRegression
model = LogisticRegression(max_iter=1000)

# --- Evaluate ---
score_mean, score_std = evaluate(model, X_processed, y, METRIC, task)

# --- Print structured output ---
elapsed = time.time() - t_start
print("---")
print(f"metric_name:  {METRIC}")
print(f"metric_value: {score_mean:.6f}")
print(f"metric_std:   {score_std:.6f}")
print(f"direction:    maximize")
print(f"elapsed_sec:  {elapsed:.1f}")
print(f"model:        {type(model).__name__}")
```

### Pattern 2: Structured Metric Output (Autoresearch Pattern)
**What:** train.py prints key-value pairs after `---` separator, extractable by grep.
**When to use:** Every experiment output.
**Example:**
```bash
# Agent extracts metric:
grep "^metric_value:" run.log | awk '{print $2}'
```
This mirrors autoresearch's `grep "^val_bpb:" run.log` pattern exactly.

### Pattern 3: Git State Management via Subprocess
**What:** All git operations through subprocess.run() with capture_output.
**When to use:** All GIT-* requirements.
**Example:**
```python
import subprocess

def git_run(*args, check=True):
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, check=check
    )
    return result.stdout.strip()

def create_run_branch(tag):
    """Create and checkout a new experiment branch."""
    branch = f"automl/run-{tag}"
    git_run("checkout", "-b", branch)
    return branch

def commit_experiment(message):
    """Commit current state of train.py."""
    git_run("add", "train.py")
    commit_hash = git_run("rev-parse", "--short", "HEAD")
    git_run("commit", "-m", message)
    return git_run("rev-parse", "--short", "HEAD")

def revert_experiment():
    """Reset to the last good commit."""
    git_run("reset", "--hard", "HEAD")
    # Also clean any untracked files the experiment may have created
    git_run("clean", "-fd", "--", ".")
```

### Pattern 4: TSV Append-Only Logging
**What:** results.tsv is tab-separated, append-only, untracked by git.
**When to use:** After every experiment.
**Example:**
```python
import os

RESULTS_FILE = "results.tsv"
HEADER = "commit\tmetric_value\tmemory_mb\telapsed_sec\tstatus\tdescription\n"

def init_results():
    """Create results.tsv with header if it doesn't exist."""
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "w") as f:
            f.write(HEADER)

def log_result(commit, metric_value, memory_mb, elapsed_sec, status, description):
    """Append one experiment result."""
    with open(RESULTS_FILE, "a") as f:
        f.write(f"{commit}\t{metric_value:.6f}\t{memory_mb:.1f}\t{elapsed_sec:.1f}\t{status}\t{description}\n")
```

### Anti-Patterns to Avoid
- **Modifying prepare.py from train.py:** The frozen/mutable boundary must be enforced. train.py imports from prepare.py but never writes to it.
- **Using GitPython:** Explicitly out of scope. Memory leaks, opaque errors. subprocess is simpler and more reliable.
- **Committing results.tsv:** It must be in .gitignore. Git tracks code changes; results.tsv is the experiment log that persists across git resets.
- **Flooding stdout:** All experiment output goes to run.log. The agent reads results via grep, not by consuming the full output.
- **Using OneHotEncoder as default:** For a framework targeting tree-based models (XGBoost, LightGBM, RandomForest), OrdinalEncoder is the correct default. OneHotEncoder creates unnecessary dimensionality expansion.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-validation | Manual fold splitting | sklearn.model_selection.cross_val_score | Handles stratification, scoring, parallelism automatically |
| Baseline models | Manual majority-class calculation | sklearn.dummy.DummyClassifier/DummyRegressor | Correct handling of all strategies, works with any sklearn metric |
| Missing value imputation | Manual fillna logic | sklearn.impute.SimpleImputer | Consistent fit/transform API, handles unseen data correctly |
| Categorical encoding | Manual label mapping | sklearn.preprocessing.OrdinalEncoder | Handles unseen categories, consistent API, invertible |
| Metric computation | Manual metric formulas | sklearn.metrics (via scoring parameter) | Correct implementations, handles edge cases (multiclass AUC, etc.) |
| Train/test splitting | Manual index slicing | sklearn.model_selection.train_test_split | Stratification, reproducibility via random_state |
| Data type inference | Manual column-by-column checks | pandas dtypes + select_dtypes() | Handles mixed types, datetime detection |

**Key insight:** scikit-learn's API is designed exactly for this use case. Every preprocessing, splitting, evaluation, and baseline computation has a battle-tested implementation. The framework's value is in orchestrating these tools, not reimplementing them.

## Common Pitfalls

### Pitfall 1: Data Leakage in Preprocessing
**What goes wrong:** Fitting the preprocessor (imputer, encoder) on the full dataset including test/holdout data.
**Why it happens:** It's easy to call fit_transform() on the entire DataFrame before splitting.
**How to avoid:** Always split first, then fit preprocessor on training data only, then transform test/holdout. Use sklearn Pipeline to enforce this.
**Warning signs:** Suspiciously high test scores, perfect or near-perfect holdout performance.

### Pitfall 2: Metric Direction Confusion
**What goes wrong:** Treating a "higher is better" metric as "lower is better" or vice versa. The agent keeps a worse model.
**Why it happens:** Some metrics (RMSE, MAE) are better when lower; others (AUC, accuracy, F1) are better when higher. sklearn scoring strings use the convention that higher is always better (e.g., `neg_mean_squared_error`).
**How to avoid:** Use sklearn's scoring parameter directly -- it always returns values where higher = better (negative for error metrics). Store the direction alongside the metric name.
**Warning signs:** Agent consistently "improves" but holdout gets worse.

### Pitfall 3: Git Reset Deleting Untracked Files
**What goes wrong:** `git reset --hard` only resets tracked files. If train.py created new files, they persist.
**Why it happens:** Misunderstanding git reset vs git clean.
**How to avoid:** After `git reset --hard HEAD`, also run `git checkout -- .` to restore tracked files, but be careful not to delete results.tsv (which is untracked and in .gitignore).
**Warning signs:** Stale artifacts from failed experiments interfering with subsequent runs.

### Pitfall 4: Cross-Validation Metric Mismatch
**What goes wrong:** Using a metric string that doesn't match the task type (e.g., "roc_auc" on multiclass without specifying multi_class parameter).
**Why it happens:** sklearn metrics have different requirements for binary vs multiclass vs regression.
**How to avoid:** Validate the metric against the detected task type. Map user-facing metric names to correct sklearn scoring strings (e.g., "auc" -> "roc_auc" for binary, "roc_auc_ovr" for multiclass).
**Warning signs:** ValueError from cross_val_score about metric incompatibility.

### Pitfall 5: Task Type Auto-Detection Failures
**What goes wrong:** Integer-encoded classification targets (0, 1, 2, ...) detected as regression.
**Why it happens:** Numeric dtype with potentially many unique values looks like regression.
**How to avoid:** Use a heuristic: if y is integer-typed AND has fewer than N unique values (e.g., 20), treat as classification. Allow user override via config.
**Warning signs:** Regression metrics applied to a classification problem, poor baselines.

### Pitfall 6: Holdout Set Contamination
**What goes wrong:** The holdout set is accidentally used during cross-validation or preprocessing.
**Why it happens:** Holdout is split but then the full dataset is passed to cross_val_score.
**How to avoid:** Split holdout FIRST, save it to a separate file or variable. All subsequent operations (preprocessing, CV, baselines) use only the remaining data.
**Warning signs:** Final holdout score suspiciously close to CV score.

## Code Examples

### Complete Preprocessing Pipeline
```python
# Source: sklearn best practices for tabular ML
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OrdinalEncoder, StandardScaler

def build_preprocessor(X):
    """Build a preprocessor that handles mixed column types."""
    cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
    num_cols = X.select_dtypes(include=["number"]).columns.tolist()

    num_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
    ])

    cat_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
    ])

    preprocessor = ColumnTransformer([
        ("num", num_pipeline, num_cols),
        ("cat", cat_pipeline, cat_cols),
    ], remainder="drop")

    return preprocessor
```

### Holdout Split Pattern
```python
# Source: autoresearch pattern adapted for tabular ML
from sklearn.model_selection import train_test_split

def split_data(X, y, task, holdout_fraction=0.15, random_state=42):
    """Split into working set (for CV) and holdout (for final validation)."""
    stratify = y if task == "classification" else None
    X_work, X_holdout, y_work, y_holdout = train_test_split(
        X, y, test_size=holdout_fraction, random_state=random_state, stratify=stratify
    )
    return X_work, X_holdout, y_work, y_holdout
```

### Metric Validation
```python
# Source: sklearn scoring parameter documentation
METRIC_MAP = {
    # Classification
    "accuracy": ("accuracy", "maximize"),
    "auc": ("roc_auc", "maximize"),
    "roc_auc": ("roc_auc", "maximize"),
    "f1": ("f1", "maximize"),
    "f1_weighted": ("f1_weighted", "maximize"),
    "precision": ("precision", "maximize"),
    "recall": ("recall", "maximize"),
    "log_loss": ("neg_log_loss", "maximize"),  # sklearn negates
    # Regression
    "rmse": ("neg_root_mean_squared_error", "maximize"),  # sklearn negates
    "mae": ("neg_mean_absolute_error", "maximize"),  # sklearn negates
    "r2": ("r2", "maximize"),
    "mse": ("neg_mean_squared_error", "maximize"),  # sklearn negates
}

def validate_metric(metric_name, task):
    """Validate and map user metric to sklearn scoring string."""
    if metric_name not in METRIC_MAP:
        raise ValueError(f"Unknown metric: {metric_name}. Valid: {list(METRIC_MAP.keys())}")
    sklearn_scoring, direction = METRIC_MAP[metric_name]
    # Validate task compatibility
    classification_metrics = {"accuracy", "auc", "roc_auc", "f1", "f1_weighted", "precision", "recall", "log_loss"}
    regression_metrics = {"rmse", "mae", "r2", "mse"}
    if task == "classification" and metric_name in regression_metrics:
        raise ValueError(f"Metric '{metric_name}' is not valid for classification tasks")
    if task == "regression" and metric_name in classification_metrics:
        raise ValueError(f"Metric '{metric_name}' is not valid for regression tasks")
    return sklearn_scoring, direction
```

### Git Operations Module
```python
# Source: autoresearch program.md git patterns
import subprocess
import os

class GitManager:
    """Manages git operations for experiment tracking via subprocess."""

    def __init__(self, repo_dir="."):
        self.repo_dir = repo_dir

    def _run(self, *args, check=True):
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, check=check,
            cwd=self.repo_dir
        )
        return result

    def init_repo(self):
        """Initialize git repo if not already initialized."""
        if not os.path.exists(os.path.join(self.repo_dir, ".git")):
            self._run("init")

    def create_branch(self, tag):
        """Create and switch to experiment branch."""
        branch = f"automl/run-{tag}"
        self._run("checkout", "-b", branch)
        return branch

    def commit(self, message, files=None):
        """Stage and commit specified files (default: train.py)."""
        files = files or ["train.py"]
        for f in files:
            self._run("add", f)
        self._run("commit", "-m", message)
        result = self._run("rev-parse", "--short", "HEAD")
        return result.stdout.strip()

    def revert(self):
        """Reset to last committed state."""
        self._run("reset", "--hard", "HEAD")

    def get_current_commit(self):
        """Get short hash of current HEAD."""
        result = self._run("rev-parse", "--short", "HEAD")
        return result.stdout.strip()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LabelEncoder for features | OrdinalEncoder for features | sklearn ~1.0+ | LabelEncoder is only for target encoding; OrdinalEncoder handles multi-column features correctly |
| Manual cross-validation loops | cross_val_score with auto-stratification | sklearn stable | Automatic StratifiedKFold for classifiers when passing cv=int |
| GridSearchCV for everything | cross_val_score for evaluation + manual search | autoresearch pattern | The agent IS the search algorithm; CV is just for evaluation |
| GitPython | subprocess + git CLI | project decision | Simpler, no memory leaks, explicit error handling |
| sklearn 1.5 | sklearn 1.8.0 (Dec 2025) | Dec 2025 | Array API support, temperature calibration, performance improvements |

**Deprecated/outdated:**
- LabelEncoder for features: Use OrdinalEncoder instead (LabelEncoder is for target labels only)
- Manual stratification: cross_val_score auto-stratifies for classifiers
- sklearn < 1.8: Current stable is 1.8.0, requires Python 3.11+

## Open Questions

1. **Time-series detection heuristic**
   - What we know: PIPE-02 says "time-based if temporal" but doesn't specify how to detect temporal data
   - What's unclear: Should the framework auto-detect datetime columns? Or require user flag?
   - Recommendation: For v1, accept an optional `temporal=True` flag. Auto-detection is fragile and can be added in v2.

2. **Holdout set storage**
   - What we know: PIPE-05 says holdout must be reserved and agent never sees it
   - What's unclear: Should holdout be saved to disk (separate file) or kept in memory within prepare.py?
   - Recommendation: Save holdout indices or data to a separate file that train.py does not import. Evaluate on holdout only as a final step, not during the experiment loop.

3. **Memory tracking granularity**
   - What we know: LOG-01 requires memory tracking per experiment
   - What's unclear: Peak RSS, tracemalloc, or process-level measurement?
   - Recommendation: Use `tracemalloc` for Python memory or `resource.getrusage()` for process-level. For tabular ML, process-level RSS is most meaningful.

4. **Metric direction in results.tsv**
   - What we know: sklearn always returns higher=better via scoring strings. Autoresearch uses raw metric (val_bpb where lower=better).
   - What's unclear: Should results.tsv store the sklearn-convention score or the natural metric value?
   - Recommendation: Store the natural metric value (e.g., actual RMSE, not neg_RMSE) in results.tsv for human readability. Use sklearn convention internally for comparison logic.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest) |
| Config file | none -- Wave 0 |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | Load any CSV with target column and metric | unit | `uv run pytest tests/test_prepare.py::test_load_data -x` | No -- Wave 0 |
| PIPE-02 | Stratified split for classification, time-based for temporal | unit | `uv run pytest tests/test_prepare.py::test_split_data -x` | No -- Wave 0 |
| PIPE-03 | Cross-validated evaluation with configurable metric | unit | `uv run pytest tests/test_prepare.py::test_evaluate -x` | No -- Wave 0 |
| PIPE-04 | Sanity-check baselines computed | unit | `uv run pytest tests/test_prepare.py::test_baselines -x` | No -- Wave 0 |
| PIPE-05 | Hidden holdout set reserved | unit | `uv run pytest tests/test_prepare.py::test_holdout_split -x` | No -- Wave 0 |
| PIPE-06 | Preprocessing handles missing values and categoricals | unit | `uv run pytest tests/test_prepare.py::test_preprocess -x` | No -- Wave 0 |
| PIPE-07 | Data summary generated | unit | `uv run pytest tests/test_prepare.py::test_data_summary -x` | No -- Wave 0 |
| MODEL-01 | train.py is a single editable file | smoke | manual verification | No -- Wave 0 |
| MODEL-02 | Baseline model in template | smoke | `uv run pytest tests/test_train.py::test_template_runs -x` | No -- Wave 0 |
| MODEL-03 | train.py imports from prepare.py | smoke | `uv run pytest tests/test_train.py::test_imports -x` | No -- Wave 0 |
| MODEL-04 | Structured metric output printed | unit | `uv run pytest tests/test_train.py::test_structured_output -x` | No -- Wave 0 |
| MODEL-05 | Time budget enforced | unit | `uv run pytest tests/test_train.py::test_timeout -x` | No -- Wave 0 |
| GIT-01 | Dedicated run branch created | integration | `uv run pytest tests/test_git.py::test_create_branch -x` | No -- Wave 0 |
| GIT-02 | Successful experiment committed | integration | `uv run pytest tests/test_git.py::test_commit -x` | No -- Wave 0 |
| GIT-03 | Failed experiment reverted | integration | `uv run pytest tests/test_git.py::test_revert -x` | No -- Wave 0 |
| GIT-04 | results.tsv in .gitignore | unit | `uv run pytest tests/test_git.py::test_gitignore -x` | No -- Wave 0 |
| GIT-05 | Git via subprocess only | unit | manual verification (no GitPython import) | No -- Wave 0 |
| LOG-01 | results.tsv tracks required fields | unit | `uv run pytest tests/test_logging.py::test_log_fields -x` | No -- Wave 0 |
| LOG-02 | TSV is tab-separated and append-only | unit | `uv run pytest tests/test_logging.py::test_tsv_format -x` | No -- Wave 0 |
| LOG-03 | Full output captured in run.log | integration | `uv run pytest tests/test_logging.py::test_run_log -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` -- shared fixtures (sample CSV, temp git repos)
- [ ] `tests/test_prepare.py` -- covers PIPE-01 through PIPE-07
- [ ] `tests/test_train.py` -- covers MODEL-01 through MODEL-05
- [ ] `tests/test_git.py` -- covers GIT-01 through GIT-05
- [ ] `tests/test_logging.py` -- covers LOG-01 through LOG-03
- [ ] Framework install: `uv add pytest` -- pytest not yet in project
- [ ] Sample test CSV fixture needed for all data tests

## Sources

### Primary (HIGH confidence)
- [scikit-learn 1.8.0 cross-validation docs](https://scikit-learn.org/stable/modules/cross_validation.html) -- stratified CV, cross_val_score API
- [scikit-learn 1.8.0 DummyClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.dummy.DummyClassifier.html) -- baseline strategies
- [scikit-learn 1.8.0 DummyRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.dummy.DummyRegressor.html) -- baseline strategies
- [scikit-learn 1.8.0 OrdinalEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OrdinalEncoder.html) -- handle_unknown parameter
- [Python subprocess docs](https://docs.python.org/3/library/subprocess.html) -- subprocess.run API
- Autoresearch reference code (`/tmp/autoresearch/`) -- prepare.py, train.py, program.md patterns

### Secondary (MEDIUM confidence)
- [scikit-learn 1.8.0 release notes](https://scikit-learn.org/stable/whats_new/v1.8.html) -- version verification, Dec 2025 release
- [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) -- temporal data splitting

### Tertiary (LOW confidence)
- None -- all findings verified against official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- scikit-learn, pandas, numpy are the definitive stack for tabular ML; versions confirmed from PyPI
- Architecture: HIGH -- directly derived from autoresearch reference code which was read in full
- Pitfalls: HIGH -- well-documented sklearn pitfalls, verified against official docs
- Git patterns: HIGH -- subprocess approach is simple and well-documented; explicitly required by project constraints

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable domain, mature libraries)
