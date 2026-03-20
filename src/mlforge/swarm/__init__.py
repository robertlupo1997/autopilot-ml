"""Swarm mode for parallel agent exploration in git worktrees.

Provides SwarmManager for orchestrating parallel agents and SwarmScoreboard
for file-locked coordination between agents.
"""

from __future__ import annotations

import json
import shutil
import signal
import subprocess
from dataclasses import replace
from pathlib import Path

from git import Repo, GitCommandError

from mlforge.config import Config
from mlforge.swarm.scoreboard import SwarmScoreboard
from mlforge.templates import get_template_env

__all__ = ["SwarmManager", "SwarmScoreboard"]


class SwarmManager:
    """Orchestrates parallel agent exploration in git worktrees.

    Creates N worktrees, spawns ``claude -p`` subprocesses with rendered
    swarm protocol templates, and coordinates via file-locked scoreboard.

    Args:
        config: Parent Config with full budget.
        experiment_dir: Root experiment directory.
        n_agents: Number of parallel agents (default 3).
    """

    def __init__(
        self,
        config: Config,
        experiment_dir: Path,
        n_agents: int = 3,
    ) -> None:
        self.config = config
        self.experiment_dir = experiment_dir
        self.n_agents = n_agents
        self.swarm_dir = experiment_dir / ".swarm"
        self.scoreboard = SwarmScoreboard(
            self.swarm_dir / "scoreboard.tsv",
            direction=config.direction,
        )
        self._worktree_paths: list[Path] = []
        self._processes: list[subprocess.Popen] = []
        self._stop_requested = False

    def create_child_configs(self) -> list[Config]:
        """Split parent budget evenly across N child configs.

        Children inherit domain, metric, direction, per-experiment settings,
        and plugin_settings. Children have NO swarm capability (leaf agents).
        """
        children = []
        for _ in range(self.n_agents):
            child = replace(
                self.config,
                budget_usd=self.config.budget_usd / self.n_agents,
                budget_minutes=self.config.budget_minutes // self.n_agents,
                budget_experiments=self.config.budget_experiments // self.n_agents,
            )
            children.append(child)
        return children

    def setup(self) -> list[Path]:
        """Create .swarm/ directory and N git worktrees.

        Returns:
            List of worktree paths created.
        """
        self.swarm_dir.mkdir(parents=True, exist_ok=True)
        repo = self._get_repo()

        self._worktree_paths = []
        for i in range(self.n_agents):
            wt_path = self.swarm_dir / f"agent-{i}"
            repo.git.worktree("add", str(wt_path), "HEAD")
            self._worktree_paths.append(wt_path)

        # Copy CLAUDE.md and create .mlforge/ in each worktree
        claude_md_src = self.experiment_dir / "CLAUDE.md"
        for wt_path in self._worktree_paths:
            if claude_md_src.exists():
                shutil.copy2(claude_md_src, wt_path / "CLAUDE.md")
            (wt_path / ".mlforge").mkdir(parents=True, exist_ok=True)

        return list(self._worktree_paths)

    def run(self) -> dict:
        """Spawn agents, wait for completion, return results.

        Returns:
            Dict with agents count, best_score, best_agent, and all results.
        """
        # Register SIGINT handler
        original_handler = signal.getsignal(signal.SIGINT)

        def _sigint_handler(signum, frame):  # noqa: ANN001
            self._stop_requested = True

        signal.signal(signal.SIGINT, _sigint_handler)

        child_configs = self.create_child_configs()
        try:
            for i, child_config in enumerate(child_configs):
                cmd = self._build_agent_command(i, child_config)
                proc = subprocess.Popen(cmd, cwd=str(self._worktree_paths[i]))
                self._processes.append(proc)

            # Wait for all to complete
            for proc in self._processes:
                proc.wait()

            # Publish results from each agent's state.json
            for i, _proc in enumerate(self._processes):
                if i < len(self._worktree_paths):
                    state_path = self._worktree_paths[i] / ".mlforge" / "state.json"
                    if state_path.exists():
                        try:
                            agent_state = json.loads(state_path.read_text())
                            metric = agent_state.get("best_metric")
                            commit = agent_state.get("best_commit", "")
                            if metric is not None:
                                self.scoreboard.publish_result(
                                    agent=f"agent-{i}",
                                    commit=commit or "",
                                    metric_value=metric,
                                    elapsed_sec=0.0,
                                    status="complete",
                                    description=f"Agent {i} best result",
                                )
                        except (json.JSONDecodeError, OSError):
                            pass  # Agent crashed or state corrupted

            best_score, best_agent = self.scoreboard.read_best()
            all_results = self.scoreboard.read_all()

            # Verify best result
            try:
                from mlforge.swarm.verifier import verify_best_result

                verification = verify_best_result(
                    self.experiment_dir, self.scoreboard
                )
            except Exception:
                verification = None

            return {
                "agents": self.n_agents,
                "best_score": best_score,
                "best_agent": best_agent,
                "results": all_results,
                "verification": verification,
            }
        finally:
            signal.signal(signal.SIGINT, original_handler)

    def _build_agent_command(
        self, agent_index: int, child_config: Config
    ) -> list[str]:
        """Build claude -p command with rendered swarm protocol template.

        Args:
            agent_index: Index of the agent (0-based).
            child_config: Budget-split child Config for this agent.

        Returns:
            Command list for subprocess.Popen.
        """
        env = get_template_env()
        template = env.get_template("swarm_claude.md.j2")
        prompt = template.render(
            agent_id=f"agent-{agent_index}",
            scoreboard_path=str(self.scoreboard.scoreboard_path),
            metric=self.config.metric,
            direction=self.config.direction,
            budget_usd=child_config.budget_usd,
            budget_minutes=child_config.budget_minutes,
            budget_experiments=child_config.budget_experiments,
        )
        wt_path = self._worktree_paths[agent_index]
        claude_md_path = wt_path / "CLAUDE.md"
        system_prompt = claude_md_path.read_text() if claude_md_path.exists() else ""

        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--dangerously-skip-permissions",
            "--max-budget-usd", str(child_config.budget_usd),
        ]

        if system_prompt:
            cmd.extend(["--append-system-prompt", system_prompt])

        return cmd

    def teardown(self) -> None:
        """Remove all worktrees and clean up.

        Safe to call even if some worktrees were already removed (crash recovery).
        """
        repo = self._get_repo()
        for wt_path in self._worktree_paths:
            try:
                repo.git.worktree("remove", "--force", str(wt_path))
            except GitCommandError:
                pass  # Already removed or doesn't exist
        try:
            repo.git.worktree("prune")
        except GitCommandError:
            pass
        self._worktree_paths = []

    def _get_repo(self) -> Repo:
        """Get GitPython Repo for the experiment directory."""
        return Repo(str(self.experiment_dir))
