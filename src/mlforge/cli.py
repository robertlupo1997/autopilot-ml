"""CLI entry point for mlforge.

Parses command-line arguments, scaffolds the experiment directory, initializes
git, and runs the experiment engine loop.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from mlforge.checkpoint import load_checkpoint
from mlforge.config import Config
from mlforge.engine import RunEngine
from mlforge.git_ops import GitManager
from mlforge.scaffold import scaffold_experiment
from mlforge.state import SessionState


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments, scaffold, and run the experiment engine.

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

    # Generate run ID
    run_id = f"run-{int(time.time())}"

    # Determine output directory
    if args.output_dir:
        target_dir = Path(args.output_dir)
    else:
        target_dir = Path(f"mlforge-{dataset_path.stem}")

    try:
        if args.resume:
            # Resume: load checkpoint, skip scaffold and git init
            checkpoint_dir = target_dir / ".mlforge"
            state = load_checkpoint(checkpoint_dir)
            if state is None:
                print(
                    f"Error: no checkpoint found in {checkpoint_dir}",
                    file=sys.stderr,
                )
                return 1
            run_id = state.run_id or run_id
        else:
            # Fresh run: scaffold, then init git branch
            scaffold_experiment(
                config=config,
                dataset_path=dataset_path,
                target_dir=target_dir,
                run_id=run_id,
            )
            git = GitManager(target_dir)
            git.create_run_branch(run_id)
            git.close()

            state = SessionState(run_id=run_id, budget_remaining=config.budget_usd)

        # Run the experiment engine
        engine = RunEngine(target_dir, config, state)
        engine.run()

        # Print summary
        print(
            f"\nCompleted: {state.experiment_count} experiments, "
            f"best={state.best_metric}, "
            f"cost=${state.cost_spent_usd:.2f}"
        )
        return 0

    except KeyboardInterrupt:
        print("\nInterrupted, state saved")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
