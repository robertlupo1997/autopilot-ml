"""Show status of past mlforge experiment runs."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def show_status(base_dir: Path) -> list[dict]:
    """Scan for mlforge experiment directories and display their status.

    Args:
        base_dir: Directory to scan for ``mlforge-*`` experiment dirs.

    Returns:
        List of dicts with run info (for programmatic use / testing).
    """
    runs: list[dict] = []

    # Find experiment dirs: look for mlforge-* dirs and dirs containing .mlforge/
    candidates = sorted(base_dir.glob("mlforge-*"))
    if (base_dir / ".mlforge").is_dir():
        candidates.insert(0, base_dir)

    for exp_dir in candidates:
        checkpoint_path = exp_dir / ".mlforge" / "checkpoint.json"
        if not checkpoint_path.exists():
            continue

        try:
            data = json.loads(checkpoint_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        run_info = {
            "directory": str(exp_dir),
            "run_id": data.get("run_id", "unknown"),
            "experiments": data.get("experiment_count", 0),
            "best_metric": data.get("best_metric"),
            "cost_usd": data.get("cost_spent_usd", 0.0),
            "keeps": data.get("total_keeps", 0),
            "reverts": data.get("total_reverts", 0),
        }
        runs.append(run_info)

    if not runs:
        logger.info("No mlforge experiment runs found in %s", base_dir)
        return runs

    # Display as a simple table
    header = f"{'Directory':<40} {'Run ID':<20} {'Exp':>5} {'Best':>10} {'Cost':>8} {'K/R':>6}"
    logger.info(header)
    logger.info("-" * len(header))
    for r in runs:
        best = f"{r['best_metric']:.4f}" if r["best_metric"] is not None else "N/A"
        logger.info(
            "%-40s %-20s %5d %10s %8s %3d/%-3d",
            r["directory"][:40], r["run_id"][:20],
            r["experiments"], best, f"${r['cost_usd']:.2f}",
            r["keeps"], r["reverts"],
        )

    return runs
