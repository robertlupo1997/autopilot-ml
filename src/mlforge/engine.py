"""Run engine -- orchestrates the autonomous experiment loop.

Spawns fresh ``claude -p`` sessions per experiment, processes results through
deviation handling, makes keep/revert decisions, and stops when guardrails trip.
This is the heart of mlforge -- the loop that runs overnight.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import signal
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from mlforge.checkpoint import save_checkpoint
from mlforge.config import Config
from mlforge.export import export_artifact
from mlforge.git_ops import GitManager
from mlforge.guardrails import CostTracker, DeviationHandler, ResourceGuardrails
from mlforge.intelligence.diagnostics import diagnose_classification, diagnose_regression
from mlforge.intelligence.drafts import DraftResult, get_families_for_domain, select_best_draft
from mlforge.intelligence.stagnation import check_stagnation, trigger_stagnation_branch
from mlforge.journal import (
    JournalEntry,
    append_journal_entry,
    get_last_diff,
    load_journal,
    render_journal_markdown,
)
from mlforge.progress import LiveProgress
from mlforge.results import ExperimentResult, ResultsTracker
from mlforge.retrospective import generate_retrospective
from mlforge.state import SessionState
from mlforge.tabular.baselines import compute_baselines, passes_baseline_gate

logger = logging.getLogger(__name__)

# Task types that map to classification diagnostics.
_CLASSIFICATION_TASKS: frozenset[str] = frozenset({
    "classification", "image_classification", "text_classification", "custom", "sft",
})

# Default task type per domain -- used when plugin_settings has no explicit "task" key.
_DOMAIN_DEFAULT_TASK: dict[str, str] = {
    "tabular": "classification",
    "deeplearning": "image_classification",
    "finetuning": "sft",
}


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
        self._journal_jsonl_path = experiment_dir / "experiments.jsonl"
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
                    if self.config.enable_drafts:
                        draft_results = self._run_draft_phase()
                        best = select_best_draft(draft_results, self.config.direction)
                        if best and best.commit_hash:
                            self.git.repo.git.checkout(best.commit_hash)
                            self.state.best_metric = best.metric_value
                            self.state.best_commit = best.commit_hash

                    self.state.baselines = self._compute_baselines()
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

                    # Tag best experiment
                    if self.state.best_commit:
                        tag_name = f"best-{getattr(self.state, 'run_id', None) or 'unknown'}"
                        try:
                            self.git.tag_best(tag_name, f"Best experiment: {self.state.best_metric}")
                        except ValueError:
                            pass  # Tag already exists (resume case)

                    self.git.close()
        finally:
            signal.signal(signal.SIGINT, prev_handler)

    def _run_one_experiment(
        self, oom_hint: bool = False, prompt_override: str | None = None
    ) -> dict:
        """Spawn a single ``claude -p`` session and return parsed JSON.

        Args:
            oom_hint: If True, prepend OOM avoidance hint to the prompt.
            prompt_override: If provided, use this prompt instead of _build_prompt().

        Returns:
            Parsed JSON dict from claude stdout. On failure, returns a dict
            with ``status`` set to ``"crash"`` or ``"timeout"``.
        """
        prompt = prompt_override if prompt_override is not None else self._build_prompt()
        if oom_hint:
            prompt = (
                "IMPORTANT: The previous attempt ran out of memory. "
                "Use smaller batch sizes or simpler models.\n\n" + prompt
            )

        claude_md_path = self.experiment_dir / "CLAUDE.md"
        system_prompt = claude_md_path.read_text() if claude_md_path.exists() else ""

        if self.config.max_turns_per_experiment:
            turns_instruction = (
                f"\n\nIMPORTANT: Complete your work within "
                f"{self.config.max_turns_per_experiment} tool-use turns. "
                f"After that limit, wrap up and report your metric value."
            )
            if system_prompt:
                system_prompt += turns_instruction
            else:
                system_prompt = turns_instruction.strip()

        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--dangerously-skip-permissions",
            "--max-budget-usd", str(self.config.per_experiment_budget_usd),
        ]

        if system_prompt:
            cmd.extend(["--append-system-prompt", system_prompt])

        if self.config.model is not None:
            cmd.extend(["--model", self.config.model])

        logger.debug("Spawning claude -p (timeout=%ds)", self.config.per_experiment_timeout_sec)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.per_experiment_timeout_sec,
                cwd=str(self.experiment_dir),
            )
        except subprocess.TimeoutExpired:
            logger.warning("Experiment timed out after %ds", self.config.per_experiment_timeout_sec)
            return {"status": "timeout"}

        if proc.returncode != 0:
            logger.warning("Experiment crashed (returncode=%d)", proc.returncode)
            return {"status": "crash", "error": proc.stderr or proc.stdout}

        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON output from claude")
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
        prev_best = self.state.best_metric
        logger.info("Experiment %d: metric=%s, action=%s", exp_id, metric_value, action)

        if action == "keep":
            # Baseline gate: check BEFORE committing
            if self.state.baselines and metric_value is not None:
                if not passes_baseline_gate(
                    metric_value, self.state.baselines, self.config.direction
                ):
                    # Downgrade to revert -- did not beat baselines
                    self.git.revert_to_last_commit()
                    self.state.total_reverts += 1
                    self.state.consecutive_reverts += 1
                    self._write_journal(exp_id, "revert", metric_value, None, prev_best=prev_best)
                    self._record_result(exp_id, "revert", metric_value, None)
                    return "revert"

            commit_hash = self.git.commit_experiment(
                f"experiment-{exp_id}: improvement",
                ["."],
            )
            self.state.best_metric = metric_value
            self.state.best_commit = commit_hash
            self.state.total_keeps += 1
            self.state.consecutive_reverts = 0
            self._write_journal(exp_id, "keep", metric_value, commit_hash, prev_best=prev_best)
            self._record_result(exp_id, "keep", metric_value, commit_hash)
            self._run_diagnostics()
            return "keep"

        if action == "revert":
            self.git.revert_to_last_commit()
            self.state.total_reverts += 1
            self.state.consecutive_reverts += 1
            self._write_journal(exp_id, "revert", metric_value, None, prev_best=prev_best)
            self._record_result(exp_id, "revert", metric_value, None)
            self._run_diagnostics()

            # Stagnation check after revert
            if check_stagnation(self.state, threshold=self.config.stagnation_threshold):
                logger.info("Stagnation detected (%d consecutive reverts)", self.state.consecutive_reverts)
                families = get_families_for_domain(self.config.domain)
                untried = [f for f in families if f not in self.state.tried_families]
                if untried:
                    new_family = untried[0]
                    logger.info("Branching to new model family: %s", new_family)
                    branch = trigger_stagnation_branch(self.git, self.state, new_family)
                    if branch is not None:
                        self.state.tried_families.append(new_family)

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
            timestamp=datetime.now(UTC).isoformat(),
        )
        self.results_tracker.add(result)

    def _run_draft_phase(self) -> list[DraftResult]:
        """Run one experiment per algorithm family and return draft results.

        Iterates over ``ALGORITHM_FAMILIES``, builds a draft-specific prompt for
        each, spawns an experiment, and collects results. Appends each family
        name to ``state.tried_families``.

        Returns:
            List of DraftResult objects, one per family.
        """
        task = self.config.plugin_settings.get(
            "task",
            _DOMAIN_DEFAULT_TASK.get(self.config.domain, "classification"),
        )
        results: list[DraftResult] = []

        families = get_families_for_domain(self.config.domain)
        for family_name, family_info in families.items():
            prompt = self._build_draft_prompt(family_name, family_info, task)
            exp_result = self._run_one_experiment(prompt_override=prompt)

            # Track cost
            cost = exp_result.get("total_cost_usd", 0.0)
            self.cost_tracker.record(cost, self.state)

            # Extract metric from nested result string
            metric_value = None
            if "result" in exp_result and isinstance(exp_result["result"], str):
                try:
                    inner = json.loads(exp_result["result"])
                    if "metric_value" in inner:
                        metric_value = inner["metric_value"]
                except (json.JSONDecodeError, TypeError):
                    pass
            elif "metric_value" in exp_result:
                metric_value = exp_result.get("metric_value")

            if metric_value is not None:
                commit_hash = self.git.commit_experiment(
                    f"draft-{family_name}",
                    ["."],
                )
                draft = DraftResult(
                    name=family_name,
                    metric_value=metric_value,
                    status="draft-keep",
                    commit_hash=commit_hash,
                    description=f"{family_info.get('description', family_name)} draft",
                )
            else:
                draft = DraftResult(
                    name=family_name,
                    metric_value=None,
                    status="draft-discard",
                    commit_hash="",
                    description=f"{family_info.get('description', family_name)} draft (failed)",
                )

            results.append(draft)
            self.state.tried_families.append(family_name)

        return results

    def _build_draft_prompt(self, family_name: str, family_info: dict, task: str) -> str:
        """Build a prompt instructing the agent to use a specific model family.

        Args:
            family_name: Algorithm family key (e.g. "linear").
            family_info: Dict with 'description', 'classification', 'regression' keys.
            task: Either "classification" or "regression".

        Returns:
            Prompt string for ``claude -p``.
        """
        model_class = family_info.get(task, family_name)
        return (
            "You are an ML research agent. Read CLAUDE.md for your protocol. "
            f"This is a DRAFT experiment. Use ONLY {model_class} from "
            f"{family_info.get('description', family_name)}. "
            "Do NOT use other model families. "
            "Run train.py, evaluate results, and report the metric value. "
            f"Metric: {self.config.metric} (direction: {self.config.direction})."
        )

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

        diagnostics_path = self.experiment_dir / "diagnostics.md"
        if diagnostics_path.exists():
            diagnostics_content = diagnostics_path.read_text()
            prompt += f"\n\nDiagnostics from last experiment:\n{diagnostics_content}"

        return prompt

    def _run_diagnostics(self) -> None:
        """Run diagnostics on predictions if predictions.csv exists.

        Loads predictions, calls the appropriate diagnose function based on
        task type, formats the output as markdown, and writes to diagnostics.md.
        """
        predictions_path = self.experiment_dir / "predictions.csv"
        if not predictions_path.exists():
            return

        import pandas as pd

        df = pd.read_csv(predictions_path)
        y_true = df["y_true"].values
        y_pred = df["y_pred"].values

        task = self.config.plugin_settings.get(
            "task",
            _DOMAIN_DEFAULT_TASK.get(self.config.domain, "classification"),
        )
        if task in _CLASSIFICATION_TASKS:
            diag = diagnose_classification(y_true, y_pred)
            task_type = "classification"
        else:
            diag = diagnose_regression(y_true, y_pred)
            task_type = "regression"

        content = self._format_diagnostics(diag, task_type)
        (self.experiment_dir / "diagnostics.md").write_text(content)

    def _format_diagnostics(self, diag: dict, task: str) -> str:
        """Format diagnostics dict as readable markdown.

        Args:
            diag: Diagnostics dict from diagnose_regression or diagnose_classification.
            task: "regression" or "classification".

        Returns:
            Markdown string with diagnostics.
        """
        lines: list[str] = ["# Diagnostics", ""]

        if task == "regression":
            # Worst predictions
            lines.append("## Worst Predictions")
            lines.append("")
            lines.append("| Index | y_true | y_pred | abs_error |")
            lines.append("|-------|--------|--------|-----------|")
            for wp in diag.get("worst_predictions", []):
                lines.append(
                    f"| {wp['index']} | {wp['y_true']:.4f} | "
                    f"{wp['y_pred']:.4f} | {wp['abs_error']:.4f} |"
                )
            lines.append("")

            # Bias
            bias = diag.get("bias", {})
            lines.append(f"## Bias: {bias.get('direction', 'unknown')} "
                         f"(magnitude: {bias.get('magnitude', 0):.4f})")
            lines.append("")

            # Feature correlations
            corrs = diag.get("feature_error_correlations", {})
            if corrs:
                lines.append("## Feature-Error Correlations")
                lines.append("")
                for name, val in sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True):
                    lines.append(f"- {name}: {val:.4f}")
                lines.append("")

        else:
            # Misclassified samples
            lines.append("## Misclassified Samples")
            lines.append("")
            lines.append("| Index | y_true | y_pred |")
            lines.append("|-------|--------|--------|")
            for ms in diag.get("misclassified_samples", []):
                lines.append(f"| {ms['index']} | {ms['y_true']} | {ms['y_pred']} |")
            lines.append("")

            # Per-class accuracy
            pca = diag.get("per_class_accuracy", {})
            if pca:
                lines.append("## Per-Class Accuracy")
                lines.append("")
                for cls, acc in pca.items():
                    lines.append(f"- {cls}: {acc:.4f}")
                lines.append("")

            # Confused pairs
            pairs = diag.get("confused_pairs", [])
            if pairs:
                lines.append("## Most Confused Pairs")
                lines.append("")
                for true_cls, pred_cls, count in pairs:
                    lines.append(f"- {true_cls} -> {pred_cls}: {count} errors")
                lines.append("")

        return "\n".join(lines)

    def _compute_baselines(self) -> dict | None:
        """Compute baselines before the experiment loop.

        Dispatches to domain-specific baseline modules:
        - tabular: sklearn DummyClassifier/DummyRegressor on training data
        - deeplearning: DummyClassifier on extracted labels or theoretical loss
        - finetuning: theoretical loss/perplexity bounds from vocab size

        Returns:
            Baselines dict, or None if domain is unknown or data unavailable.
        """
        if self.config.domain == "tabular":
            return self._compute_tabular_baselines()
        elif self.config.domain == "deeplearning":
            return self._compute_dl_baselines()
        elif self.config.domain == "finetuning":
            return self._compute_ft_baselines()
        else:
            return None

    def _compute_tabular_baselines(self) -> dict | None:
        """Compute baselines for tabular domain using prepare.py."""
        prepare_path = self.experiment_dir / "prepare.py"
        if not prepare_path.exists():
            return None

        spec = importlib.util.spec_from_file_location("prepare", str(prepare_path))
        if spec is None or spec.loader is None:
            return None

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        csv_path = self.config.plugin_settings.get("csv_path")
        target_column = self.config.plugin_settings.get("target_column")
        if not csv_path or not target_column:
            return None

        try:
            df = mod.load_data(self.experiment_dir / csv_path)
            X_train, _X_test, y_train, _y_test = mod.split_data(df, target_column)
        except Exception:
            return None

        task = self.config.plugin_settings.get("task", "classification")
        self.state.task = task
        return compute_baselines(X_train, y_train, self.config.metric, task)

    def _compute_dl_baselines(self) -> dict | None:
        """Compute baselines for deep learning domain."""
        labels = self._load_dl_labels()
        if labels is None:
            return None

        from mlforge.deeplearning.baselines import compute_baselines as dl_baselines

        task = self.config.plugin_settings.get("task", "image_classification")
        return dl_baselines(labels, self.config.metric, task)

    def _load_dl_labels(self):
        """Extract labels from dataset directory structure or CSV.

        Returns:
            numpy array of labels, or None on any failure.
        """
        import numpy as np

        dataset_path_str = self.config.plugin_settings.get("dataset_path")
        if not dataset_path_str:
            return None

        dataset_path = self.experiment_dir / dataset_path_str
        if not dataset_path.exists():
            return None

        try:
            if dataset_path.is_dir():
                # Scan subdirectories as class folders
                class_dirs = sorted(
                    [d for d in dataset_path.iterdir() if d.is_dir()]
                )
                if not class_dirs:
                    return None
                labels_list = []
                for idx, class_dir in enumerate(class_dirs):
                    file_count = sum(1 for f in class_dir.iterdir() if f.is_file())
                    if file_count > 0:
                        labels_list.extend([idx] * file_count)
                if not labels_list:
                    return None
                return np.array(labels_list)
            else:
                # CSV-like file with a "label" column
                import pandas as pd

                df = pd.read_csv(dataset_path)
                if "label" not in df.columns:
                    return None
                return df["label"].values
        except Exception:
            return None

    def _compute_ft_baselines(self) -> dict | None:
        """Compute baselines for fine-tuning domain."""
        from mlforge.finetuning.baselines import compute_baselines as ft_baselines

        vocab_size = self.config.plugin_settings.get("vocab_size", 32000)
        return ft_baselines(self.config.metric, vocab_size)

    def _write_journal(
        self,
        exp_id: int,
        status: str,
        metric_value: float | None,
        commit_hash: str | None,
        hypothesis: str = "",
        prev_best: float | None = None,
    ) -> None:
        """Write a journal entry and re-render experiments.md.

        Args:
            exp_id: Experiment number.
            status: "keep", "revert", or "crash".
            metric_value: Observed metric value.
            commit_hash: Git commit hash if kept.
            hypothesis: What was tried.
            prev_best: Previous best metric for delta computation.
        """
        diff = get_last_diff(self.experiment_dir) if status == "keep" else None
        delta = None
        if metric_value is not None and prev_best is not None:
            delta = metric_value - prev_best

        entry = JournalEntry(
            experiment_id=exp_id,
            hypothesis=hypothesis,
            result=f"Experiment {exp_id}: {status}",
            metric_value=metric_value,
            metric_delta=delta,
            commit_hash=commit_hash,
            status=status,
            diff=diff,
        )
        append_journal_entry(self._journal_jsonl_path, entry)

        # Re-render markdown from JSONL
        entries = load_journal(self._journal_jsonl_path)
        self._journal_path.write_text(render_journal_markdown(entries))
