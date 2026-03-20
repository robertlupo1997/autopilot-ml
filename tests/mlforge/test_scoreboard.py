"""Tests for SwarmScoreboard -- file-locked TSV scoreboard for cross-agent coordination."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from mlforge.swarm.scoreboard import SwarmScoreboard


class TestScoreboardCreation:
    """Test scoreboard file creation and initialization."""

    def test_creates_tsv_with_header_on_first_publish(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv")
        sb.publish_result("agent-0", "abc123", 0.85, 10.0, "keep", "Ridge baseline")
        content = (tmp_path / "scoreboard.tsv").read_text()
        lines = content.strip().split("\n")
        assert lines[0].startswith("agent\t")
        assert len(lines) == 2  # header + 1 row

    def test_lock_file_created_alongside_scoreboard(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv")
        sb.publish_result("agent-0", "abc123", 0.85, 10.0, "keep", "Ridge baseline")
        assert (tmp_path / "scoreboard.lock").exists()


class TestPublishResult:
    """Test publish_result() behavior for maximize and minimize directions."""

    def test_returns_true_if_new_global_best_maximize(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv", direction="maximize")
        assert sb.publish_result("agent-0", "abc", 0.85, 10.0, "keep", "first") is True
        assert sb.publish_result("agent-1", "def", 0.90, 12.0, "keep", "better") is True

    def test_returns_false_if_not_new_global_best_maximize(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv", direction="maximize")
        sb.publish_result("agent-0", "abc", 0.90, 10.0, "keep", "best")
        assert sb.publish_result("agent-1", "def", 0.80, 12.0, "keep", "worse") is False

    def test_returns_true_if_new_global_best_minimize(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv", direction="minimize")
        assert sb.publish_result("agent-0", "abc", 0.50, 10.0, "keep", "first") is True
        assert sb.publish_result("agent-1", "def", 0.30, 12.0, "keep", "better") is True

    def test_returns_false_if_not_new_global_best_minimize(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv", direction="minimize")
        sb.publish_result("agent-0", "abc", 0.30, 10.0, "keep", "best")
        assert sb.publish_result("agent-1", "def", 0.50, 12.0, "keep", "worse") is False


class TestReadBest:
    """Test read_best() lockless read behavior."""

    def test_returns_none_if_empty(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv")
        best_score, best_agent = sb.read_best()
        assert best_score is None
        assert best_agent is None

    def test_returns_best_score_and_agent_maximize(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv", direction="maximize")
        sb.publish_result("agent-0", "abc", 0.80, 10.0, "keep", "ok")
        sb.publish_result("agent-1", "def", 0.95, 12.0, "keep", "great")
        sb.publish_result("agent-2", "ghi", 0.85, 14.0, "keep", "meh")
        best_score, best_agent = sb.read_best()
        assert best_score == pytest.approx(0.95)
        assert best_agent == "agent-1"

    def test_returns_best_score_and_agent_minimize(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv", direction="minimize")
        sb.publish_result("agent-0", "abc", 0.50, 10.0, "keep", "ok")
        sb.publish_result("agent-1", "def", 0.20, 12.0, "keep", "great")
        sb.publish_result("agent-2", "ghi", 0.35, 14.0, "keep", "meh")
        best_score, best_agent = sb.read_best()
        assert best_score == pytest.approx(0.20)
        assert best_agent == "agent-1"


class TestReadAll:
    """Test read_all() lockless read behavior."""

    def test_returns_list_of_dicts(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv")
        sb.publish_result("agent-0", "abc", 0.85, 10.0, "keep", "Ridge baseline")
        sb.publish_result("agent-1", "def", 0.90, 12.0, "keep", "XGBoost")
        results = sb.read_all()
        assert len(results) == 2
        assert results[0]["agent"] == "agent-0"
        assert results[1]["agent"] == "agent-1"
        assert float(results[0]["metric_value"]) == pytest.approx(0.85)

    def test_returns_empty_list_when_no_file(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv")
        assert sb.read_all() == []


class TestConcurrentWrites:
    """Test thread-safety of concurrent writes."""

    def test_concurrent_writes_no_corruption(self, tmp_path: Path) -> None:
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv", direction="maximize")
        n_threads = 5
        n_per_thread = 10
        errors: list[Exception] = []

        def writer(agent_id: int) -> None:
            try:
                for i in range(n_per_thread):
                    sb.publish_result(
                        f"agent-{agent_id}",
                        f"commit-{agent_id}-{i}",
                        float(agent_id * 100 + i),
                        1.0,
                        "keep",
                        f"result {i}",
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        results = sb.read_all()
        assert len(results) == n_threads * n_per_thread  # 50 total rows

    def test_scoreboard_append_only(self, tmp_path: Path) -> None:
        """Scoreboard file survives crash (append-only, no rewrite)."""
        sb = SwarmScoreboard(tmp_path / "scoreboard.tsv")
        sb.publish_result("agent-0", "abc", 0.85, 10.0, "keep", "first")
        size_after_first = (tmp_path / "scoreboard.tsv").stat().st_size
        sb.publish_result("agent-1", "def", 0.90, 12.0, "keep", "second")
        size_after_second = (tmp_path / "scoreboard.tsv").stat().st_size
        # File grew (append), never shrank (no rewrite)
        assert size_after_second > size_after_first
