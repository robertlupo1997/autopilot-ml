"""Tests for mlforge.git_ops -- GitManager wrapping GitPython."""

import pytest
from pathlib import Path
from git import Repo


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with an initial commit."""
    repo = Repo.init(tmp_path)
    # Configure git user for commits
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    # Create initial commit so HEAD exists
    initial_file = tmp_path / "README.md"
    initial_file.write_text("# Test Repo\n")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    repo.close()
    return tmp_path


class TestCreateRunBranch:
    def test_create_run_branch(self, git_repo: Path) -> None:
        from mlforge.git_ops import GitManager

        with GitManager(git_repo) as gm:
            branch_name = gm.create_run_branch("abc123")
            assert branch_name == "mlforge/run-abc123"
            assert gm.repo.active_branch.name == "mlforge/run-abc123"

    def test_create_run_branch_duplicate_raises(self, git_repo: Path) -> None:
        from mlforge.git_ops import GitManager

        with GitManager(git_repo) as gm:
            gm.create_run_branch("dup")
            with pytest.raises(ValueError, match="already exists"):
                gm.create_run_branch("dup")


class TestCommitExperiment:
    def test_commit_experiment(self, git_repo: Path) -> None:
        from mlforge.git_ops import GitManager

        with GitManager(git_repo) as gm:
            # Create a file to commit
            test_file = git_repo / "model.py"
            test_file.write_text("# model code\n")
            short_hash = gm.commit_experiment("Add model", ["model.py"])
            assert len(short_hash) == 8
            # Verify file is committed
            assert "model.py" in [
                item.path for item in gm.repo.head.commit.tree.traverse()
            ]

    def test_commit_no_changes_raises(self, git_repo: Path) -> None:
        from mlforge.git_ops import GitManager

        with GitManager(git_repo) as gm:
            # Stage an already-committed file with no modifications
            with pytest.raises(ValueError, match="[Nn]othing to commit"):
                gm.commit_experiment("Empty commit", ["README.md"])


class TestRevert:
    def test_revert_to_last_commit(self, git_repo: Path) -> None:
        from mlforge.git_ops import GitManager

        with GitManager(git_repo) as gm:
            readme = git_repo / "README.md"
            original = readme.read_text()
            # Modify file
            readme.write_text("Modified content\n")
            assert readme.read_text() != original
            # Revert
            gm.revert_to_last_commit()
            assert readme.read_text() == original

    def test_revert_stays_on_branch(self, git_repo: Path) -> None:
        from mlforge.git_ops import GitManager

        with GitManager(git_repo) as gm:
            gm.create_run_branch("test-revert")
            readme = git_repo / "README.md"
            readme.write_text("Modified\n")
            gm.revert_to_last_commit()
            assert not gm.repo.head.is_detached


class TestTagBest:
    def test_tag_best(self, git_repo: Path) -> None:
        from mlforge.git_ops import GitManager

        with GitManager(git_repo) as gm:
            gm.tag_best("best-v1", "Best model v1")
            assert "best-v1" in [t.name for t in gm.repo.tags]
            assert gm.repo.tags["best-v1"].commit == gm.repo.head.commit

    def test_tag_duplicate_raises(self, git_repo: Path) -> None:
        from mlforge.git_ops import GitManager

        with GitManager(git_repo) as gm:
            gm.tag_best("dup-tag")
            with pytest.raises(ValueError, match="already exists"):
                gm.tag_best("dup-tag")


class TestContextManager:
    def test_context_manager(self, git_repo: Path) -> None:
        from mlforge.git_ops import GitManager

        with GitManager(git_repo) as gm:
            assert gm.repo is not None
            branch = gm.create_run_branch("ctx-test")
            assert branch == "mlforge/run-ctx-test"
        # After exit, should not raise (close was called)
