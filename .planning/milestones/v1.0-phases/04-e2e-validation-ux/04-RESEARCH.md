# Phase 4: E2E Validation + UX - Research

**Researched:** 2026-03-19
**Domain:** End-to-end validation, task auto-detection, model artifact export, run retrospective
**Confidence:** HIGH

## Summary

Phase 4 delivers seven requirements across three domains: (1) UX features that make mlforge usable without expertise (simple mode, expert mode, dataset profiling), (2) artifact export so completed runs produce a usable model with metadata, and (3) a run retrospective that summarizes what happened. There is also E2E validation proving the full pipeline works on real data, and TABL-03 leakage prevention verification.

The codebase is well-structured for these additions. The existing `Config` dataclass, `scaffold_experiment()` flow, `RunEngine`, and `ResultsTracker` provide clean integration points. Simple mode is primarily auto-detection logic in the CLI layer that infers task type and metric from the dataset. Expert mode is CLI flags that pass custom paths through to scaffold. Artifact export is `joblib.dump()` of the best model with a JSON metadata sidecar. The retrospective is a markdown report generated from `ResultsTracker.summary()` plus `CostTracker` data.

**Primary recommendation:** Split into 3 plans: (1) Simple/Expert mode + dataset profiling (UX-01, UX-02, UX-04), (2) Artifact export + run retrospective + GUARD-06 (UX-03, UX-05, GUARD-06), (3) E2E validation on real tabular data (TABL-03, integration test).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UX-01 | Simple mode auto-detects task type, selects metrics, runs with minimal input | Dataset profiling via `get_data_summary()` already exists in prepare.py; add auto-detection logic in CLI/scaffold |
| UX-02 | Expert mode accepts custom CLAUDE.md, frozen/mutable zones, baselines, plugin API | CLI flags + Config overrides; scaffold already supports custom frozen/mutable via Config |
| UX-03 | Best model artifact exported with metadata after session | joblib serialization + JSON metadata sidecar; engine post-loop export |
| UX-04 | Dataset profiling analyzes schema, feature types, target distribution, temporal patterns | `get_data_summary()` already in prepare.py; extend for temporal detection and missing value analysis |
| UX-05 | Run retrospective summarizes approaches tried, failures, cost, recommendations | `ResultsTracker.summary()` + `CostTracker` + journal entries; generate markdown report |
| GUARD-06 | Run summary generated at session end | Same as UX-05 -- the run retrospective IS the run summary |
| TABL-03 | Leakage prevention: shift-first temporal features, walk-forward CV | `temporal_split()` and `validate_no_leakage()` already in prepare.py; E2E validates they work |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| joblib | 1.5.x | Model serialization (pickle with compression) | Bundled with scikit-learn; handles numpy arrays, sparse matrices, sklearn pipelines natively |
| pandas | 2.0+ | Dataset profiling and type inference | Already a dependency; `pd.api.types` for dtype detection |
| rich | 13.0+ | Retrospective terminal display | Already a dependency for LiveProgress |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | - | Metadata sidecar for exported models | Always -- model metadata stored alongside joblib artifact |
| pathlib (stdlib) | - | File path operations | Always -- consistent with existing codebase pattern |
| datetime (stdlib) | - | Timestamps in retrospective and metadata | Always |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| joblib | pickle | joblib handles numpy arrays and large data more efficiently; joblib is already installed via sklearn |
| joblib | ONNX export | ONNX requires model-specific converters; too complex for Phase 4; better as ADV feature |
| JSON metadata | TOML metadata | JSON is machine-readable by default; matches existing state.py pattern |

**Installation:**
```bash
# No new dependencies -- joblib comes with scikit-learn, all others already in pyproject.toml
```

## Architecture Patterns

### Recommended Project Structure
```
src/mlforge/
  cli.py              # Add --mode simple/expert, --custom-claude-md, --custom-frozen flags
  config.py           # Add mode field, custom_claude_md_path, custom_baselines
  scaffold.py         # Route through simple vs expert mode; dataset profiling integration
  engine.py           # Post-loop: export artifact, generate retrospective
  profiler.py         # NEW: Dataset profiling (auto-detect task, temporal patterns, schema)
  export.py           # NEW: Model artifact export (joblib + metadata JSON)
  retrospective.py    # NEW: Run retrospective markdown generation
  tabular/
    baselines.py      # No changes
    prepare.py        # Already has get_data_summary(), temporal_split(), validate_no_leakage()
```

