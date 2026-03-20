"""Run retrospective -- generates a markdown summary of the experiment session.

Produces a structured report with summary statistics, successful and failed
approaches, cost breakdown, and recommendations for future runs.
"""

from __future__ import annotations

from mlforge.config import Config
from mlforge.results import ResultsTracker
from mlforge.state import SessionState


def generate_retrospective(
    tracker: ResultsTracker, state: SessionState, config: Config
) -> str:
    """Generate a markdown retrospective report for the completed session.

    Args:
        tracker: Results tracker with experiment history.
        state: Final session state.
        config: Session configuration.

    Returns:
        Markdown string containing the full retrospective report.
    """
    summary = tracker.summary()
    keeps = tracker.get_by_status("keep")
    reverts = tracker.get_by_status("revert")

    lines: list[str] = []

    # Header
    lines.append("# mlforge Run Retrospective\n")

    # Summary table
    lines.append("## Summary\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Experiments | {summary['total_experiments']} |")
    lines.append(f"| Keeps | {summary['keeps']} |")
    lines.append(f"| Reverts | {summary['reverts']} |")
    lines.append(f"| Crashes | {summary['crashes']} |")
    best_display = f"{summary['best_metric']}" if summary["best_metric"] is not None else "N/A"
    lines.append(f"| Best {config.metric} | {best_display} |")
    lines.append(f"| Total Cost (USD) | {state.cost_spent_usd:.2f} |")
    lines.append("")

    # Successful approaches
    if keeps:
        lines.append("## Successful Approaches\n")
        for r in keeps:
            metric_str = f"{r.metric_value}" if r.metric_value is not None else "N/A"
            lines.append(
                f"- **Experiment {r.experiment_id}** ({config.metric}={metric_str}): "
                f"{r.description}"
            )
        lines.append("")

    # Failed approaches (limit to 10)
    if reverts:
        lines.append("## Failed Approaches\n")
        for r in reverts[:10]:
            lines.append(f"- **Experiment {r.experiment_id}**: {r.description}")
        if len(reverts) > 10:
            lines.append(f"- *...and {len(reverts) - 10} more*")
        lines.append("")

    # Recommendations
    lines.append("## Recommendations\n")
    if summary["keeps"] == 0:
        lines.append(
            "No improvements found. Consider different model families "
            "or feature engineering."
        )
    elif summary["reverts"] > summary["keeps"] * 3:
        lines.append(
            "High revert rate. Consider narrower search space or more budget."
        )
    else:
        best_hash = summary["best_commit"] or "unknown"
        lines.append(
            f"Best approach committed at {best_hash}. "
            "Consider longer budget for further improvement."
        )
    lines.append("")

    return "\n".join(lines)
