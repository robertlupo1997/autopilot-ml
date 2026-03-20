"""Tests for ResourceGuardrails, CostTracker, and DeviationHandler."""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import patch

import pytest

from mlforge.config import Config
from mlforge.guardrails import CostTracker, DeviationHandler, ResourceGuardrails
from mlforge.state import SessionState


# ---------------------------------------------------------------------------
# ResourceGuardrails
# ---------------------------------------------------------------------------


class TestResourceGuardrails:
    """Tests for ResourceGuardrails.should_stop and stop_reason."""

    def _make(
        self, tmp_path: Path, *, budget_experiments: int = 50, budget_usd: float = 5.0, budget_minutes: int = 60
    ) -> ResourceGuardrails:
        config = Config(
            budget_experiments=budget_experiments,
            budget_usd=budget_usd,
            budget_minutes=budget_minutes,
        )
        return ResourceGuardrails(config, tmp_path)

    def test_should_stop_false_when_all_budgets_have_room(self, tmp_path: Path) -> None:
        g = self._make(tmp_path)
        state = SessionState(experiment_count=0, cost_spent_usd=0.0)
        assert g.should_stop(state) is False

    def test_should_stop_true_when_experiment_count_exceeded(self, tmp_path: Path) -> None:
        g = self._make(tmp_path, budget_experiments=5)
        state = SessionState(experiment_count=5)
        assert g.should_stop(state) is True

    def test_should_stop_true_when_cost_exceeded(self, tmp_path: Path) -> None:
        g = self._make(tmp_path, budget_usd=2.0)
        state = SessionState(cost_spent_usd=2.5)
        assert g.should_stop(state) is True

    def test_should_stop_true_when_time_exceeded(self, tmp_path: Path) -> None:
        g = self._make(tmp_path, budget_minutes=1)
        state = SessionState()
        # Pretend 120 seconds have elapsed (budget is 60s)
        with patch("mlforge.guardrails.time") as mock_time:
            mock_time.time.return_value = g._start_time + 120
            assert g.should_stop(state) is True

    def test_should_stop_true_when_disk_low(self, tmp_path: Path) -> None:
        g = self._make(tmp_path)
        state = SessionState()
        # Mock disk_usage to report < 1 GB free
        fake_usage = type("Usage", (), {"free": 500 * 1024 * 1024})()  # 500 MB
        with patch("mlforge.guardrails.shutil.disk_usage", return_value=fake_usage):
            assert g.should_stop(state) is True

    def test_stop_reason_returns_none_when_ok(self, tmp_path: Path) -> None:
        g = self._make(tmp_path)
        state = SessionState()
        assert g.stop_reason(state) is None

    def test_stop_reason_returns_string_for_experiments(self, tmp_path: Path) -> None:
        g = self._make(tmp_path, budget_experiments=3)
        state = SessionState(experiment_count=3)
        reason = g.stop_reason(state)
        assert reason is not None
        assert "experiment" in reason.lower()

    def test_stop_reason_returns_string_for_cost(self, tmp_path: Path) -> None:
        g = self._make(tmp_path, budget_usd=1.0)
        state = SessionState(cost_spent_usd=1.5)
        reason = g.stop_reason(state)
        assert reason is not None
        assert "cost" in reason.lower()

    def test_stop_reason_returns_string_for_time(self, tmp_path: Path) -> None:
        g = self._make(tmp_path, budget_minutes=1)
        state = SessionState()
        with patch("mlforge.guardrails.time") as mock_time:
            mock_time.time.return_value = g._start_time + 120
            reason = g.stop_reason(state)
            assert reason is not None
            assert "time" in reason.lower()

    def test_stop_reason_returns_string_for_disk(self, tmp_path: Path) -> None:
        g = self._make(tmp_path)
        state = SessionState()
        fake_usage = type("Usage", (), {"free": 500 * 1024 * 1024})()
        with patch("mlforge.guardrails.shutil.disk_usage", return_value=fake_usage):
            reason = g.stop_reason(state)
            assert reason is not None
            assert "disk" in reason.lower()


# ---------------------------------------------------------------------------
# CostTracker
# ---------------------------------------------------------------------------


class TestCostTracker:
    """Tests for CostTracker accumulation and state update."""

    def test_record_adds_to_total(self) -> None:
        tracker = CostTracker()
        state = SessionState()
        tracker.record(0.50, state)
        tracker.record(0.25, state)
        assert tracker.total_cost == pytest.approx(0.75)

    def test_record_updates_session_state(self) -> None:
        tracker = CostTracker()
        state = SessionState()
        tracker.record(0.50, state)
        assert state.cost_spent_usd == pytest.approx(0.50)
        tracker.record(0.25, state)
        assert state.cost_spent_usd == pytest.approx(0.75)

    def test_per_experiment_costs_returns_list(self) -> None:
        tracker = CostTracker()
        state = SessionState()
        tracker.record(0.10, state)
        tracker.record(0.20, state)
        tracker.record(0.30, state)
        assert tracker.per_experiment_costs == [0.10, 0.20, 0.30]

    def test_initial_state(self) -> None:
        tracker = CostTracker()
        assert tracker.total_cost == 0.0
        assert tracker.per_experiment_costs == []


