"""Experiment directory scaffolding.

Creates a complete standalone experiment directory from a CSV file,
containing all files needed for autonomous ML experimentation:
prepare.py, train.py, program.md, CLAUDE.md, .gitignore, pyproject.toml,
and a copy of the dataset.

CLI-01: scaffold_experiment function
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import shutil
import textwrap
from pathlib import Path

import automl.forecast as _forecast_module
import automl.prepare as _prepare_module
from automl.prepare import (
    build_preprocessor,
    get_baselines,
    get_data_summary,
    load_data,
    validate_metric,
)
from automl.templates import render_claude_md, render_claude_md_forecast, render_program_md


def scaffold_experiment(
    data_path: str | Path,
    target_column: str,
    metric: str,
    goal: str,
    output_dir: str | Path | None = None,
    time_budget: int = 60,
    date_col: str | None = None,
) -> Path:
    """Create a complete experiment directory from a CSV file.

    Parameters
    ----------
    data_path : str or Path
        Path to the CSV dataset.
    target_column : str
        Name of the target column.
    metric : str
        User-facing metric name (e.g. "accuracy", "rmse").
    goal : str
        Human-readable description of the prediction goal.
    output_dir : str, Path, or None
        Where to create the experiment directory. If None, creates
        ``experiment-{csv_stem}`` in the current working directory.
    time_budget : int
        Time budget in seconds for each experiment run (default 60).
    date_col : str or None
        Name of the date column to enable forecasting mode. When provided,
        scaffolds a forecasting experiment using forecast templates instead of
        the standard classification/regression templates. Default: None (v1.0 path).

    Returns
    -------
    Path
        Path to the created experiment directory.

    Raises
    ------
    FileNotFoundError
        If data_path does not exist.
    FileExistsError
        If output_dir already exists.
    ValueError
        If metric is invalid for the detected task type.
    """
    csv_path = Path(data_path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Load data (pass date_col for forecasting mode)
    X, y, task = load_data(str(csv_path), target_column, date_col=date_col)

    # Resolve output directory
    if output_dir is None:
        out = Path(f"experiment-{csv_path.stem}")
    else:
        out = Path(output_dir)

    # Create output directory (fail if exists)
    out.mkdir(parents=True, exist_ok=False)

    # 1. Copy prepare.py (byte-identical to installed source)
    prepare_source = inspect.getfile(_prepare_module)
    shutil.copy2(prepare_source, out / "prepare.py")

    # 1b. Copy forecast.py (byte-identical to installed source)
    forecast_source = inspect.getfile(_forecast_module)
    shutil.copy2(forecast_source, out / "forecast.py")

    # 3. Copy CSV into experiment directory
    shutil.copy2(csv_path, out / csv_path.name)

    if date_col is not None:
        # --- Forecasting path ---
        direction = "minimize"

        # 2. Generate train.py from forecast template
        _fspec = importlib.util.find_spec("automl.train_template_forecast")
        forecast_template_content = Path(_fspec.origin).read_text()
        train_content = forecast_template_content
        train_content = train_content.replace(
            'CSV_PATH = "data.csv"', f'CSV_PATH = "{csv_path.name}"'
        )
        train_content = train_content.replace(
            'TARGET_COLUMN = "target"', f'TARGET_COLUMN = "{target_column}"'
        )
        train_content = train_content.replace(
            'DATE_COLUMN = "date"', f'DATE_COLUMN = "{date_col}"'
        )
        train_content = train_content.replace(
            'METRIC = "mape"', f'METRIC = "{metric}"'
        )
        train_content = train_content.replace(
            "TIME_BUDGET = 120", f"TIME_BUDGET = {time_budget}"
        )
        (out / "train.py").write_text(train_content)

        # 4. Compute forecasting summary and baselines
        summary_str = _format_forecast_summary(X, y)
        baselines_str = _format_forecast_baselines(y.values)

        # 5. Render forecasting program.md (custom — avoids "higher is always better")
        program_md = _render_forecast_program_md(
            dataset_name=csv_path.stem,
            goal=goal,
            metric=metric,
            summary_str=summary_str,
            baselines_str=baselines_str,
        )
        (out / "program.md").write_text(program_md)

        # 6. Render forecasting CLAUDE.md
        claude_md = render_claude_md_forecast()
        (out / "CLAUDE.md").write_text(claude_md)

    else:
        # --- Standard v1.0 path (no regression) ---
        _sklearn_metric, direction = validate_metric(metric, task)

        # 2. Generate train.py from standard template
        _spec = importlib.util.find_spec("automl.train_template")
        template_source = _spec.origin
        template_content = Path(template_source).read_text()
        train_content = template_content
        train_content = train_content.replace(
            'CSV_PATH = "data.csv"', f'CSV_PATH = "{csv_path.name}"'
        )
        train_content = train_content.replace(
            'TARGET_COLUMN = "target"', f'TARGET_COLUMN = "{target_column}"'
        )
        train_content = train_content.replace(
            'METRIC = "accuracy"', f'METRIC = "{metric}"'
        )
        train_content = train_content.replace(
            "TIME_BUDGET = 60", f"TIME_BUDGET = {time_budget}"
        )
        (out / "train.py").write_text(train_content)

        # 4. Compute data summary and baselines
        preprocessor = build_preprocessor(X)
        X_processed = preprocessor.transform(X)
        baselines = get_baselines(X_processed, y, _sklearn_metric, task)
        summary = get_data_summary(X, y, task)

        summary_str = _format_summary(summary)
        baselines_str = _format_baselines(baselines)

        # 5. Render program.md
        program_md = render_program_md(
            dataset_name=csv_path.stem,
            goal_description=goal,
            metric_name=metric,
            direction=direction,
            data_summary=summary_str,
            baselines=baselines_str,
        )
        (out / "program.md").write_text(program_md)

        # 6. Render CLAUDE.md
        claude_md = render_claude_md()
        (out / "CLAUDE.md").write_text(claude_md)

    # 7. Write .gitignore
    (out / ".gitignore").write_text(_gitignore_content())

    # 8. Write pyproject.toml
    (out / "pyproject.toml").write_text(_pyproject_content(csv_path.stem))

    # 9. Write .claude/ directory with settings.json and guard hook
    _dot_claude_settings(out)

    return out


def _format_forecast_summary(X, y) -> str:
    """Format a forecasting data summary for program.md."""
    import pandas as pd

    rows, cols = X.shape
    lines = []
    lines.append(f"- **Shape:** {rows} rows x {cols + 1} columns (including target)")

    # Time range (X has DatetimeIndex after load_data with date_col)
    try:
        start_date = X.index[0].date()
        end_date = X.index[-1].date()
        lines.append(f"- **Time range:** {start_date} to {end_date}")
    except Exception:
        lines.append("- **Time range:** (could not determine)")

    # Inferred frequency
    try:
        freq = pd.infer_freq(X.index)
        if freq is None:
            freq = "irregular (could not infer)"
    except Exception:
        freq = "irregular (could not infer)"
    lines.append(f"- **Inferred frequency:** {freq}")

    # Target stats
    y_vals = y.values if hasattr(y, "values") else y
    lines.append(
        f"- **Target stats:** mean={y_vals.mean():.2f}, "
        f"std={y_vals.std():.2f}, "
        f"min={y_vals.min():.2f}, max={y_vals.max():.2f}"
    )

    return "\n".join(lines)


def _format_forecast_baselines(y_values) -> str:
    """Compute and format naive/seasonal-naive MAPE baselines for program.md."""
    from automl.forecast import get_forecasting_baselines

    baselines = get_forecasting_baselines(y_values, n_splits=5, period=4)
    naive = baselines["naive"]
    seasonal = baselines["seasonal_naive"]
    lines = [
        f"- **Naive MAPE:** {naive:.4f} ({naive * 100:.1f}%)",
        f"- **Seasonal Naive MAPE:** {seasonal:.4f} ({seasonal * 100:.1f}%)",
    ]
    return "\n".join(lines)


def _render_forecast_program_md(
    dataset_name: str,
    goal: str,
    metric: str,
    summary_str: str,
    baselines_str: str,
) -> str:
    """Render a forecasting-specific program.md (does NOT say 'higher is always better')."""
    return f"""# Program: {dataset_name}