### Pattern 1: Auto-Detection via Dataset Profiling
**What:** Infer task type (classification vs regression), metric, and temporal nature from dataset schema
**When to use:** Simple mode (UX-01)
**Example:**
```python
# Source: existing prepare.py get_data_summary() + new profiler.py
def profile_dataset(df: pd.DataFrame, target_column: str) -> DatasetProfile:
    """Auto-detect task type, metric, and temporal characteristics."""
    target = df[target_column]

    # Task detection: categorical target or low-cardinality numeric = classification
    if not pd.api.types.is_numeric_dtype(target) or target.nunique() <= 20:
        task = "classification"
        metric = "accuracy" if target.nunique() == 2 else "f1_weighted"
        direction = "maximize"
    else:
        task = "regression"
        metric = "r2"
        direction = "maximize"

    # Temporal detection: look for datetime-parseable columns
    date_columns = _detect_date_columns(df)

    return DatasetProfile(task=task, metric=metric, direction=direction,
                         date_columns=date_columns, ...)
```

### Pattern 2: Expert Mode Pass-Through
**What:** CLI flags that override scaffold defaults with user-provided files
**When to use:** Expert mode (UX-02)
**Example:**
```python
# CLI flags -> Config fields -> scaffold_experiment reads them
parser.add_argument("--custom-claude-md", type=Path, help="Custom CLAUDE.md template")
parser.add_argument("--custom-frozen", nargs="+", help="Additional frozen files")
parser.add_argument("--custom-mutable", nargs="+", help="Additional mutable files")

# In scaffold_experiment: if config.custom_claude_md_path:
#   copy user's CLAUDE.md instead of rendering from template
```

### Pattern 3: Post-Loop Artifact Export
**What:** After engine.run() completes, export the best model with metadata
**When to use:** Always at session end (UX-03)
**Example:**
```python
# Source: joblib docs + sklearn patterns
def export_best_model(
    experiment_dir: Path,
    state: SessionState,
    config: Config,
    results_tracker: ResultsTracker,
) -> Path:
    """Export best model artifact with metadata sidecar."""
    artifacts_dir = experiment_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    # The agent's train.py should save model to a known path
    # Export copies it to artifacts/ with metadata
    model_path = artifacts_dir / "best_model.joblib"
    metadata = {
        "metric_name": config.metric,
        "metric_value": state.best_metric,
        "best_commit": state.best_commit,
        "experiment_count": state.experiment_count,
        "total_cost_usd": state.cost_spent_usd,
        "config": asdict(config),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    (artifacts_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    return model_path
```

### Pattern 4: Retrospective Report Generation
**What:** Markdown report from ResultsTracker + CostTracker data
**When to use:** At session end (UX-05, GUARD-06)
**Example:**
```python
def generate_retrospective(
    results_tracker: ResultsTracker,
    state: SessionState,
    config: Config,
) -> str:
    """Generate a markdown run retrospective."""
    summary = results_tracker.summary()
    kept = results_tracker.get_by_status("keep")
    reverted = results_tracker.get_by_status("revert")

    sections = [
        f"# Run Retrospective\n",
        f"## Summary\n- Experiments: {summary['total_experiments']}\n",
        f"- Best metric ({config.metric}): {summary['best_metric']}\n",
        f"- Cost: ${state.cost_spent_usd:.2f}\n",
        f"## Approaches That Worked\n",
        # List kept experiments with descriptions
        f"## Failed Approaches\n",
        # List reverted experiments
        f"## Recommendations\n",
    ]
    return "\n".join(sections)
```

### Anti-Patterns to Avoid
- **Auto-detecting task type from column name:** Use statistical properties (nunique, dtype), not heuristic name matching
- **Exporting model from within the agent loop:** The agent saves models; mlforge infrastructure copies/packages them post-loop
- **Coupling retrospective generation to engine.run():** Keep it as a separate function called after run() returns for testability

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model serialization | Custom pickle wrapper | `joblib.dump()` / `joblib.load()` | Handles numpy, sparse matrices, large arrays with compression; standard sklearn pattern |
| Task type detection | Name-based heuristics | `pd.api.types.is_numeric_dtype()` + `nunique()` threshold | Robust against edge cases; matches pandas ecosystem conventions |
| Datetime detection | Regex on column names | `pd.to_datetime(col, errors='coerce')` + check success rate | Handles ISO, US, European, epoch formats automatically |
| Rich markdown tables | String concatenation | `rich.table.Table` for terminal + string formatting for file | Rich is already a dependency; provides consistent styling |

