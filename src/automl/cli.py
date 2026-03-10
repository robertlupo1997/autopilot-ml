"""CLI entry point for AutoML scaffold command.

CLI-02: CLI accepts positional args (data_path, target_column, metric)
        and optional flags (--goal, --output-dir, --time-budget).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Run the AutoML scaffold CLI.

    Parameters
    ----------
    argv : list of str or None
        Command-line arguments. If None, uses sys.argv[1:].

    Returns
    -------
    int
        Exit code: 0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        prog="automl",
        description="Scaffold an autonomous ML experiment from a CSV file.",
    )
    parser.add_argument(
        "data_path",
        help="Path to the CSV dataset.",
    )
    parser.add_argument(
        "target_column",
        help="Name of the target column.",
    )
    parser.add_argument(
        "metric",
        help="Metric to optimize (e.g. accuracy, rmse, f1).",
    )
    parser.add_argument(
        "--goal",
        default="",
        help="Human-readable description of the prediction goal.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to create the experiment in (default: experiment-{csv_stem}).",
    )
    parser.add_argument(
        "--time-budget",
        type=int,
        default=60,
        help="Time budget in seconds per experiment run (default: 60).",
    )

    if argv is not None and len(argv) == 0:
        parser.print_usage(sys.stderr)
        return 1

    args = parser.parse_args(argv)

    try:
        from automl.scaffold import scaffold_experiment

        project_dir = scaffold_experiment(
            data_path=args.data_path,
            target_column=args.target_column,
            metric=args.metric,
            goal=args.goal,
            output_dir=args.output_dir,
            time_budget=args.time_budget,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"\nExperiment scaffolded at: {project_dir.resolve()}\n")
    print("Next steps:")
    print(f"  cd {project_dir}")
    print("  uv run train.py          # Run baseline experiment")
    print("  claude                    # Start Claude Code for autonomous iteration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
