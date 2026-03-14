"""Unit tests for SwarmScoreboard -- file-locked cross-agent results TSV."""

import threading
import time
from pathlib import Path

import pytest

from automl.swarm_scoreboard import SwarmScoreboard, HEADER


class TestPublishResult:
    def test_creates_header_on_first_publish(self, tmp_path):
        """Header row written when scoreboard.tsv does not exist."""
        sb = SwarmScoreboard(tmp_path)
        sb.publish_result("agent-0", "abc1234", 0.85, 12.5, "keep", "LogisticRegression")
        lines = (tmp_path / "scoreboard.tsv").read_text().splitlines()
        assert lines[0] == HEADER.strip()

    def test_appends_row(self, tmp_path):
        """publish_result appends a TSV row with all fields."""
        sb = SwarmScoreboard(tmp_path)
        sb.publish_result("agent-0", "abc1234", 0.85, 12.5, "keep", "LogisticRegression")
        lines = (tmp_path / "scoreboard.tsv").read_text().splitlines()
        assert len(lines) == 2  # header + 1 row
        parts = lines[1].split("\t")
        assert parts[0] == "agent-0"
        assert parts[1] == "abc1234"
        assert float(parts[2]) == pytest.approx(0.85, abs=1e-5)
        assert float(parts[3]) == pytest.approx(12.5, abs=0.05)
        assert parts[4] == "keep"
        assert parts[5] == "LogisticRegression"
        assert len(parts) == 7  # 7 columns including timestamp

    def test_returns_true_for_new_best_keep(self, tmp_path):
        """Returns True when status=keep and metric exceeds current best."""
        sb = SwarmScoreboard(tmp_path)
        result = sb.publish_result("agent-0", "abc1234", 0.85, 12.5, "keep", "LogisticRegression")
        assert result is True

    def test_returns_false_for_non_improving_keep(self, tmp_path):
        """Returns False when status=keep but metric does NOT exceed current best."""
        sb = SwarmScoreboard(tmp_path)
        sb.publish_result("agent-0", "abc1234", 0.90, 12.5, "keep", "LogisticRegression")
        result = sb.publish_result("agent-1", "def5678", 0.85, 11.0, "keep", "RandomForest")
        assert result is False

    def test_returns_false_for_discard(self, tmp_path):
        """Returns False when status=discard regardless of metric."""
        sb = SwarmScoreboard(tmp_path)
        result = sb.publish_result("agent-0", "abc1234", 0.99, 12.5, "discard", "bad run")
        assert result is False

    def test_copies_best_train_py_when_new_best(self, tmp_path):
        """Copies train_py_source to best_train.py when is_new_best=True."""
        sb = SwarmScoreboard(tmp_path)
        source = "# best train script\nprint('hello')\n"
        is_best = sb.publish_result(
            "agent-0", "abc1234", 0.85, 12.5, "keep", "LogisticRegression",
            train_py_source=source,
        )
        assert is_best is True
        assert (tmp_path / "best_train.py").read_text() == source

    def test_does_not_copy_best_train_py_for_discard(self, tmp_path):
        """Does not copy best_train.py for discard status."""
        sb = SwarmScoreboard(tmp_path)
        sb.publish_result(
            "agent-0", "abc1234", 0.99, 12.5, "discard", "bad run",
            train_py_source="# bad script",
        )
        assert not (tmp_path / "best_train.py").exists()

    def test_multiple_rows_appended(self, tmp_path):
        """Multiple publish_result calls append rows correctly."""
        sb = SwarmScoreboard(tmp_path)
        sb.publish_result("agent-0", "abc1234", 0.80, 10.0, "keep", "exp1")
        sb.publish_result("agent-0", "def5678", 0.90, 11.0, "keep", "exp2")
        sb.publish_result("agent-1", "ghi9012", 0.70, 9.0, "discard", "exp3")
        lines = (tmp_path / "scoreboard.tsv").read_text().splitlines()
        assert len(lines) == 4  # header + 3 rows


class TestReadBest:
    def test_returns_none_none_when_no_scoreboard(self, tmp_path):
        """Returns (None, None) when scoreboard.tsv does not exist."""
        sb = SwarmScoreboard(tmp_path)
        score, agent = sb.read_best()
        assert score is None
        assert agent is None

    def test_returns_best_keep_entry(self, tmp_path):
        """Returns (score, agent_id) of highest 'keep' entry."""
        sb = SwarmScoreboard(tmp_path)
        sb.publish_result("agent-0", "abc1234", 0.85, 10.0, "keep", "exp1")
        score, agent = sb.read_best()
        assert score == pytest.approx(0.85, abs=1e-5)
        assert agent == "agent-0"

    def test_ignores_discard_entries(self, tmp_path):
        """read_best ignores discard entries."""
        sb = SwarmScoreboard(tmp_path)
        sb.publish_result("agent-0", "abc1234", 0.99, 10.0, "discard", "bad")
        score, agent = sb.read_best()
        assert score is None
        assert agent is None

    def test_ignores_crash_entries(self, tmp_path):
        """read_best ignores crash entries."""
        sb = SwarmScoreboard(tmp_path)
        sb.publish_result("agent-0", "abc1234", 0.99, 10.0, "crash", "crash")
        score, agent = sb.read_best()
        assert score is None
        assert agent is None

    def test_returns_highest_keep_across_agents(self, tmp_path):
        """Returns the highest 'keep' score among multiple agents."""
        sb = SwarmScoreboard(tmp_path)
        sb.publish_result("agent-0", "abc1234", 0.75, 10.0, "keep", "exp1")
        sb.publish_result("agent-1", "def5678", 0.92, 11.0, "keep", "exp2")
        sb.publish_result("agent-2", "ghi9012", 0.88, 12.0, "keep", "exp3")
        score, agent = sb.read_best()
        assert score == pytest.approx(0.92, abs=1e-5)
        assert agent == "agent-1"

    def test_mixed_statuses_returns_best_keep(self, tmp_path):
        """Mixed statuses: only 'keep' entries considered."""
        sb = SwarmScoreboard(tmp_path)
        sb.publish_result("agent-0", "abc1234", 0.99, 10.0, "discard", "bad")
        sb.publish_result("agent-0", "def5678", 0.80, 11.0, "keep", "good")
        sb.publish_result("agent-1", "ghi9012", 0.95, 12.0, "crash", "crash")
        score, agent = sb.read_best()
        assert score == pytest.approx(0.80, abs=1e-5)
        assert agent == "agent-0"


class TestConcurrentWrites:
    def test_concurrent_writes_no_corruption(self, tmp_path):
        """5 threads each publishing 10 results: 50 data rows, no corruption."""
        sb = SwarmScoreboard(tmp_path)
        n_threads = 5
        results_per_thread = 10

        def worker(agent_id: int):
            for i in range(results_per_thread):
                sb.publish_result(
                    f"agent-{agent_id}",
                    f"commit{agent_id}{i:02d}",
                    float(agent_id) * 0.1 + i * 0.01,
                    float(i),
                    "keep",
                    f"experiment-{agent_id}-{i}",
                )

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lines = (tmp_path / "scoreboard.tsv").read_text().splitlines()
        # 1 header + 50 data rows
        assert len(lines) == n_threads * results_per_thread + 1
        # Verify header is intact
        assert lines[0] == HEADER.strip()
        # Verify every data row has exactly 7 tab-separated fields
        for line in lines[1:]:
            parts = line.split("\t")
            assert len(parts) == 7, f"Corrupted line: {line!r}"
