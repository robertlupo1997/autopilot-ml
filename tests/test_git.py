"""Integration tests for GitManager -- git state management via subprocess."""

import os
import re
import subprocess

import pytest

from automl.git_ops import GitManager


@pytest.fixture
def git_repo(tmp_path):
    """Create a temp git repo with an initial commit so HEAD exists."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    # Create an initial commit so HEAD exists
    readme = tmp_path / "README.md"
    readme.write_text("init")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial commit"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    return tmp_path


class TestCreateBranch:
    def test_create_branch(self, git_repo):
        gm = GitManager(repo_dir=str(git_repo))
        branch = gm.create_branch("test-run")
        assert branch == "automl/run-test-run"
        # Verify branch is checked out
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=git_repo, capture_output=True, text=True,
        )
        assert result.stdout.strip() == "automl/run-test-run"


class TestCommit:
    def test_commit(self, git_repo):
        gm = GitManager(repo_dir=str(git_repo))
        # Create a file to commit
        test_file = git_repo / "test.txt"
        test_file.write_text("hello")
        short_hash = gm.commit("test message", files=["test.txt"])
        # short hash is 7+ hex chars
        assert re.match(r"^[0-9a-f]{7,}$", short_hash)


class TestRevert:
    def test_revert(self, git_repo):
        gm = GitManager(repo_dir=str(git_repo))
        # Create and commit a file
        test_file = git_repo / "tracked.txt"
        test_file.write_text("original content")
        gm.commit("add tracked file", files=["tracked.txt"])
        # Modify the file
        test_file.write_text("modified content")
        assert test_file.read_text() == "modified content"
        # Revert
        gm.revert()
        assert test_file.read_text() == "original content"

    def test_revert_preserves_untracked_gitignored(self, git_repo):
        gm = GitManager(repo_dir=str(git_repo))
        # Set up gitignore
        gm.init_repo()
        # Create results.tsv (should be gitignored)
        results = git_repo / "results.tsv"
        results.write_text("some data")
        # Create and commit a tracked file
        tracked = git_repo / "tracked.txt"
        tracked.write_text("original")
        gm.commit("add tracked", files=["tracked.txt"])
        # Modify tracked and revert
        tracked.write_text("modified")
        gm.revert()
        # results.tsv should still exist (not deleted by revert)
        assert results.exists()
        assert results.read_text() == "some data"


class TestGitignore:
    def test_gitignore(self, git_repo):
        gm = GitManager(repo_dir=str(git_repo))
        gm.init_repo()
        gitignore = git_repo / ".gitignore"
        content = gitignore.read_text()
        assert "results.tsv" in content
        assert "run.log" in content
        assert "__pycache__/" in content
        assert "*.pyc" in content


class TestGetCurrentCommit:
    def test_get_current_commit(self, git_repo):
        gm = GitManager(repo_dir=str(git_repo))
        commit_hash = gm.get_current_commit()
        assert re.match(r"^[0-9a-f]{7,}$", commit_hash)


class TestRevertLastCommit:
    def test_revert_last_commit(self, git_repo):
        """After commit + revert_last_commit, HEAD is back at pre-commit state."""
        gm = GitManager(repo_dir=str(git_repo))
        # Create and commit first file
        file_a = git_repo / "a.txt"
        file_a.write_text("first version")
        gm.commit("first commit", files=["a.txt"])
        first_hash = gm.get_current_commit()

        # Create and commit second change
        file_a.write_text("second version")
        gm.commit("second commit", files=["a.txt"])
        second_hash = gm.get_current_commit()
        assert first_hash != second_hash

        # Revert the last commit
        gm.revert_last_commit()

        # HEAD should be back at first commit
        assert gm.get_current_commit() == first_hash
        # File content should match first commit
        assert file_a.read_text() == "first version"


class TestNoGitPython:
    def test_no_gitpython(self):
        """Verify git_ops.py does not import GitPython (GIT-05)."""
        import automl.git_ops as mod
        source_path = mod.__file__
        with open(source_path) as f:
            source = f.read()
        # Should not have "import git" (but "import git_ops" style is OK)
        lines = source.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Check for "import git" but not "import git_ops"
            if "import git" in stripped and "git_ops" not in stripped:
                assert False, f"Found GitPython import: {stripped}"


class TestSubprocessUsed:
    def test_subprocess_used(self):
        """Verify git_ops.py uses subprocess.run for git commands."""
        import automl.git_ops as mod
        source_path = mod.__file__
        with open(source_path) as f:
            source = f.read()
        assert "subprocess.run" in source
        assert re.search(r'subprocess\.run.*git', source)


class TestWorktree:
    def test_create_worktree(self, git_repo):
        """create_worktree returns branch name and creates worktree directory."""
        gm = GitManager(repo_dir=str(git_repo))
        wt_path = str(git_repo / "worktree-1")
        branch = gm.create_worktree(wt_path, "test-branch")
        assert branch == "test-branch"
        assert (git_repo / "worktree-1" / ".git").exists()

    def test_remove_worktree(self, git_repo):
        """remove_worktree removes the worktree directory and git metadata."""
        gm = GitManager(repo_dir=str(git_repo))
        wt_path = str(git_repo / "worktree-1")
        gm.create_worktree(wt_path, "test-branch")
        gm.remove_worktree(wt_path)
        assert not (git_repo / "worktree-1").exists()

    def test_worktree_has_git_file_not_dir(self, git_repo):
        """Worktree .git is a file (pointer), not a directory."""
        gm = GitManager(repo_dir=str(git_repo))
        wt_path = str(git_repo / "worktree-1")
        gm.create_worktree(wt_path, "test-branch")
        git_path = git_repo / "worktree-1" / ".git"
        assert git_path.is_file()  # .git is a file (pointer), not a directory
