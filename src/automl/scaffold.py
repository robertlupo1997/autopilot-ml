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
import shutil
import textwrap
from pathlib import Path

import automl.prepare as _prepare_module
from automl.prepare import (
    build_preprocessor,
    get_baselines,
    get_data_summary,
    load_data,
    validate_metric,
)
from automl.templates import render_claude_md, render_program_md


def scaffold_experiment(
    data_path: str | Path,
    target_column: str,
    metric: str,
    goal: str,
    output_dir: str | Path | None = None,
    time_budget: int = 60,
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

    # Early validation: load data and check metric compatibility
    X, y, task = load_data(str(csv_path), target_column)
    _sklearn_metric, direction = validate_metric(metric, task)

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

    # 2. Generate train.py from template with config substitution
    # train_template.py uses sibling imports (from prepare import ...) so we
    # cannot import it as automl.train_template. Use importlib to locate it.
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

    # 3. Copy CSV into experiment directory
    shutil.copy2(csv_path, out / csv_path.name)

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

    return out


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


def _gitignore_content() -> str:
    """Return .gitignore content for experiment directories."""
    return textwrap.dedent("""\
        results.tsv
        run.log
        __pycache__/
        *.pyc
        .venv/
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
        ]
    """)