**Key insight:** Most of these features compose existing infrastructure -- `get_data_summary()`, `ResultsTracker.summary()`, `CostTracker`, `Config`. The new code is glue and formatting, not new algorithms.

## Common Pitfalls

### Pitfall 1: Model Not Available at Export Time
**What goes wrong:** The agent's train.py creates a model object in memory during `claude -p` subprocess, but it's gone when the process exits. mlforge cannot access the trained model directly.
**Why it happens:** Each experiment runs in a separate `claude -p` process.
**How to avoid:** The agent's CLAUDE.md protocol must instruct it to `joblib.dump(model, "best_model.joblib")` after each kept experiment. The export step copies/packages this file. The train.py template should include model saving.
**Warning signs:** `best_model.joblib` not found in experiment directory after a kept experiment.

### Pitfall 2: Auto-Detection Misclassifies Regression as Classification
**What goes wrong:** A regression target with few unique values (e.g., ratings 1-5) gets classified as classification.
**Why it happens:** Threshold-based detection using `nunique()` is inherently ambiguous.
**How to avoid:** Use `nunique() <= 20` as threshold (not 10); if numeric dtype AND nunique > 2 AND nunique <= 20, flag as "ambiguous" and let user confirm or default to classification. Log the decision.
**Warning signs:** Model trained with classification metric on a continuous target.

### Pitfall 3: Retrospective With No Results
**What goes wrong:** If all experiments crash or the budget is exhausted immediately, the retrospective has no data.
**Why it happens:** Edge case of zero successful experiments.
**How to avoid:** Handle empty ResultsTracker gracefully -- "No successful experiments" message instead of division-by-zero errors.
**Warning signs:** `summary["total_experiments"] == 0` or `summary["keeps"] == 0`.

