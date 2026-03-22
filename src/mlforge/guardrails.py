"""Resource guardrails, cost tracking, and deviation handling.

These are the safety nets for unattended overnight runs. ResourceGuardrails
enforces hard stops on cost, time, experiment count, and disk space.
CostTracker accumulates per-experiment costs. DeviationHandler routes
experiment outcomes to keep/revert/retry/stop actions.
"""

from __future__ import annotations

import logging
import math
import shutil
import time
from pathlib import Path

from mlforge.config import Config
from mlforge.state import SessionState

logger = logging.getLogger(__name__)


class ResourceGuardrails:
    """Hard stops for cost, time, experiments, and disk space.

    Checked before each experiment iteration. If any guardrail trips,
    the run engine should stop gracefully.
    """

    def __init__(self, config: Config, experiment_dir: Path) -> None:
        self.config = config
        self.experiment_dir = experiment_dir
        self._start_time = time.time()
        self.min_free_disk_gb = 1.0

    def should_stop(self, state: SessionState) -> bool:
        """Return True if any guardrail is tripped."""
        reason = self.stop_reason(state)
        if reason:
            logger.info("Guardrail tripped: %s", reason)
        return reason is not None

    def stop_reason(self, state: SessionState) -> str | None:
        """Return a human-readable reason if a guardrail tripped, else None."""
        if state.experiment_count >= self.config.budget_experiments:
            return (
                f"Experiment count limit reached: "
                f"{state.experiment_count}/{self.config.budget_experiments}"
            )
        if state.cost_spent_usd >= self.config.budget_usd:
            return (
                f"Cost cap reached: "
                f"${state.cost_spent_usd:.2f}/${self.config.budget_usd:.2f}"
            )
        elapsed = time.time() - self._start_time
        budget_seconds = self.config.budget_minutes * 60
        if elapsed >= budget_seconds:
            return (
                f"Time budget exceeded: "
                f"{elapsed / 60:.1f}min/{self.config.budget_minutes}min"
            )
        usage = shutil.disk_usage(self.experiment_dir)
        free_gb = usage.free / (1024**3)
        if free_gb < self.min_free_disk_gb:
            return f"Disk space low: {free_gb:.2f}GB free (min {self.min_free_disk_gb}GB)"
        return None


class CostTracker:
    """Accumulates per-experiment API costs and updates SessionState."""

    def __init__(self) -> None:
        self._costs: list[float] = []
        self._total: float = 0.0

    def record(self, cost_usd: float, state: SessionState) -> None:
        """Record a single experiment's cost and update state."""
        self._costs.append(cost_usd)
        self._total += cost_usd
        state.cost_spent_usd = self._total
        logger.debug("Cost: $%.4f this experiment, $%.2f total", cost_usd, self._total)

    @property
    def total_cost(self) -> float:
        """Running total cost in USD."""
        return self._total

    @property
    def per_experiment_costs(self) -> list[float]:
        """List of individual experiment costs."""
        return list(self._costs)

    def summary(self) -> dict:
        """Return a cost summary dict."""
        if not self._costs:
            return {"total": 0.0, "count": 0, "avg": 0.0, "min": 0.0, "max": 0.0}
        return {
            "total": self._total,
            "count": len(self._costs),
            "avg": self._total / len(self._costs),
            "min": min(self._costs),
            "max": max(self._costs),
        }


class DeviationHandler:
    """Routes experiment outcomes to keep/revert/retry/stop actions.

    - OOM crashes get retried up to MAX_RETRIES times
    - Non-OOM crashes and timeouts get reverted
    - Invalid metrics (None, NaN, inf) get reverted
    - Improvements get kept; non-improvements get reverted
    """

    MAX_RETRIES = 2

    def __init__(self, direction: str = "maximize") -> None:
        self.direction = direction
        self._retry_count = 0

    def handle(self, result: dict, state: SessionState) -> str:
        """Return action: 'keep', 'revert', 'retry', or 'stop'."""
        status = result.get("status", "ok")

        # 1. Crash handling
        if status == "crash":
            error = result.get("error", "")
            if "MemoryError" in error or "OOM" in error:
                self._retry_count += 1
                if self._retry_count > self.MAX_RETRIES:
                    return "stop"
                return "retry"
            return "revert"

        # 2. Timeout handling
        if status == "timeout":
            return "revert"

        # 3. Metric validation
        metric = result.get("metric_value")
        if metric is None or not math.isfinite(metric):
            return "revert"

        # 4. Improvement check
        if self._is_improvement(metric, state):
            self._retry_count = 0
            return "keep"

        return "revert"

    def _is_improvement(self, metric: float, state: SessionState) -> bool:
        """Check if metric improves over best, respecting direction."""
        if state.best_metric is None:
            return True
        if self.direction == "maximize":
            return metric > state.best_metric
        return metric < state.best_metric
