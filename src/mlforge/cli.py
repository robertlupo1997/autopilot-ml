"""CLI entry point for mlforge.

Parses command-line arguments and orchestrates experiment scaffolding.
The run engine is wired in a later plan.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mlforge.config import Config
from mlforge.scaffold import scaffold_experiment


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and scaffold an experiment directory.

    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:].
              If empty list, prints usage and returns 1.

    Returns:
        0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        prog="mlforge",
        description="Autonomous ML research framework",
    )
    parser.add_argument("dataset", help="Path to dataset (CSV or Parquet)")
    parser.add_argument("goal", help="What to predict or optimize")
    parser.add_argument("--domain", default="tabular", help="Plugin domain")
    parser.add_argument("--metric", default=None, help="Metric to optimize")
    parser.add_argument("--budget-minutes", type=int, default=None)
    parser.add_argument("--budget-usd", type=float, default=None)
    parser.add_argument("--budget-experiments", type=int, default=None)
    parser.add_argument("--output-dir", default=None, help="Experiment output directory")
    parser.add_argument("--resume", action="store_true", help="Resume a previous run")
    parser.add_argument("--model", default=None, help="Claude model to use")

    # Handle empty args
    if argv is not None and len(argv) == 0:
        parser.print_usage(sys.stderr)
        return 1

    args = parser.parse_args(argv)

    # Validate dataset exists
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Error: dataset '{args.dataset}' does not exist", file=sys.stderr)
        return 1

    # Build Config from defaults + CLI overrides
    config = Config(domain=args.domain)
    if args.metric is not None:
        config.metric = args.metric
    if args.budget_minutes is not None:
        config.budget_minutes = args.budget_minutes
    if args.budget_usd is not None:
        config.budget_usd = args.budget_usd
    if args.budget_experiments is not None:
        config.budget_experiments = args.budget_experiments
    if args.model is not None:
        config.model = args.model

    # Determine output directory
    if args.output_dir:
        target_dir = Path(args.output_dir)
    else:
        target_dir = Path(f"mlforge-{dataset_path.stem}")

    # Generate a run ID
    import time

    run_id = f"run-{int(time.time())}"

    # Scaffold the experiment directory
    scaffold_experiment(
        config=config,
        dataset_path=dataset_path,
        target_dir=target_dir,
        run_id=run_id,
    )

    print(f"Scaffolded experiment in {target_dir}")
    return 0
