"""Tests for LiveProgress terminal display."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from mlforge.config import Config
from mlforge.progress import LiveProgress
from mlforge.state import SessionState


class TestLiveProgressRender:
    """Tests for _render() output content."""

    def _make(
        self, *, experiment_count: int = 0, best_metric: float | None = None,
        cost_spent_usd: float = 0.0, total_keeps: int = 0, total_reverts: int = 0,
        budget_experiments: int = 50, budget_usd: float = 5.0,
    ) -> LiveProgress:
        config = Config(budget_experiments=budget_experiments, budget_usd=budget_usd)
        state = SessionState(
            experiment_count=experiment_count,
            best_metric=best_metric,
            cost_spent_usd=cost_spent_usd,
            total_keeps=total_keeps,
            total_reverts=total_reverts,
        )
        return LiveProgress(config, state)

    def test_render_returns_table(self) -> None:
        from rich.table import Table
        lp = self._make()
        table = lp._render()
        assert isinstance(table, Table)

    def test_render_shows_experiment_count(self) -> None:
        lp = self._make(experiment_count=3, budget_experiments=50)
        text = self._table_text(lp._render())
        assert "3/50" in text

    def test_render_shows_na_when_best_metric_none(self) -> None:
        lp = self._make(best_metric=None)
        text = self._table_text(lp._render())
        assert "N/A" in text

    def test_render_shows_best_metric(self) -> None:
        lp = self._make(best_metric=0.9523)
        text = self._table_text(lp._render())
        assert "0.9523" in text

    def test_render_shows_cost_format(self) -> None:
        lp = self._make(cost_spent_usd=1.50, budget_usd=5.0)
        text = self._table_text(lp._render())
        assert "$1.50/$5.00" in text

    def test_render_shows_keeps_reverts(self) -> None:
        lp = self._make(total_keeps=7, total_reverts=3)
        text = self._table_text(lp._render())
        assert "7/3" in text

    def test_render_shows_status(self) -> None:
        lp = self._make()
        text = self._table_text(lp._render())
        assert "Running" in text

    @staticmethod
    def _table_text(table) -> str:
        """Extract text from a rich Table by rendering to string."""
        from io import StringIO

        from rich.console import Console
        buf = StringIO()
        console = Console(file=buf, width=120, no_color=True)
        console.print(table)
        return buf.getvalue()


class TestLiveProgressLifecycle:
    """Tests for start/stop lifecycle."""

    def test_start_creates_live(self) -> None:
        config = Config()
        state = SessionState()
        lp = LiveProgress(config, state)
        assert lp._live is None
        with patch("mlforge.progress.Live") as MockLive:
            lp.start()
            assert MockLive.called
            assert lp._live is not None

    def test_stop_clears_live(self) -> None:
        config = Config()
        state = SessionState()
        lp = LiveProgress(config, state)
        mock_live = MagicMock()
        lp._live = mock_live
        lp.stop()
        mock_live.stop.assert_called_once()
        assert lp._live is None

    def test_stop_safe_when_not_started(self) -> None:
        config = Config()
        state = SessionState()
        lp = LiveProgress(config, state)
        lp.stop()  # Should not raise

    def test_context_manager(self) -> None:
        config = Config()
        state = SessionState()
        lp = LiveProgress(config, state)
        with patch("mlforge.progress.Live"):
            with lp:
                assert lp._live is not None
            assert lp._live is None

    def test_update_changes_state(self) -> None:
        config = Config()
        state1 = SessionState(experiment_count=0)
        lp = LiveProgress(config, state1)
        mock_live = MagicMock()
        lp._live = mock_live
        state2 = SessionState(experiment_count=5)
        lp.update(state2)
        assert lp.state is state2
        mock_live.update.assert_called_once()
