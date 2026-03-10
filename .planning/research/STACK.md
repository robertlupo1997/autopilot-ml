# Technology Stack

**Project:** AutoML -- Autonomous ML Research Framework
**Researched:** 2026-03-09
**Primary source:** Training data (cutoff ~May 2025) + PROJECT.md context
**Verification note:** WebSearch/WebFetch/Bash were unavailable during research. Versions reflect best knowledge from training data. Flag items marked LOW confidence for manual verification with `pip index versions <package>` before finalizing `pyproject.toml`.

## Recommended Stack

### Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | >=3.11, <3.13 | Runtime | 3.11 is the sweet spot: fast, stable, broad library support. 3.12 is fine too. Avoid 3.13 -- some ML libraries may lag on support. PROJECT.md specifies 3.11+. | HIGH |
| uv | >=0.4 | Package manager + venv | Follows autoresearch pattern. 10-100x faster than pip. Handles venv creation, lockfiles, and Python version management. Replaces pip, pip-tools, virtualenv, and pyenv in one tool. | HIGH |

### ML Libraries (Core)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| scikit-learn | >=1.5,<2.0 | Base ML framework | Industry standard for tabular ML. Provides RandomForest, LogisticRegression, GradientBoosting, preprocessing, model selection, metrics. v1.5 added improved metadata routing and HistGradientBoosting improvements. Pin below 2.0 to avoid potential breaking API changes. | MEDIUM -- verify latest is 1.5.x or 1.6.x |
| xgboost | >=2.1,<3.0 | Gradient boosting | Best-in-class for tabular data. v2.0+ unified the API and added better categorical support. Typically wins or ties LightGBM on most tabular benchmarks. CPU training is fast enough for this project's scope. | MEDIUM -- verify 2.1.x is latest |
| lightgbm | >=4.5,<5.0 | Gradient boosting | Faster training than XGBoost on large datasets, excellent categorical handling. Complementary to XGBoost -- having both lets the multi-draft approach try each. v4.x modernized the Python API. | MEDIUM -- verify 4.5.x is latest |
| catboost | >=1.2,<2.0 | Gradient boosting (optional) | Strong on categorical-heavy datasets without manual encoding. Include as optional dependency for multi-draft diversity. | LOW -- verify current version |

### Data Handling

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pandas | >=2.2,<3.0 | Data loading + manipulation | Standard for CSV loading and tabular data manipulation. v2.x has better Arrow backend and copy-on-write. Pin below 3.0 for stability. | MEDIUM -- verify 2.2.x is latest |
| numpy | >=1.26,<3.0 | Numerical arrays | Required by all ML libraries. v1.26 is the last 1.x; v2.0 has breaking changes but most libraries now support it. Allow v2.x but ensure compatibility. | MEDIUM -- numpy 2.x compatibility needs testing |

### Git Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| subprocess (stdlib) | N/A | Git operations | **Use subprocess.run() to call git directly, NOT GitPython.** This is critical. Autoresearch calls `git` via shell commands. GitPython adds abstraction that hides failures, has memory leaks with large repos, and adds a dependency for no real benefit when your operations are simple (commit, reset, branch, log). | HIGH |

**Anti-recommendation: GitPython.** Do NOT use it. The operations needed (commit, reset --hard, checkout, branch, log) are simple shell commands. GitPython introduces: (1) memory leaks from unclosed repo objects, (2) opaque error handling, (3) unnecessary abstraction over simple CLI calls, (4) another dependency to maintain. subprocess + git CLI is simpler, more debuggable, and what autoresearch uses.

### Experiment Tracking

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| TSV file (results.tsv) | N/A | Experiment log | Follows autoresearch pattern exactly. Simple append-only TSV with columns: commit_hash, metric_value, status (keep/revert), description, timestamp. No external service needed. Git tracks the file. Grep-able, diff-able, human-readable. | HIGH |
| csv (stdlib) | N/A | TSV reading/writing | Use stdlib csv module with delimiter='\t'. No external dependency needed. | HIGH |

**Anti-recommendation: MLflow, Weights & Biases, Neptune.** Do NOT use these for v1. They add: (1) server dependencies (MLflow needs a tracking server), (2) network calls that can fail during autonomous runs, (3) complexity that's unnecessary when git IS your experiment tracker. The whole point of the autoresearch pattern is that git commits ARE the experiment log. A TSV file provides the summary view.

### Process Management

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| subprocess (stdlib) | N/A | Run experiments | subprocess.run() to execute the training script, capture stdout/stderr to run.log, enforce timeouts. This is how autoresearch does it. | HIGH |
| signal (stdlib) | N/A | Timeout enforcement | Use signal.alarm() or subprocess timeout parameter to kill hung experiments. Essential for autonomous operation. | HIGH |

**Anti-recommendation: Celery, Ray, multiprocessing.** Do NOT use these for v1. Single-machine, single-experiment-at-a-time is the autoresearch pattern. Adding distributed execution adds complexity with zero benefit when experiments take ~30 seconds each.

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| optuna | >=3.6,<4.0 | Hyperparameter optimization | Optional. The agent can do manual hyperparameter iteration, but Optuna can be used WITHIN an experiment (the agent writes code that uses Optuna). Not as an orchestrator. | MEDIUM |
| scipy | >=1.13 | Statistical functions | Transitive dependency of scikit-learn. Pin for reproducibility. | MEDIUM |
| joblib | >=1.4 | Parallel model fitting | Transitive dependency of scikit-learn. Used for parallel cross-validation. | MEDIUM |

### Development Dependencies

