"""Tests for mlforge.journal -- JSONL experiment journal."""

import json
import pytest
from datetime import datetime
from pathlib import Path


@pytest.fixture
def journal_path(tmp_path: Path) -> Path:
    """Return path to a temporary journal file."""
    return tmp_path / "experiments.jsonl"


def _make_entry(experiment_id: int = 1, **overrides):
    """Helper to create a JournalEntry with defaults."""
    from mlforge.journal import JournalEntry

    defaults = dict(
        experiment_id=experiment_id,
        hypothesis="Try XGBoost with depth=3",
        result="Accuracy improved by 2%",
        metric_value=0.85,
        metric_delta=0.02,
        commit_hash="abc12345",
        status="keep",
    )
    defaults.update(overrides)
    return JournalEntry(**defaults)


class TestAppendAndLoad:
    def test_append_and_load_single_entry(self, journal_path: Path) -> None:
        from mlforge.journal import append_journal_entry, load_journal

        entry = _make_entry(experiment_id=1)
        append_journal_entry(journal_path, entry)
        entries = load_journal(journal_path)
        assert len(entries) == 1
        assert entries[0]["experiment_id"] == 1
        assert entries[0]["hypothesis"] == "Try XGBoost with depth=3"
        assert entries[0]["status"] == "keep"

    def test_append_multiple_entries(self, journal_path: Path) -> None:
        from mlforge.journal import append_journal_entry, load_journal

        for i in range(1, 4):
            entry = _make_entry(experiment_id=i)
            append_journal_entry(journal_path, entry)
        entries = load_journal(journal_path)
        assert len(entries) == 3
        assert [e["experiment_id"] for e in entries] == [1, 2, 3]


class TestLoadEdgeCases:
    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        from mlforge.journal import load_journal

        result = load_journal(tmp_path / "nonexistent.jsonl")
        assert result == []

    def test_load_skips_blank_lines(self, journal_path: Path) -> None:
        from mlforge.journal import load_journal

        # Write JSONL with blank lines interspersed
        line = json.dumps({"experiment_id": 1, "hypothesis": "test"})
        journal_path.write_text(f"{line}\n\n{line}\n\n")
        entries = load_journal(journal_path)
        assert len(entries) == 2


class TestEntryFields:
    def test_entry_has_timestamp(self, journal_path: Path) -> None:
        from mlforge.journal import append_journal_entry, load_journal

        entry = _make_entry()
        append_journal_entry(journal_path, entry)
        entries = load_journal(journal_path)
        ts = entries[0]["timestamp"]
        # Should be valid ISO format
        parsed = datetime.fromisoformat(ts)
        assert parsed.year >= 2026

    def test_entry_has_all_fields(self, journal_path: Path) -> None:
        from mlforge.journal import append_journal_entry, load_journal

        entry = _make_entry()
        append_journal_entry(journal_path, entry)
        entries = load_journal(journal_path)
        expected_fields = {
            "experiment_id", "timestamp", "hypothesis", "result",
            "metric_value", "metric_delta", "commit_hash", "status",
        }
        assert expected_fields.issubset(set(entries[0].keys()))


class TestJournalEntry:
    def test_journal_entry_dataclass(self) -> None:
        from mlforge.journal import JournalEntry

        entry = JournalEntry(
            experiment_id=5,
            hypothesis="Try Ridge regression",
            result="Improved",
            metric_value=0.92,
            metric_delta=0.03,
            commit_hash="def45678",
            status="keep",
        )
        assert entry.experiment_id == 5
        assert entry.status == "keep"
        assert entry.metric_value == 0.92


class TestRenderMarkdown:
    def test_render_markdown(self, journal_path: Path) -> None:
        from mlforge.journal import append_journal_entry, load_journal, render_journal_markdown

        for i in range(1, 3):
            entry = _make_entry(experiment_id=i, hypothesis=f"Hypothesis {i}")
            append_journal_entry(journal_path, entry)

        entries = load_journal(journal_path)
        md = render_journal_markdown(entries)
        # Should contain a table with experiment IDs
        assert "| 1 " in md or "|1|" in md or "| 1|" in md
        assert "| 2 " in md or "|2|" in md or "| 2|" in md
        # Should have column headers
        assert "Status" in md
        assert "Metric" in md
        assert "Hypothesis" in md