### Pitfall 4: Expert Mode Breaks Scaffold Assumptions
**What goes wrong:** User provides custom frozen files that conflict with hook enforcement, or custom CLAUDE.md that lacks essential protocol rules.
**Why it happens:** Expert mode bypasses validation that simple mode handles automatically.
**How to avoid:** Validate custom inputs: check frozen files exist, warn if custom CLAUDE.md is missing "metric" or "frozen" keywords, merge (don't replace) frozen file lists.
**Warning signs:** Hook engine blocks writes the user expected to be allowed.

### Pitfall 5: TABL-03 Temporal Leakage in E2E Test
**What goes wrong:** Walk-forward CV not used for temporal data, or shift-first pattern not enforced.
**Why it happens:** Auto-detection doesn't recognize date column, falls back to random split.
**How to avoid:** Dataset profiling MUST detect date columns and set `date_column` in config when temporal data is detected. `validate_no_leakage()` should be called during scaffold.
**Warning signs:** Random train/test split on time-series data.

## Code Examples

### Dataset Profiler
```python
# New module: src/mlforge/profiler.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class DatasetProfile:
    """Results of dataset auto-analysis."""
    task: str                    # "classification" or "regression"
    metric: str                  # auto-selected metric
    direction: str               # "maximize" or "minimize"
    n_rows: int
    n_features: int
    numeric_features: list[str]
    categorical_features: list[str]
    date_columns: list[str]
    target_stats: dict
    missing_pct: float           # overall missing data percentage
    leakage_warnings: list[str]


def profile_dataset(
    df: pd.DataFrame,
    target_column: str,
) -> DatasetProfile:
    """Analyze dataset and auto-detect task type, metric, and properties."""
    target = df[target_column]
    feature_cols = [c for c in df.columns if c != target_column]

    # Task type detection
    if not pd.api.types.is_numeric_dtype(target) or target.nunique() <= 20:
        task = "classification"
        metric = "accuracy" if target.nunique() == 2 else "f1_weighted"
        direction = "maximize"
    else:
        task = "regression"
        metric = "r2"
        direction = "maximize"

    # Feature type detection
    numeric = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c])]
    categorical = [c for c in feature_cols if not pd.api.types.is_numeric_dtype(df[c])]

    # Date column detection
    date_cols = _detect_date_columns(df, feature_cols)

    # Missing data
    total_cells = df[feature_cols].size
    missing = df[feature_cols].isna().sum().sum()
    missing_pct = (missing / total_cells * 100) if total_cells > 0 else 0.0

    # Target stats (reuse prepare.py pattern)
    if task == "regression":
        target_stats = {
            "type": "continuous",
            "mean": float(target.mean()),
            "std": float(target.std()),
        }
    else:
        target_stats = {
            "type": "categorical",
            "n_classes": int(target.nunique()),
            "distribution": target.value_counts().to_dict(),
        }

    return DatasetProfile(
        task=task, metric=metric, direction=direction,
        n_rows=len(df), n_features=len(feature_cols),
        numeric_features=numeric, categorical_features=categorical,
        date_columns=date_cols, target_stats=target_stats,
        missing_pct=missing_pct, leakage_warnings=[],
    )


def _detect_date_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    """Detect columns that contain datetime values."""
    date_cols = []
    for col in columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            date_cols.append(col)
            continue
        if df[col].dtype == object:
            sample = df[col].dropna().head(20)
            try:
                parsed = pd.to_datetime(sample, errors="coerce")
                if parsed.notna().mean() > 0.8:
                    date_cols.append(col)
            except Exception:
                pass
    return date_cols
```

### Model Artifact Export
```python
# New module: src/mlforge/export.py
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2

from mlforge.config import Config
from mlforge.state import SessionState


def export_artifact(
    experiment_dir: Path,
    state: SessionState,
    config: Config,
) -> Path | None:
    """Export best model artifact with metadata.

    Looks for best_model.joblib in experiment_dir. If found,
    copies to artifacts/ directory with metadata.json sidecar.

    Returns artifacts directory path, or None if no model found.
    """
    model_file = experiment_dir / "best_model.joblib"
    if not model_file.exists():
        return None

    artifacts_dir = experiment_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    copy2(model_file, artifacts_dir / "best_model.joblib")

    metadata = {
        "metric_name": config.metric,
        "metric_value": state.best_metric,
        "metric_direction": config.direction,
        "best_commit": state.best_commit,
        "experiment_count": state.experiment_count,
        "total_cost_usd": state.cost_spent_usd,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    (artifacts_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )

    return artifacts_dir
```

### Run Retrospective
```python
# New module: src/mlforge/retrospective.py
from mlforge.results import ResultsTracker
from mlforge.state import SessionState
from mlforge.config import Config


def generate_retrospective(
    tracker: ResultsTracker,
    state: SessionState,
    config: Config,
) -> str:
    """Generate markdown run retrospective report."""
    summary = tracker.summary()
    lines = [
        "# mlforge Run Retrospective\n",
        "## Summary\n",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total experiments | {summary['total_experiments']} |",
        f"| Kept (improvements) | {summary['keeps']} |",
        f"| Reverted | {summary['reverts']} |",
        f"| Crashed | {summary['crashes']} |",
        f"| Best {config.metric} | {summary['best_metric']} |",
        f"| Total cost | ${state.cost_spent_usd:.2f} |",
        "",
    ]

    # Approaches that worked
    kept = tracker.get_by_status("keep")
    if kept:
        lines.append("## Successful Approaches\n")
        for r in kept:
            lines.append(
                f"- Experiment {r.experiment_id}: "
                f"{r.description} ({config.metric}={r.metric_value})"
            )
        lines.append("")

    # Failed approaches
    reverted = tracker.get_by_status("revert")
    if reverted:
        lines.append("## Failed Approaches\n")
        for r in reverted[:10]:  # Limit to 10
            lines.append(f"- Experiment {r.experiment_id}: {r.description}")
        if len(reverted) > 10:
            lines.append(f"- ... and {len(reverted) - 10} more")
        lines.append("")

    # Recommendations
    lines.append("## Recommendations\n")
    if summary["keeps"] == 0:
        lines.append("- No improvements found. Consider different model families or feature engineering.")
    elif summary["reverts"] > summary["keeps"] * 3:
        lines.append("- High revert rate. Consider narrower search space or more budget.")
    else:
        lines.append(f"- Best approach committed at {summary['best_commit']}.")
        lines.append("- Consider longer budget or stagnation branching for further improvement.")
    lines.append("")

    return "\n".join(lines)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual task type specification | Auto-detect from target column stats | Standard in AutoML (auto-sklearn, FLAML) | Users need only dataset + goal |
| Model saved in notebook/script | Artifact export with metadata sidecar | Standard in MLflow/W&B | Reproducible model deployment |
| No run summary | Structured retrospective from experiment log | Standard in experiment trackers | Users understand what happened without reading logs |

**Deprecated/outdated:**
- Saving models with `pickle.dump()` directly: Use `joblib.dump()` for sklearn-compatible models (better handling of large numpy arrays)

## Open Questions

1. **Model saving location convention**
   - What we know: The agent (claude -p) trains models in subprocess. joblib.dump() must be called inside train.py.
   - What's unclear: Should train.py always save to `best_model.joblib` at root, or should the engine instruct a specific path via protocol?
   - Recommendation: CLAUDE.md template should include rule: "Save best model to best_model.joblib using joblib.dump()". The export step copies this to artifacts/.

2. **Training history format**
   - What we know: UX-03 says "training history" should be part of artifact metadata.
   - What's unclear: What constitutes "training history" for tabular ML (no epochs)?
   - Recommendation: Use the experiment journal (ResultsTracker results) as training history. Include list of kept experiments with metrics in metadata.json.

3. **Auto-detection ambiguous cases**
   - What we know: Some targets (ratings 1-5, ordinal) are ambiguous between classification and regression.
   - What's unclear: Should we prompt the user or make a default decision?
   - Recommendation: Default to classification for nunique <= 20, log the decision. Users can override with `--metric` which implies task type.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/mlforge/ -x -q` |
| Full suite command | `python3 -m pytest tests/mlforge/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UX-01 | Simple mode auto-detects task, metric, runs with minimal input | unit | `python3 -m pytest tests/mlforge/test_profiler.py -x` | No -- Wave 0 |
| UX-02 | Expert mode accepts custom CLAUDE.md, frozen/mutable, baselines | unit | `python3 -m pytest tests/mlforge/test_cli.py::TestExpertMode -x` | No -- Wave 0 |
| UX-03 | Best model artifact exported with metadata | unit | `python3 -m pytest tests/mlforge/test_export.py -x` | No -- Wave 0 |
| UX-04 | Dataset profiling analyzes schema, types, distribution, temporal | unit | `python3 -m pytest tests/mlforge/test_profiler.py -x` | No -- Wave 0 |
| UX-05 | Run retrospective summarizes approaches, cost, recommendations | unit | `python3 -m pytest tests/mlforge/test_retrospective.py -x` | No -- Wave 0 |
| GUARD-06 | Run summary generated at session end | unit | `python3 -m pytest tests/mlforge/test_retrospective.py -x` | No -- Wave 0 |
| TABL-03 | Leakage prevention with temporal features and walk-forward CV | integration | `python3 -m pytest tests/mlforge/test_profiler.py::test_temporal_detection -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/mlforge/ -x -q`
- **Per wave merge:** `python3 -m pytest tests/mlforge/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/mlforge/test_profiler.py` -- covers UX-01, UX-04, TABL-03
- [ ] `tests/mlforge/test_export.py` -- covers UX-03
- [ ] `tests/mlforge/test_retrospective.py` -- covers UX-05, GUARD-06
- [ ] Update `tests/mlforge/test_cli.py` -- covers UX-02 expert mode flags

## Sources

### Primary (HIGH confidence)
- Codebase inspection: all 16 modules in src/mlforge/ read and analyzed
- pyproject.toml: dependency versions confirmed (scikit-learn 1.7.1, joblib 1.5.1)
- Existing prepare.py: `get_data_summary()`, `temporal_split()`, `validate_no_leakage()` confirmed present
- Existing ResultsTracker: `.summary()`, `.get_by_status()`, `.get_best()` confirmed present

### Secondary (MEDIUM confidence)
- joblib serialization patterns: standard sklearn documentation pattern for model persistence
- pandas dtype detection: `pd.api.types.is_numeric_dtype()` confirmed in existing codebase

### Tertiary (LOW confidence)
- None -- all findings verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies needed; all libraries already installed
- Architecture: HIGH - clean integration points identified in existing code; patterns follow established codebase conventions
- Pitfalls: HIGH - based on direct codebase analysis and understanding of subprocess architecture

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable domain, no fast-moving dependencies)