# ---------------------------------------------------------------------------
# DeviationHandler
# ---------------------------------------------------------------------------


class TestDeviationHandler:
    """Tests for DeviationHandler routing decisions."""

    def test_keep_on_improvement_maximize(self) -> None:
        handler = DeviationHandler(direction="maximize")
        state = SessionState(best_metric=0.8)
        result = {"status": "ok", "metric_value": 0.9}
        assert handler.handle(result, state) == "keep"

    def test_keep_on_improvement_minimize(self) -> None:
        handler = DeviationHandler(direction="minimize")
        state = SessionState(best_metric=0.5)
        result = {"status": "ok", "metric_value": 0.3}
        assert handler.handle(result, state) == "keep"

    def test_revert_when_no_improvement_maximize(self) -> None:
        handler = DeviationHandler(direction="maximize")
        state = SessionState(best_metric=0.9)
        result = {"status": "ok", "metric_value": 0.85}
        assert handler.handle(result, state) == "revert"

    def test_revert_when_no_improvement_minimize(self) -> None:
        handler = DeviationHandler(direction="minimize")
        state = SessionState(best_metric=0.3)
        result = {"status": "ok", "metric_value": 0.5}
        assert handler.handle(result, state) == "revert"

    def test_retry_on_oom_crash(self) -> None:
        handler = DeviationHandler(direction="maximize")
        state = SessionState()
        result = {"status": "crash", "error": "MemoryError: out of memory"}
        assert handler.handle(result, state) == "retry"

    def test_retry_on_oom_keyword(self) -> None:
        handler = DeviationHandler(direction="maximize")
        state = SessionState()
        result = {"status": "crash", "error": "CUDA OOM on device 0"}
        assert handler.handle(result, state) == "retry"

    def test_stop_when_oom_retries_exhausted(self) -> None:
        handler = DeviationHandler(direction="maximize")
        state = SessionState()
        oom_result = {"status": "crash", "error": "MemoryError"}
        # First retry
        assert handler.handle(oom_result, state) == "retry"
        # Second retry
        assert handler.handle(oom_result, state) == "retry"
        # Third time -> stop
        assert handler.handle(oom_result, state) == "stop"

    def test_revert_on_non_oom_crash(self) -> None:
        handler = DeviationHandler(direction="maximize")
        state = SessionState()
        result = {"status": "crash", "error": "ZeroDivisionError"}
        assert handler.handle(result, state) == "revert"

    def test_revert_on_timeout(self) -> None:
        handler = DeviationHandler(direction="maximize")
        state = SessionState()
        result = {"status": "timeout", "error": "Exceeded timeout"}
        assert handler.handle(result, state) == "revert"

    def test_revert_on_none_metric(self) -> None:
        handler = DeviationHandler(direction="maximize")
        state = SessionState(best_metric=0.8)
        result = {"status": "ok", "metric_value": None}
        assert handler.handle(result, state) == "revert"

    def test_revert_on_nan_metric(self) -> None:
        handler = DeviationHandler(direction="maximize")
        state = SessionState(best_metric=0.8)
        result = {"status": "ok", "metric_value": float("nan")}
        assert handler.handle(result, state) == "revert"

    def test_revert_on_inf_metric(self) -> None:
        handler = DeviationHandler(direction="maximize")
        state = SessionState(best_metric=0.8)
        result = {"status": "ok", "metric_value": float("inf")}
        assert handler.handle(result, state) == "revert"

    def test_keep_when_best_is_none(self) -> None:
        """Any finite metric is improvement when best_metric is None."""
        handler = DeviationHandler(direction="maximize")
        state = SessionState(best_metric=None)
        result = {"status": "ok", "metric_value": 0.5}
        assert handler.handle(result, state) == "keep"

    def test_retry_count_resets_on_keep(self) -> None:
        handler = DeviationHandler(direction="maximize")
        state = SessionState(best_metric=None)
        # Trigger one OOM retry
        oom_result = {"status": "crash", "error": "MemoryError"}
        handler.handle(oom_result, state)
        assert handler._retry_count == 1
        # Then a keep
        good_result = {"status": "ok", "metric_value": 0.9}
        handler.handle(good_result, state)
        assert handler._retry_count == 0


# ---------------------------------------------------------------------------
# SessionState.cost_spent_usd persistence
# ---------------------------------------------------------------------------


class TestSessionStateCost:
    """Tests for cost_spent_usd field in SessionState."""

    def test_cost_spent_usd_defaults_to_zero(self) -> None:
        state = SessionState()
        assert state.cost_spent_usd == 0.0

    def test_cost_spent_usd_round_trips_json(self, tmp_path: Path) -> None:
        state = SessionState(cost_spent_usd=3.75, experiment_count=10)
        path = tmp_path / "state.json"
        state.to_json(path)
        loaded = SessionState.from_json(path)
        assert loaded.cost_spent_usd == pytest.approx(3.75)
        assert loaded.experiment_count == 10
