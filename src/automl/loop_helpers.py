"""Loop orchestration helpers: keep/revert decisions, stagnation, crash detection.

Called by the Claude Code agent during the autonomous loop to make
keep/revert decisions and detect stuck states (stagnation, repeated crashes).
"""

from __future__ import annotations

from dataclasses import dataclass, field

STRATEGY_CATEGORIES: list[str] = [
    "hyperparameter_tuning",
    "algorithm_switch",
    "ensemble_methods",
    "feature_preprocessing",
    "regularization_tuning",
]


@dataclass
class LoopState:
    """Mutable state tracked across loop iterations."""

    best_score: float | None = None
    best_commit: str | None = None
    consecutive_reverts: int = 0
    consecutive_crashes: int = 0
    last_crash_error: str | None = None
    total_experiments: int = 0
    total_keeps: int = 0
    total_reverts: int = 0
    total_crashes: int = 0
    strategy_categories_tried: list[str] = field(default_factory=list)
    stagnation_threshold: int = 5
    crash_threshold: int = 3


def should_keep(new_score: float, best_score: float | None) -> bool:
    """Return True if new_score is an improvement over best_score.

    First experiment (best_score is None) is always kept.
    Uses strict greater-than: equal is NOT an improvement.
    All metrics use sklearn convention (higher = better).
    """
    if best_score is None:
        return True
    return new_score > best_score


def is_stagnating(state: LoopState) -> bool:
    """Return True if consecutive reverts have reached the stagnation threshold."""
    return state.consecutive_reverts >= state.stagnation_threshold


def is_crash_stuck(state: LoopState) -> bool:
    """Return True if consecutive crashes have reached the crash threshold."""
    return state.consecutive_crashes >= state.crash_threshold


def suggest_strategy_shift(state: LoopState) -> str:
    """Return the first untried strategy category, cycling if all tried."""
    for category in STRATEGY_CATEGORIES:
        if category not in state.strategy_categories_tried:
            return category
    # All tried -- cycle back to the first
    return STRATEGY_CATEGORIES[0]
