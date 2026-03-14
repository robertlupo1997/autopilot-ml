"""Git state management via subprocess -- no GitPython dependency.

Handles experiment lifecycle: branch creation, commits, reverts, and .gitignore setup.
All operations use subprocess.run to call git directly.
"""

import os
import subprocess


class GitManager:
    """Manage git operations for experiment branches."""

    def __init__(self, repo_dir="."):
        self.repo_dir = repo_dir

    def _run(self, *args, check=True):
        """Run a git command via subprocess. Return CompletedProcess."""
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True,
            text=True,
            check=check,
            cwd=self.repo_dir,
        )
        return result

    def init_repo(self):
        """Initialize git repo and create .gitignore if not exists."""
        if not os.path.exists(os.path.join(self.repo_dir, ".git")):
            self._run("init")
        gitignore_path = os.path.join(self.repo_dir, ".gitignore")
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, "w") as f:
                f.write("results.tsv\nrun.log\n__pycache__/\n*.pyc\n")
            self._run("add", ".gitignore")
            self._run("commit", "-m", "Initial commit with .gitignore")

    def create_branch(self, tag):
        """Create and checkout experiment branch. Returns branch name."""
        branch = f"automl/run-{tag}"
        self._run("checkout", "-b", branch)
        return branch

    def commit(self, message, files=None):
        """Stage files and commit. Returns short hash."""
        files = files or ["train.py"]
        for f in files:
            self._run("add", f)
        self._run("commit", "-m", message)
        result = self._run("rev-parse", "--short", "HEAD")
        return result.stdout.strip()

    def revert(self):
        """Hard reset to last commit. Does NOT touch untracked/ignored files."""
        self._run("reset", "--hard", "HEAD")

    def revert_last_commit(self):
        """Hard reset to parent commit. Undoes the most recent commit.

        Use after 'commit then run' pattern: if the run fails, this
        reverts to the state before the commit.
        """
        self._run("reset", "--hard", "HEAD~1")

    def get_current_commit(self):
        """Return short hash of HEAD."""
        result = self._run("rev-parse", "--short", "HEAD")
        return result.stdout.strip()

    def create_worktree(self, path: str, branch: str) -> str:
        """Create a git worktree at path with a new branch.

        The created directory contains a .git file (pointer), not a directory.
        Requires the repo to have at least one commit (HEAD must exist).

        Args:
            path: Filesystem path for the new worktree.
            branch: Name of the new branch to create in the worktree.

        Returns:
            The branch name (same as the branch argument).

        Raises:
            subprocess.CalledProcessError: If git worktree add fails.
        """
        self._run("worktree", "add", path, "-b", branch)
        return branch

    def remove_worktree(self, path: str) -> None:
        """Remove a git worktree and its metadata.

        Uses --force to handle dirty worktrees (uncommitted changes).

        Args:
            path: Filesystem path of the worktree to remove.

        Raises:
            subprocess.CalledProcessError: If git worktree remove fails.
        """
        self._run("worktree", "remove", path, "--force")