| Library | Version | Purpose | Confidence |
|---------|---------|---------|------------|
| ruff | >=0.5 | Linting + formatting | Fast Python linter/formatter. Replaces flake8+black+isort. | HIGH |
| pytest | >=8.0 | Testing | For framework tests (not ML experiment tests). | HIGH |

## How Autoresearch Structures Dependencies

Based on training data analysis of Karpathy's autoresearch (HIGH confidence on patterns, MEDIUM on exact versions):

**Key patterns:**
- Uses `uv` for package management (uv pip install, uv venv)
- Minimal dependencies: PyTorch + a few data libraries
- No experiment tracking library -- just `results.tsv` appended after each run
- Git operations via shell commands (`subprocess` or direct shell in the agent loop)
- Single `train.py` file that the agent modifies
- `run.log` for stdout/stderr capture to avoid flooding the agent context
- `program.md` as human-editable guidance file

**Translated to this project's domain:**
- Replace PyTorch with scikit-learn + XGBoost + LightGBM
- Keep everything else identical: uv, results.tsv, subprocess git, run.log, program.md

## How AIDE Structures Dependencies

Based on training data analysis of Weco AI's AIDE (MEDIUM confidence):

**Key patterns:**
- Python package with `pyproject.toml`
- Dependencies: openai (for LLM calls), tree-sitter (for code analysis), docker (for sandboxing)
- ML libraries are NOT dependencies of AIDE itself -- they're installed in the execution environment
- Separate concerns: AIDE is the orchestrator, the experiment code runs in isolation
- Uses a "journal" data structure (tree of solution nodes) rather than TSV

**Translated to this project:**
- This project does NOT need AIDE's approach because Claude Code IS the orchestrator
- ML libraries ARE direct dependencies (they run in the same environment, not in Docker)
- No need for tree-sitter or code parsing -- Claude Code handles that natively
- No need for openai SDK -- Claude Code handles LLM calls natively

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Package Manager | uv | pip + venv | uv is faster, handles lockfiles, PROJECT.md specifies it |
| Git Integration | subprocess + git CLI | GitPython | Memory leaks, unnecessary abstraction, harder to debug |
| Experiment Tracking | results.tsv + git | MLflow | Server dependency, network calls, overkill for file-based tracking |
| Experiment Tracking | results.tsv + git | Weights & Biases | External service, network dependency, overkill |
| Process Management | subprocess | Ray | Distributed computing overhead, single-machine project |
| Hyperparameters | Agent-driven (manual) | Optuna (as orchestrator) | Agent should explore creatively, not delegate to optimization library |
| Data Validation | pandas assertions | Great Expectations | Heavyweight, the frozen data pipeline handles validation |
| Boosting | XGBoost + LightGBM | CatBoost only | Less ecosystem support, XGBoost/LightGBM are more commonly used |

## Project Structure

```
AutoML/
  pyproject.toml           # uv-managed dependencies
  uv.lock                  # Lockfile for reproducibility
  .python-version          # Pin Python version (e.g., 3.11)
  src/
    automl/
      __init__.py
      data.py              # FROZEN: data loading, splitting, evaluation
      model.py             # MUTABLE: agent modifies this
      run.py               # Entry point: load data, train, evaluate, print metric
      git_ops.py           # Git operations via subprocess
      experiment_log.py    # TSV append/read for results.tsv
  program.md               # Human domain expertise
  results.tsv              # Experiment log
  run.log                  # Stdout/stderr from last run
  CLAUDE.md                # Instructions for Claude Code agent
```

## pyproject.toml Skeleton

```toml
[project]
name = "automl"
version = "0.1.0"
requires-python = ">=3.11,<3.13"
dependencies = [
    "scikit-learn>=1.5,<2.0",
    "xgboost>=2.1,<3.0",
    "lightgbm>=4.5,<5.0",
    "pandas>=2.2,<3.0",
    "numpy>=1.26,<3.0",
]

[project.optional-dependencies]
extra-models = [
    "catboost>=1.2,<2.0",
]
dev = [
    "ruff>=0.5",
    "pytest>=8.0",
]

[tool.ruff]
line-length = 120
target-version = "py311"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project and install dependencies
uv venv
uv pip install -e ".[dev]"

# Or with lockfile
uv lock
uv sync
```

## Critical Version Verification Needed

The following versions are based on training data (cutoff ~May 2025) and MUST be verified before writing the final pyproject.toml:

| Package | Stated Version | How to Verify |
|---------|---------------|---------------|
| scikit-learn | >=1.5 | `pip index versions scikit-learn` |
| xgboost | >=2.1 | `pip index versions xgboost` |
| lightgbm | >=4.5 | `pip index versions lightgbm` |
| pandas | >=2.2 | `pip index versions pandas` |
| numpy | >=1.26 | `pip index versions numpy` |
| uv | >=0.4 | `uv --version` |

**Note:** Use `>=` lower bounds (not `==` pins) so that `uv lock` captures the exact resolution. The lockfile provides reproducibility; the pyproject.toml specifies compatibility ranges.

## Sources

- PROJECT.md (project constraints and decisions)
- Training data knowledge of autoresearch (Karpathy, late 2024 - early 2025)
- Training data knowledge of AIDE/Weco AI (2024-2025)
- Training data knowledge of scikit-learn, XGBoost, LightGBM, pandas, numpy release cycles
- Training data knowledge of uv (Astral, 2024-2025)

**Confidence caveat:** All version numbers are MEDIUM confidence. They are based on training data and may be one minor version behind current releases. The version ranges (>=X, <Y) are designed to accommodate this -- `uv lock` will resolve to the actual latest compatible versions at install time.