## Goal

{goal or f"Forecast {dataset_name} using time-series methods."}

## Metric

**{metric} (minimize)** — lower MAPE is better; 0.05 = 5% mean absolute percentage error.

## Data Description

{summary_str}

## Baselines

{baselines_str}

## Domain Expertise

*(Human operator: fill in any domain-specific knowledge, known patterns, seasonal effects, or strategy hints here.)*
"""


def _format_summary(summary: dict) -> str:
    """Format a data summary dict as a human-readable string."""
    lines = []
    rows, cols = summary["shape"]
    lines.append(f"- **Shape:** {rows} rows x {cols} columns")

    dtypes = summary["dtypes"]
    dtype_parts = [f"{v} {k}" for k, v in dtypes.items()]
    lines.append(f"- **Column types:** {', '.join(dtype_parts)}")

    lines.append(f"- **Missing values:** {summary['missing']}")

    dist = summary["target_distribution"]
    if isinstance(dist, dict):
        # Check if classification (string/int keys) or regression (stat keys)
        if "mean" in dist:
            lines.append(
                f"- **Target stats:** mean={dist['mean']:.2f}, "
                f"std={dist['std']:.2f}, "
                f"min={dist['min']:.2f}, max={dist['max']:.2f}"
            )
        else:
            dist_parts = [f"{k}: {v}" for k, v in dist.items()]
            lines.append(f"- **Target distribution:** {', '.join(dist_parts)}")

    return "\n".join(lines)


def _format_baselines(baselines: dict) -> str:
    """Format baseline scores as a human-readable string."""
    lines = []
    for name, scores in baselines.items():
        lines.append(
            f"- **{name}:** {scores['score']:.4f} (+/- {scores['std']:.4f})"
        )
    return "\n".join(lines)


def _guard_frozen_hook_content() -> str:
    """Return the bash script content for .claude/hooks/guard-frozen.sh."""
    return textwrap.dedent("""\
        #!/bin/bash
        # Guard: deny writes to frozen files. Reads PreToolUse JSON from stdin.
        INPUT=$(cat)
        # Try jq first, fall back to python3
        if command -v jq >/dev/null 2>&1; then
          FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
        else
          FILE_PATH=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))")
        fi
        BASENAME=$(basename "$FILE_PATH" 2>/dev/null)
        FROZEN_FILES="prepare.py forecast.py"
        for frozen in $FROZEN_FILES; do
          if [ "$BASENAME" = "$frozen" ]; then
            cat <<'DENY'
        {"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"prepare.py and forecast.py are FROZEN. Only train.py is mutable. Do not modify prepare.py or forecast.py."}}
        DENY
            exit 0
          fi
        done
        exit 0
    """)


def _dot_claude_settings(out: Path) -> None:
    """Create .claude/ directory with settings.json and guard-frozen.sh hook.

    Parameters
    ----------
    out : Path
        Root of the experiment directory.
    """
    dot_claude = out / ".claude"
    hooks_dir = dot_claude / "hooks"
    dot_claude.mkdir(exist_ok=True)
    hooks_dir.mkdir(exist_ok=True)

    settings = {
        "$schema": "https://docs.anthropic.com/en/docs/claude-code/settings",
        "permissions": {
            "allow": [
                "Bash(*)",
                "Edit(*)",
                "Write(*)",
                "Read",
                "Glob",
                "Grep",
            ],
            "deny": [
                "Edit(prepare.py)",
                "Write(prepare.py)",
                "Edit(forecast.py)",
                "Write(forecast.py)",
            ],
        },
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": '"$CLAUDE_PROJECT_DIR"/.claude/hooks/guard-frozen.sh',
                        }
                    ],
                }
            ]
        },
    }
    (dot_claude / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")

    hook_path = hooks_dir / "guard-frozen.sh"
    hook_path.write_text(_guard_frozen_hook_content())
    hook_path.chmod(0o755)


def _gitignore_content() -> str:
    """Return .gitignore content for experiment directories."""
    return textwrap.dedent("""\
        results.tsv
        run.log
        checkpoint.json
        checkpoint.json.tmp
        __pycache__/
        *.pyc
        .venv/
        .claude/settings.local.json
        .swarm/scoreboard.tsv
        .swarm/scoreboard.lock
        .swarm/claims/
        .swarm/config.json
        .swarm/best_train.py
    """)


def _pyproject_content(dataset_name: str) -> str:
    """Return pyproject.toml content for experiment directories."""
    return textwrap.dedent(f"""\
        [project]
        name = "experiment-{dataset_name}"
        version = "0.1.0"
        requires-python = ">=3.11"
        dependencies = [
            "scikit-learn>=1.5",
            "pandas>=2.0",
            "numpy>=2.0",
            "xgboost",
            "lightgbm",
            "optuna>=4.0",
        ]
    """)
