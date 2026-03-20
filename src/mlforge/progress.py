"""Live terminal progress display using rich.

Shows experiment count, best metric, cost, and keeps/reverts in a
continuously-updating table. Used by the run engine to provide
visibility during unattended overnight runs.
"""

from __future__ import annotations

from rich.live import Live
from rich.table import Table

from mlforge.config import Config
from mlforge.state import SessionState


class LiveProgress:
    """Live-updating terminal display of experiment session status.

    Usage as context manager::

        with LiveProgress(config, state) as progress:
            # run experiments
            progress.update(state)
    """

    def __init__(self, config: Config, state: SessionState) -> None:
        self.config = config
        self.state = state
        self._live: Live | None = None

    def start(self) -> None:
        """Create and start the rich Live display."""
        self._live = Live(self._render(), refresh_per_second=1)
        self._live.start()

    def stop(self) -> None:
        """Stop the Live display safely."""
        if self._live is not None:
            try:
                self._live.stop()
            finally:
                self._live = None

    def update(self, state: SessionState) -> None:
        """Update the displayed state."""
        self.state = state
        if self._live is not None:
            self._live.update(self._render())

    def _render(self) -> Table:
        """Build a rich Table with current session status."""
        table = Table(title="mlforge")
        table.add_column("Field")
        table.add_column("Value")

        table.add_row(
            "Experiment",
            f"{self.state.experiment_count}/{self.config.budget_experiments}",
        )

        best = self.state.best_metric
        table.add_row("Best Metric", "N/A" if best is None else str(best))

        table.add_row(
            "Cost",
            f"${self.state.cost_spent_usd:.2f}/${self.config.budget_usd:.2f}",
        )

        table.add_row(
            "Keeps/Reverts",
            f"{self.state.total_keeps}/{self.state.total_reverts}",
        )

        table.add_row("Status", "Running")

        return table

    def __enter__(self) -> LiveProgress:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()
