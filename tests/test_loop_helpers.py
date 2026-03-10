"""Tests for loop orchestration helpers: keep/revert decisions, stagnation, crash detection."""

import pytest

from automl.loop_helpers import (
    STRATEGY_CATEGORIES,
    LoopState,
    is_crash_stuck,
    is_stagnating,
    should_keep,
    suggest_strategy_shift,
)


class TestShouldKeep:
    def test_first_experiment_none_best(self):
        """should_keep returns True when best_score is None (first experiment)."""
        assert should_keep(5.0, None) is True

    def test_improvement(self):
        """should_keep returns True when new_score > best_score."""
        assert should_keep(0.85, 0.80) is True

    def test_regression(self):
        """should_keep returns False when new_score < best_score."""
        assert should_keep(0.80, 0.85) is False

    def test_equal_not_improvement(self):
        """should_keep returns False when new_score == best_score (strict >)."""
        assert should_keep(0.85, 0.85) is False


class TestLoopStateDefaults:
    def test_defaults(self):
        """LoopState has sensible defaults."""
        state = LoopState()
        assert state.best_score is None
        assert state.best_commit is None
        assert state.consecutive_reverts == 0
        assert state.consecutive_crashes == 0
        assert state.last_crash_error is None
        assert state.total_experiments == 0
        assert state.total_keeps == 0
        assert state.total_reverts == 0
        assert state.total_crashes == 0
        assert state.strategy_categories_tried == []
        assert state.stagnation_threshold == 5
        assert state.crash_threshold == 3


class TestIsStagnating:
    def test_at_threshold(self):
        """Stagnation detected at exactly stagnation_threshold consecutive reverts."""
        state = LoopState(consecutive_reverts=5)
        assert is_stagnating(state) is True

    def test_above_threshold(self):
        """Stagnation detected above threshold."""
        state = LoopState(consecutive_reverts=10)
        assert is_stagnating(state) is True

    def test_below_threshold(self):
        """No stagnation below threshold."""
        state = LoopState(consecutive_reverts=4)
        assert is_stagnating(state) is False

    def test_zero_reverts(self):
        """No stagnation with zero reverts."""
        state = LoopState(consecutive_reverts=0)
        assert is_stagnating(state) is False


class TestIsCrashStuck:
    def test_at_threshold(self):
        """Crash stuck detected at exactly crash_threshold consecutive crashes."""
        state = LoopState(consecutive_crashes=3)
        assert is_crash_stuck(state) is True

    def test_above_threshold(self):
        """Crash stuck detected above threshold."""
        state = LoopState(consecutive_crashes=5)
        assert is_crash_stuck(state) is True

    def test_below_threshold(self):
        """No crash stuck below threshold."""
        state = LoopState(consecutive_crashes=2)
        assert is_crash_stuck(state) is False

    def test_zero_crashes(self):
        """No crash stuck with zero crashes."""
        state = LoopState(consecutive_crashes=0)
        assert is_crash_stuck(state) is False


class TestSuggestStrategyShift:
    def test_returns_first_untried(self):
        """Returns the first untried category."""
        state = LoopState(strategy_categories_tried=[])
        result = suggest_strategy_shift(state)
        assert result == STRATEGY_CATEGORIES[0]

    def test_skips_tried_categories(self):
        """Returns first untried category, skipping tried ones."""
        state = LoopState(
            strategy_categories_tried=[STRATEGY_CATEGORIES[0], STRATEGY_CATEGORIES[1]]
        )
        result = suggest_strategy_shift(state)
        assert result == STRATEGY_CATEGORIES[2]

    def test_cycles_when_all_tried(self):
        """Cycles back to first category when all have been tried."""
        state = LoopState(strategy_categories_tried=list(STRATEGY_CATEGORIES))
        result = suggest_strategy_shift(state)
        assert result == STRATEGY_CATEGORIES[0]


class TestStrategyCategories:
    def test_categories_exist(self):
        """STRATEGY_CATEGORIES has the expected entries."""
        assert len(STRATEGY_CATEGORIES) == 5
        assert "hyperparameter_tuning" in STRATEGY_CATEGORIES
        assert "algorithm_switch" in STRATEGY_CATEGORIES
        assert "ensemble_methods" in STRATEGY_CATEGORIES
        assert "feature_preprocessing" in STRATEGY_CATEGORIES
        assert "regularization_tuning" in STRATEGY_CATEGORIES
