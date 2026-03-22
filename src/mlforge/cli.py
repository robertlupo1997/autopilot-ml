"""CLI entry point for mlforge.

Supports subcommands (run, status, clean) and backward-compatible positional
usage: ``mlforge data.csv "predict churn"`` is equivalent to
``mlforge run data.csv "predict churn"``.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path

import pandas as pd

from mlforge import __version__
from mlforge.checkpoint import load_checkpoint
from mlforge.config import Config
from mlforge.engine import RunEngine
from mlforge.git_ops import GitManager
from mlforge.logging_config import setup_logging
from mlforge.profiler import profile_dataset
from mlforge.scaffold import scaffold_experiment
from mlforge.state import SessionState


def _extract_target_column(goal: str) -> str:
    """Extract target column name from a goal string.

    Supports patterns like "predict price", "predict the target", or just
    uses the last word as a fallback.
    """
    match = re.search(r"\bpredict\s+(?:the\s+)?(\w+)", goal, re.IGNORECASE)
    if match:
        return match.group(1)
    return goal.strip().split()[-1]


def _add_run_args(parser: argparse.ArgumentParser) -> None:
    """Add run-subcommand arguments to a parser."""
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
    parser.add_argument(
        "--custom-claude-md", type=Path, default=None,
        help="Path to custom CLAUDE.md template",
    )
    parser.add_argument(
        "--custom-frozen", nargs="+", default=None,
        help="Additional frozen files beyond plugin defaults",
    )
    parser.add_argument(
        "--custom-mutable", nargs="+", default=None,
        help="Additional mutable files beyond plugin defaults",
    )
    parser.add_argument(
        "--swarm", action="store_true", help="Enable swarm mode with parallel agents",
    )
    parser.add_argument(
        "--n-agents", type=int, default=3, help="Number of swarm agents (default: 3)",
    )
    parser.add_argument(
        "--enable-drafts", action="store_true",
        help="Enable multi-draft initial exploration (3-5 diverse solutions)",
    )
    parser.add_argument(
        "--model-name", type=str, default=None,
        help="HuggingFace model name for fine-tuning domain",
    )
    parser.add_argument(
        "--direction", choices=["minimize", "maximize"], default=None,
        help="Metric optimization direction override",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Profile dataset and show plan without executing",
    )
    parser.add_argument(
        "--notify", default=None,
        help="Notification on completion: 'desktop' or 'webhook:<url>'",
    )


def _build_config(args: argparse.Namespace, dataset_path: Path, logger: logging.Logger) -> Config:
    """Build a Config from CLI args and optional dataset profiling."""
    config = Config(domain=args.domain)
    if args.budget_minutes is not None:
        config.budget_minutes = args.budget_minutes
    if args.budget_usd is not None:
        config.budget_usd = args.budget_usd
    if args.budget_experiments is not None:
        config.budget_experiments = args.budget_experiments
    if args.model is not None:
        config.model = args.model
    if args.custom_claude_md is not None:
        config.custom_claude_md_path = args.custom_claude_md
    if args.custom_frozen is not None:
        config.custom_frozen = args.custom_frozen
    if args.custom_mutable is not None:
        config.custom_mutable = args.custom_mutable
    if args.enable_drafts:
        config.enable_drafts = True
    if args.direction is not None:
        config.direction = args.direction

    config.plugin_settings["dataset_path"] = dataset_path.name
    if args.model_name is not None:
        config.plugin_settings["model_name"] = args.model_name

    if args.metric is not None:
        config.metric = args.metric
    else:
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
                logger.info(
                    "Auto-detected: %s task, metric=%s", profile.task, profile.metric,
                )
                logger.info(
                    "  Rows: %d, Features: %d, Numeric: %d, Categorical: %d, Missing: %.1f%%",
                    profile.n_rows, profile.n_features,
                    len(profile.numeric_features), len(profile.categorical_features),
                    profile.missing_pct,
                )
                if profile.leakage_warnings:
                    for warning in profile.leakage_warnings:
                        logger.warning("Leakage: %s", warning)
        except Exception:
            logger.debug("Profiling failed, using defaults", exc_info=True)

    return config


def _cmd_run(args: argparse.Namespace) -> int:
    """Execute the 'run' subcommand."""
    logger = logging.getLogger("mlforge.cli")

    # Validate swarm + resume conflict
    if args.swarm and args.resume:
        logger.error("--swarm and --resume cannot be used together")
        return 1
    if args.n_agents != 3 and not args.swarm:
        logger.warning("--n-agents has no effect without --swarm")

    # Validate dataset exists
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        logger.error("dataset '%s' does not exist", args.dataset)
        return 1

    config = _build_config(args, dataset_path, logger)

    # GPU check for DL/FT domains
    from mlforge.gpu import check_gpu_for_domain
    check_gpu_for_domain(config.domain)

    # Generate run ID
    run_id = f"run-{int(time.time())}"

    # Determine output directory
    if args.output_dir:
        target_dir = Path(args.output_dir)
    else:
        target_dir = Path(f"mlforge-{dataset_path.stem}")

    # Dry-run: show plan and exit
    if args.dry_run:
        logger.info("Dry run -- plan for: %s", dataset_path)
        logger.info("  Domain: %s", config.domain)
        logger.info("  Metric: %s (%s)", config.metric, config.direction)
        logger.info("  Budget: %d min / $%.2f / %d experiments",
                     config.budget_minutes, config.budget_usd, config.budget_experiments)
        logger.info("  Output: %s", target_dir)
        logger.info("  Branch: mlforge/%s", run_id)
        if args.swarm:
            logger.info("  Swarm: %d agents", args.n_agents)
        if args.enable_drafts:
            logger.info("  Drafts: enabled")
        logger.info("Dry run complete. Remove --dry-run to execute.")
        return 0

    # Add file handler now that we know the output directory
    setup_logging(log_dir=target_dir / ".mlforge", verbose=getattr(args, "verbose", False))

    try:
        if args.resume:
            checkpoint_dir = target_dir / ".mlforge"
            state = load_checkpoint(checkpoint_dir)
            if state is None:
                logger.error("no checkpoint found in %s", checkpoint_dir)
                return 1
            run_id = state.run_id or run_id
        else:
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
                config=config, experiment_dir=target_dir, n_agents=args.n_agents,
            )
            manager.setup()
            try:
                results = manager.run()
                logger.info(
                    "Swarm complete: %d agents, best=%s (agent %s)",
                    results["agents"], results["best_score"], results["best_agent"],
                )
                if results.get("verification"):
                    v = results["verification"]
                    status = "VERIFIED" if v.get("match") else "MISMATCH"
                    logger.info("Verification: %s", status)
            finally:
                manager.teardown()
            return 0

        engine = RunEngine(target_dir, config, state)
        engine.run()

        summary = (
            f"Completed: {state.experiment_count} experiments, "
            f"best={state.best_metric}, cost=${state.cost_spent_usd:.2f}"
        )
        logger.info(summary)

        if getattr(args, "notify", None):
            from mlforge.notify import send_notification
            send_notification("mlforge run complete", summary, args.notify)

        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted, state saved")
        return 0
    except FileNotFoundError as exc:
        logger.error("File not found: %s", exc.filename or exc)
        logger.debug("Full traceback:", exc_info=True)
        return 1
    except PermissionError as exc:
        logger.error("Permission denied: %s. Check file permissions.", exc.filename or exc)
        logger.debug("Full traceback:", exc_info=True)
        return 1
    except ValueError as exc:
        logger.error("%s", exc)
        logger.debug("Full traceback:", exc_info=True)
        return 1
    except Exception as exc:
        error_msg = str(exc)
        if "claude" in error_msg.lower() and (
            "not found" in error_msg.lower() or "No such file" in error_msg.lower()
        ):
            logger.error(
                "Claude Code CLI not found. Install it from "
                "https://docs.anthropic.com/en/docs/claude-code"
            )
        else:
            logger.error("%s", exc)
        logger.debug("Full traceback:", exc_info=True)
        return 1


def _cmd_status(args: argparse.Namespace) -> int:
    """Execute the 'status' subcommand."""
    from mlforge.status import show_status

    base_dir = Path(args.dir) if args.dir else Path(".")
    show_status(base_dir)
    return 0


def _cmd_clean(args: argparse.Namespace) -> int:
    """Execute the 'clean' subcommand."""
    from mlforge.clean import clean_experiments

    base_dir = Path(args.dir) if args.dir else Path(".")
    clean_experiments(base_dir, dry_run=args.dry_run)
    return 0


_SUBCOMMANDS = {"run", "status", "clean"}


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and dispatch to the appropriate subcommand.

    Backward compatible: ``mlforge data.csv "goal"`` is treated as
    ``mlforge run data.csv "goal"``.
    """
    parser = argparse.ArgumentParser(
        prog="mlforge",
        description="Autonomous ML research framework",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose (DEBUG-level) console logging",
    )

    subparsers = parser.add_subparsers(dest="command")

    # 'run' subcommand
    run_parser = subparsers.add_parser("run", help="Run experiments")
    _add_run_args(run_parser)
    run_parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose (DEBUG-level) console logging",
    )

    # 'status' subcommand
    status_parser = subparsers.add_parser("status", help="Show past experiment runs")
    status_parser.add_argument(
        "--dir", default=None, help="Base directory to scan (default: current dir)",
    )

    # 'clean' subcommand
    clean_parser = subparsers.add_parser("clean", help="Clean up old experiment artifacts")
    clean_parser.add_argument(
        "--dir", default=None, help="Base directory to clean (default: current dir)",
    )
    clean_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be removed without deleting",
    )

    # Handle empty args
    if argv is not None and len(argv) == 0:
        parser.print_usage(sys.stderr)
        return 1

    # Backward compatibility: if first arg is not a subcommand and looks like
    # a file path or doesn't start with '-', insert 'run' as the subcommand
    effective_argv = argv if argv is not None else sys.argv[1:]
    if effective_argv and effective_argv[0] not in _SUBCOMMANDS and not effective_argv[0].startswith("-"):
        effective_argv = ["run", *effective_argv]

    args = parser.parse_args(effective_argv)

    # Set up logging
    setup_logging(verbose=getattr(args, "verbose", False))

    if args.command == "run" or (args.command is None and hasattr(args, "dataset")):
        return _cmd_run(args)
    elif args.command == "status":
        return _cmd_status(args)
    elif args.command == "clean":
        return _cmd_clean(args)
    else:
        parser.print_usage(sys.stderr)
        return 1
