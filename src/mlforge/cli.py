"""CLI entry point for mlforge.

Parses command-line arguments, scaffolds the experiment directory, initializes
git, and runs the experiment engine loop. Supports simple mode (auto-detect
task/metric from data) and expert mode (custom CLAUDE.md, frozen/mutable files).
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import pandas as pd

from mlforge.checkpoint import load_checkpoint
from mlforge.config import Config
from mlforge.engine import RunEngine
from mlforge.git_ops import GitManager
from mlforge.profiler import profile_dataset
from mlforge.scaffold import scaffold_experiment
from mlforge.state import SessionState


def _extract_target_column(goal: str) -> str:
    """Extract target column name from a goal string.

    Supports patterns like "predict price", "predict the target", or just
    uses the last word as a fallback.

    Args:
        goal: The user's goal description.

    Returns:
        The extracted target column name.
    """
    # Try "predict X" pattern
    match = re.search(r"\bpredict\s+(?:the\s+)?(\w+)", goal, re.IGNORECASE)
    if match:
        return match.group(1)
    # Fallback: last word
    return goal.strip().split()[-1]


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
    # Expert mode flags
    parser.add_argument(
        "--custom-claude-md",
        type=Path,
        default=None,
        help="Path to custom CLAUDE.md template",
    )
    parser.add_argument(
        "--custom-frozen",
        nargs="+",
        default=None,
        help="Additional frozen files beyond plugin defaults",
    )
    parser.add_argument(
        "--custom-mutable",
        nargs="+",
        default=None,
        help="Additional mutable files beyond plugin defaults",
    )
    # Swarm mode flags
    parser.add_argument(
        "--swarm", action="store_true", help="Enable swarm mode with parallel agents"
    )
    parser.add_argument(
        "--n-agents", type=int, default=3, help="Number of swarm agents (default: 3)"
    )

    # Handle empty args
    if argv is not None and len(argv) == 0:
        parser.print_usage(sys.stderr)
        return 1

    args = parser.parse_args(argv)

    # Validate swarm + resume conflict
    if args.swarm and args.resume:
        print(
            "Error: --swarm and --resume cannot be used together",
            file=sys.stderr,
        )
        return 1
    if args.n_agents != 3 and not args.swarm:
        print(
            "Warning: --n-agents has no effect without --swarm",
            file=sys.stderr,
        )

    # Validate dataset exists
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Error: dataset '{args.dataset}' does not exist", file=sys.stderr)
        return 1

    # Build Config from defaults + CLI overrides
    config = Config(domain=args.domain)
    if args.budget_minutes is not None:
        config.budget_minutes = args.budget_minutes
    if args.budget_usd is not None:
        config.budget_usd = args.budget_usd
    if args.budget_experiments is not None:
        config.budget_experiments = args.budget_experiments
    if args.model is not None:
        config.model = args.model

    # Expert mode config fields
    if args.custom_claude_md is not None:
        config.custom_claude_md_path = args.custom_claude_md
    if args.custom_frozen is not None:
        config.custom_frozen = args.custom_frozen
    if args.custom_mutable is not None:
        config.custom_mutable = args.custom_mutable

    if args.metric is not None:
        # Expert mode: user specified metric, skip profiling
        config.metric = args.metric
    else:
        # Simple mode: auto-detect from dataset
        try:
            if str(dataset_path).endswith(".parquet"):
                df = pd.read_parquet(dataset_path)
            else:
                df = pd.read_csv(dataset_path)
            target_column = _extract_target_column(args.goal)
            if target_column in df.columns:
                profile = profile_dataset(df, target_column)
                config.metric = profile.metric
                config.direction = profile.direction
                config.plugin_settings["task"] = profile.task
                config.plugin_settings["csv_path"] = dataset_path.name
                config.plugin_settings["target_column"] = target_column
                if profile.date_columns:
                    config.plugin_settings["date_column"] = profile.date_columns[0]
                print(
                    f"Auto-detected: {profile.task} task, metric={profile.metric}, "
                    f"{profile.n_rows} rows, {profile.n_features} features"
                )
        except Exception:
            # If profiling fails, fall back to defaults silently
            pass

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

        if args.swarm:
            from mlforge.swarm import SwarmManager

            manager = SwarmManager(
                config=config, experiment_dir=target_dir, n_agents=args.n_agents
            )
            manager.setup()
            try:
                results = manager.run()
                print(
                    f"\nSwarm complete: {results['agents']} agents, "
                    f"best={results['best_score']} (agent {results['best_agent']})"
                )
                if results.get("verification"):
                    v = results["verification"]
                    status = "VERIFIED" if v.get("match") else "MISMATCH"
                    print(f"Verification: {status}")
            finally:
                manager.teardown()
            return 0

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
