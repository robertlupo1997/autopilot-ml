"""Tests for stagnation detection and branch-on-stagnation."""

from __future__ import annotations

from pathlib import Path

import pytest
from git import Repo

from mlforge.intelligence.stagnation import check_stagnation, trigger_stagnation_branch
from mlforge.git_ops import GitManager
from mlforge.state import SessionState


@pytest.fixture
def git_repo(tmp_path: Path) -> Repo:
    """Create a temporary git repo with an initial commit."""
    repo = Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    # Initial commit
    readme = tmp_path / "README.md"
    readme.write_text("init")
    repo.index.add(["README.md"])
    repo.index.commit("initial commit")
    return repo


class TestCheckStagnation:
    def test_below_threshold(self):
        state = SessionState(consecutive_reverts=2)
        assert check_stagnation(state) is False

    def test_at_threshold(self):
        state = SessionState(consecutive_reverts=3)
        assert check_stagnation(state) is True

    def test_above_threshold(self):
        state = SessionState(consecutive_reverts=5)
        assert check_stagnation(state) is True

    def test_custom_threshold(self):
        state = SessionState(consecutive_reverts=2)
        assert check_stagnation(state, threshold=2) is True
        assert check_stagnation(state, threshold=3) is False


class TestTriggerStagnationBranch:
    def test_creates_branch(self, git_repo: Repo):
        best_commit = git_repo.head.commit.hexsha
        state = SessionState(
            consecutive_reverts=3,
            best_commit=best_commit,
        )
        gm = GitManager(git_repo.working_dir)
        try:
            branch_name = trigger_stagnation_branch(gm, state, "xgboost")
            assert branch_name == "explore-xgboost"
            assert git_repo.active_branch.name == "explore-xgboost"
        finally:
            gm.close()

    def test_resets_counter(self, git_repo: Repo):
        best_commit = git_repo.head.commit.hexsha
        state = SessionState(
            consecutive_reverts=5,
            best_commit=best_commit,
        )
        gm = GitManager(git_repo.working_dir)
        try:
            trigger_stagnation_branch(gm, state, "lightgbm")
            assert state.consecutive_reverts == 0
        finally:
            gm.close()

    def test_no_best_commit_raises(self, git_repo: Repo):
        state = SessionState(consecutive_reverts=3, best_commit=None)
        gm = GitManager(git_repo.working_dir)
        try:
            with pytest.raises(ValueError, match="best_commit"):
                trigger_stagnation_branch(gm, state, "svm")
        finally:
            gm.close()
