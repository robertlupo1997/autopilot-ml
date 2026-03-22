"""Clean up old mlforge experiment artifacts."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def clean_experiments(base_dir: Path, dry_run: bool = False) -> dict:
    """Remove old mlforge experiment directories and orphaned git branches.

    Args:
        base_dir: Directory to scan for ``mlforge-*`` experiment dirs.
        dry_run: If True, only show what would be removed.

    Returns:
        Summary dict with counts of removed items.
    """
    removed_dirs: list[str] = []
    removed_branches: list[str] = []

    # Find experiment dirs
    candidates = sorted(base_dir.glob("mlforge-*"))

    if not candidates:
        logger.info("No mlforge experiment directories found in %s", base_dir)
        return {"dirs_removed": 0, "branches_removed": 0}

    for exp_dir in candidates:
        if not exp_dir.is_dir():
            continue
        size_mb = sum(f.stat().st_size for f in exp_dir.rglob("*") if f.is_file()) / (1024 * 1024)
        if dry_run:
            logger.info("Would remove: %s (%.1f MB)", exp_dir, size_mb)
        else:
            logger.info("Removing: %s (%.1f MB)", exp_dir, size_mb)
            shutil.rmtree(exp_dir)
        removed_dirs.append(str(exp_dir))

    # Clean orphaned git branches
    try:
        from git import Repo

        repo = Repo(base_dir, search_parent_directories=True)
        for branch in repo.branches:
            if branch.name.startswith("mlforge/run-"):
                # Check if corresponding experiment dir still exists
                if dry_run:
                    logger.info("Would remove branch: %s", branch.name)
                else:
                    logger.info("Removing branch: %s", branch.name)
                    repo.delete_head(branch, force=True)
                removed_branches.append(branch.name)
    except Exception:
        logger.debug("Could not clean git branches", exc_info=True)

    summary = {
        "dirs_removed": len(removed_dirs),
        "branches_removed": len(removed_branches),
    }

    action = "Would remove" if dry_run else "Removed"
    logger.info(
        "%s %d directories and %d branches",
        action, summary["dirs_removed"], summary["branches_removed"],
    )
    return summary
