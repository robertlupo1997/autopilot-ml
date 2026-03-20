"""Verification agent that re-runs holdout evaluation on the best swarm result.

Checks that the claimed metric from the scoreboard matches actual holdout
performance, catching metric inflation or evaluation bugs.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mlforge.swarm.scoreboard import SwarmScoreboard

TOLERANCE = 0.001


def verify_best_result(
    experiment_dir: Path,
    scoreboard: SwarmScoreboard,
    eval_script: str = "python train.py --eval-only",
) -> dict | None:
    """Re-run evaluation on the best swarm result and compare metrics.

    Args:
        experiment_dir: Root experiment directory.
        scoreboard: SwarmScoreboard to read best result from.
        eval_script: Command to run for evaluation (must output JSON with metric_value).

    Returns:
        Dict with claimed_metric, verified_metric, match, agent, commit.
        None if scoreboard has no results.
    """
    results = scoreboard.read_all()
    if not results:
        return None

    # Find best result
    if scoreboard.direction == "maximize":
        best = max(results, key=lambda r: float(r["metric_value"]))
    else:
        best = min(results, key=lambda r: float(r["metric_value"]))

    claimed_metric = float(best["metric_value"])
    agent = best["agent"]
    commit = best["commit"]

    # Checkout best commit in a temporary worktree
    verify_dir = experiment_dir / ".swarm" / "verify"
    try:
        _checkout_in_worktree(experiment_dir, commit, verify_dir)

        # Run evaluation
        proc = subprocess.run(
            eval_script.split(),
            cwd=str(verify_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if proc.returncode != 0:
            return {
                "claimed_metric": claimed_metric,
                "verified_metric": None,
                "match": False,
                "agent": agent,
                "commit": commit,
                "error": proc.stderr,
            }

        output = json.loads(proc.stdout)
        verified_metric = float(output["metric_value"])
        match = abs(claimed_metric - verified_metric) < TOLERANCE

        return {
            "claimed_metric": claimed_metric,
            "verified_metric": verified_metric,
            "match": match,
            "agent": agent,
            "commit": commit,
        }
    finally:
        _cleanup_worktree(experiment_dir, verify_dir)


def _checkout_in_worktree(
    experiment_dir: Path, commit: str, worktree_dir: Path
) -> None:
    """Create a temporary git worktree at the given commit."""
    subprocess.run(
        ["git", "worktree", "add", str(worktree_dir), commit],
        cwd=str(experiment_dir),
        capture_output=True,
        check=True,
    )


def _cleanup_worktree(experiment_dir: Path, worktree_dir: Path) -> None:
    """Remove a temporary git worktree."""
    try:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_dir)],
            cwd=str(experiment_dir),
            capture_output=True,
        )
    except Exception:
        pass
    try:
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=str(experiment_dir),
            capture_output=True,
        )
    except Exception:
        pass
