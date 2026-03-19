"""Experiment journal with JSONL persistence.

Provides an append-only structured log of experiment results. Each entry
records hypothesis, outcome, metric, and git state. The JSONL format
survives context resets and supports both machine parsing and human-readable
markdown rendering.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class JournalEntry:
    """A single experiment journal entry.

    Attributes:
        experiment_id: Sequential experiment number.
        hypothesis: What change was tried and why.
        result: What happened (human-readable summary).
        metric_value: Observed metric value (or None if crashed).
        metric_delta: Change from previous best (or None).
        commit_hash: Git short hash if kept (or None if reverted/crashed).
        status: Outcome -- ``"keep"``, ``"revert"``, or ``"crash"``.
    """

    experiment_id: int
    hypothesis: str
    result: str
    metric_value: float | None
    metric_delta: float | None
    commit_hash: str | None
    status: str  # "keep" | "revert" | "crash"


def append_journal_entry(path: Path, entry: JournalEntry) -> None:
    """Append a journal entry as a single JSON line.

    Adds a UTC ISO timestamp automatically. Creates the file if it
    does not exist.

    Args:
        path: Path to the JSONL file (e.g., ``experiments.jsonl``).
        entry: The journal entry to append.
    """
    record = asdict(entry)
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def load_journal(path: Path) -> list[dict]:
    """Load all journal entries from a JSONL file.

    Args:
        path: Path to the JSONL file.

    Returns:
        List of entry dicts. Empty list if file does not exist.
        Blank lines are silently skipped.
    """
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped:
            entries.append(json.loads(stripped))
    return entries


def render_journal_markdown(entries: list[dict]) -> str:
    """Render journal entries as a human-readable markdown table.

    Args:
        entries: List of entry dicts (as returned by :func:`load_journal`).

    Returns:
        Markdown string with a table of experiments.
    """
    if not entries:
        return "*No experiments recorded yet.*\n"

    header = "| # | Status | Metric | Delta | Hypothesis | Commit |"
    separator = "|---|--------|--------|-------|------------|--------|"
    rows = [header, separator]

    for e in entries:
        exp_id = e.get("experiment_id", "?")
        status = e.get("status", "?")
        metric = e.get("metric_value")
        metric_str = f"{metric:.4f}" if metric is not None else "-"
        delta = e.get("metric_delta")
        delta_str = f"{delta:+.4f}" if delta is not None else "-"
        hypothesis = e.get("hypothesis", "")
        if len(hypothesis) > 60:
            hypothesis = hypothesis[:57] + "..."
        commit = e.get("commit_hash", "-") or "-"
        rows.append(f"| {exp_id} | {status} | {metric_str} | {delta_str} | {hypothesis} | {commit} |")

    return "\n".join(rows) + "\n"
