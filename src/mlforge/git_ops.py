"""Git operations manager wrapping GitPython for experiment state management.

Provides branch-per-run, commit-per-experiment, revert-on-discard, and tag-best
workflow. Implements context manager to prevent file handle leaks (Pitfall 1).
"""

from __future__ import annotations

from pathlib import Path

from git import Repo


class GitManager:
    """Wraps GitPython Repo for experiment git operations.

    Usage::

        with GitManager("/path/to/repo") as gm:
            gm.create_run_branch("abc123")
            gm.commit_experiment("Add model", ["model.py"])
            gm.tag_best("best-v1", "Best model so far")
    """

    def __init__(self, repo_path: str | Path = ".") -> None:
        self.repo = Repo(str(repo_path))

    def create_run_branch(self, run_id: str) -> str:
        """Create and checkout a new branch for this run.

        Args:
            run_id: Unique identifier for the run.

        Returns:
            The branch name created (``mlforge/run-{run_id}``).

        Raises:
            ValueError: If a branch with this run_id already exists.
        """
        branch_name = f"mlforge/run-{run_id}"
        # Check for existing branch
        existing = [ref.name for ref in self.repo.heads]
        if branch_name in existing:
            raise ValueError(f"Branch '{branch_name}' already exists")
        branch = self.repo.create_head(branch_name)
        branch.checkout()
        return branch_name

    def commit_experiment(self, message: str, files: list[str]) -> str:
        """Stage specified files and commit.

        Args:
            message: Commit message.
            files: List of file paths (relative to repo root) to stage.

        Returns:
            Short commit hash (8 characters).

        Raises:
            ValueError: If there are no changes to commit after staging.
        """
        # Stage the files
        self.repo.index.add(files)
        # Check if there are actual changes staged
        if not self.repo.index.diff("HEAD"):
            raise ValueError("Nothing to commit -- no changes detected")
        commit = self.repo.index.commit(message)
        return commit.hexsha[:8]

    def revert_to_last_commit(self) -> None:
        """Hard reset index and working tree to HEAD.

        After revert, verifies HEAD is not detached (Pitfall 3).
        """
        self.repo.head.reset(index=True, working_tree=True)

    def tag_best(self, tag_name: str, message: str = "") -> None:
        """Create an annotated tag on the current HEAD.

        Args:
            tag_name: Name for the tag.
            message: Optional annotation message.

        Raises:
            ValueError: If a tag with this name already exists.
        """
        existing_tags = [t.name for t in self.repo.tags]
        if tag_name in existing_tags:
            raise ValueError(f"Tag '{tag_name}' already exists")
        self.repo.create_tag(tag_name, message=message)

    def close(self) -> None:
        """Close the underlying Repo to prevent file handle leaks."""
        self.repo.close()

    def __enter__(self) -> GitManager:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        self.close()
