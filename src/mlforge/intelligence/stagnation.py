"""Branch-on-stagnation logic for escaping local optima.

When the agent hits N consecutive reverts, it branches from the best-ever
commit and tries a different model family.
"""

from __future__ import annotations

from mlforge.git_ops import GitManager
from mlforge.state import SessionState


def check_stagnation(state: SessionState, threshold: int = 3) -> bool:
    """Check whether the session has stagnated.

    Args:
        state: Current session state.
        threshold: Number of consecutive reverts that signals stagnation.

    Returns:
        True if consecutive_reverts >= threshold.
    """
    return state.consecutive_reverts >= threshold


def trigger_stagnation_branch(
    git_manager: GitManager,
    state: SessionState,
    new_family: str,
) -> str:
    """Create an exploration branch from the best-ever commit.

    Args:
        git_manager: GitManager for branch operations.
        state: Current session state (must have best_commit set).
        new_family: Algorithm family name for the new branch.

    Returns:
        The branch name created (``explore-{new_family}``).

    Raises:
        ValueError: If state.best_commit is None.
    """
    if state.best_commit is None:
        raise ValueError("Cannot branch: best_commit is None")

    # Checkout the best-ever commit (detached HEAD)
    git_manager.repo.git.checkout(state.best_commit)

    # Create and checkout the exploration branch
    branch_name = f"explore-{new_family}"
    git_manager.repo.create_head(branch_name).checkout()

    # Reset stagnation counter
    state.consecutive_reverts = 0

    return branch_name
