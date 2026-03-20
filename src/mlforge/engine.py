"""Run engine -- orchestrates the autonomous experiment loop.

Spawns fresh ``claude -p`` sessions per experiment, processes results through
deviation handling, makes keep/revert decisions, and stops when guardrails trip.
This is the heart of mlforge -- the loop that runs overnight.
"""

from __future__ import annotations

import json
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from mlforge.checkpoint import save_checkpoint
from mlforge.config import Config
from mlforge.export import export_artifact
from mlforge.git_ops import GitManager
from mlforge.guardrails import CostTracker, DeviationHandler, ResourceGuardrails
from mlforge.progress import LiveProgress
from mlforge.results import ExperimentResult, ResultsTracker
from mlforge.retrospective import generate_retrospective
from mlforge.state import SessionState


class RunEngine:
    """Orchestrates the experiment loop.

    For each iteration: save checkpoint, spawn ``claude -p``, process result
    (keep/revert/retry/stop), update state, check guardrails.

    Args:
        experiment_dir: Path to the scaffolded experiment directory.
        config: Session configuration.
        state: Mutable session state.
    """

    def __init__(
        self, experiment_dir: Path, config: Config, state: SessionState
    ) -> None:
        self.experiment_dir = experiment_dir
        self.config = config
        self.state = state
        self.git = GitManager(experiment_dir)
        self.guardrails = ResourceGuardrails(config, experiment_dir)
        self.cost_tracker = CostTracker()
        self.deviation = DeviationHandler(config.direction)
        self.progress = LiveProgress(config, state)
        self._checkpoint_dir = experiment_dir / ".mlforge"
        self._journal_path = experiment_dir / "experiments.md"
        self._results_path = experiment_dir / "results.jsonl"
        self.results_tracker = ResultsTracker(self._results_path)
        self._stop_requested = False

    def run(self) -> None:
        """Execute the experiment loop until guardrails trip or stop requested.

        Saves checkpoint before each iteration and in the finally block.
        Uses LiveProgress as a context manager for terminal display.
        Registers SIGINT handler for graceful shutdown.
        """
        prev_handler = signal.getsignal(signal.SIGINT)

        def _handle_sigint(signum: int, frame: object) -> None:
            self._stop_requested = True

        signal.signal(signal.SIGINT, _handle_sigint)

        try:
            with self.progress:
                try:
                    while (
                        not self.guardrails.should_stop(self.state)
                        and not self._stop_requested
                    ):
                        save_checkpoint(self.state, self._checkpoint_dir)
                        result = self._run_one_experiment()
                        action = self._process_result(result)
                        self.state.experiment_count += 1
                        self.progress.update(self.state)
                        if action == "stop":
                            break
                finally:
                    save_checkpoint(self.state, self._checkpoint_dir)

                    # Post-loop: export artifact and generate retrospective
                    artifact_dir = export_artifact(
                        self.experiment_dir, self.state, self.config
                    )
                    if artifact_dir:
                        self.progress.log(f"Model exported to {artifact_dir}")

                    retrospective = generate_retrospective(
                        self.results_tracker, self.state, self.config
                    )
                    retro_path = self.experiment_dir / "RETROSPECTIVE.md"
                    retro_path.write_text(retrospective)
                    self.progress.log(f"Retrospective written to {retro_path}")

                    self.git.close()
        finally:
            signal.signal(signal.SIGINT, prev_handler)

    def _run_one_experiment(self, oom_hint: bool = False) -> dict:
        """Spawn a single ``claude -p`` session and return parsed JSON.

        Args:
            oom_hint: If True, prepend OOM avoidance hint to the prompt.

        Returns:
            Parsed JSON dict from claude stdout. On failure, returns a dict
            with ``status`` set to ``"crash"`` or ``"timeout"``.
        """
        prompt = self._build_prompt()
        if oom_hint:
            prompt = (
                "IMPORTANT: The previous attempt ran out of memory. "
                "Use smaller batch sizes or simpler models.\n\n" + prompt
            )

        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--dangerously-skip-permissions",
            "--max-turns", str(self.config.max_turns_per_experiment),
            "--max-budget-usd", str(self.config.per_experiment_budget_usd),
            "--append-system-prompt-file", "CLAUDE.md",
        ]

        if self.config.model is not None:
            cmd.extend(["--model", self.config.model])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.per_experiment_timeout_sec,
                cwd=str(self.experiment_dir),
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout"}

        if proc.returncode != 0:
            return {"status": "crash", "error": proc.stderr or proc.stdout}

        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"status": "crash", "error": "Invalid JSON output"}

    def _process_result(self, result: dict) -> str:
        """Route an experiment result through deviation handling.

        Records cost, then delegates to DeviationHandler for the action.
        On keep: commits, updates best metric/commit, resets consecutive reverts.
        On revert: hard-resets working tree, increments revert counters.
        On retry: re-runs the experiment with OOM hint.
        On stop: returns "stop" to break the loop.

        Args:
            result: Parsed JSON dict from ``_run_one_experiment``.

        Returns:
            Action string: ``"keep"``, ``"revert"``, ``"retry"``, or ``"stop"``.
        """
        # Track cost
        cost = result.get("total_cost_usd", 0.0)
        self.cost_tracker.record(cost, self.state)

        # Extract metric from nested result string if present
        result_for_handler = dict(result)
        if "result" in result and isinstance(result["result"], str):
            try:
                inner = json.loads(result["result"])
                if "metric_value" in inner:
                    result_for_handler["metric_value"] = inner["metric_value"]
            except (json.JSONDecodeError, TypeError):
                pass

        action = self.deviation.handle(result_for_handler, self.state)
        exp_id = self.state.experiment_count + 1
        metric_value = result_for_handler.get("metric_value")

        if action == "keep":
            commit_hash = self.git.commit_experiment(
                f"experiment-{exp_id}: improvement",
                ["."],
            )
            self.state.best_metric = metric_value
            self.state.best_commit = commit_hash
            self.state.total_keeps += 1
            self.state.consecutive_reverts = 0
            self._record_result(exp_id, "keep", metric_value, commit_hash)
            return "keep"

        if action == "revert":
            self.git.revert_to_last_commit()
            self.state.total_reverts += 1
            self.state.consecutive_reverts += 1
            self._record_result(exp_id, "revert", metric_value, None)
            return "revert"

        if action == "retry":
            return self._process_result(self._run_one_experiment(oom_hint=True))

        # action == "stop"
        self._record_result(exp_id, "crash", metric_value, None)
        return "stop"

    def _record_result(
        self,
        experiment_id: int,
        status: str,
        metric_value: float | None,
        commit_hash: str | None,
    ) -> None:
        """Record an experiment result in the results tracker.

        Args:
            experiment_id: Sequential experiment number.
            status: Outcome -- ``"keep"``, ``"revert"``, or ``"crash"``.
            metric_value: Observed metric value (or None).
            commit_hash: Git commit hash if kept (or None).
        """
        result = ExperimentResult(
            experiment_id=experiment_id,
            commit_hash=commit_hash,
            metric_name=self.config.metric,
            metric_value=metric_value,
            status=status,
            description=f"experiment-{experiment_id}",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.results_tracker.add(result)

    def _build_prompt(self) -> str:
        """Construct the experiment prompt with context from experiments.md.

        Returns:
            Prompt string for ``claude -p``.
        """
        journal_content = ""
        if self._journal_path.exists():
            journal_content = self._journal_path.read_text()

        exp_num = self.state.experiment_count + 1
        prompt = (
            "You are an ML research agent. "
            "Read CLAUDE.md for your protocol. "
            "Read experiments.md for history. "
            "Run train.py, evaluate results, and report the metric value. "
            f"Metric: {self.config.metric} (direction: {self.config.direction}). "
            f"Experiment #{exp_num}."
        )

        if journal_content:
            prompt += f"\n\nExperiment history:\n{journal_content}"

        return prompt
