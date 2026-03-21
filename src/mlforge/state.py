"""SessionState dataclass.

Tracks experiment session state across context resets.
Serialization is handled by checkpoint.py via dataclasses.asdict().
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SessionState:
    """Mutable state tracked across the experiment session."""

    experiment_count: int = 0
    best_metric: float | None = None
    best_commit: str | None = None
    budget_remaining: float = 0.0
    consecutive_reverts: int = 0
    total_keeps: int = 0
    total_reverts: int = 0
    run_id: str = ""
    cost_spent_usd: float = 0.0
    baselines: dict | None = None
    tried_families: list = field(default_factory=list)
    task: str = "classification"

