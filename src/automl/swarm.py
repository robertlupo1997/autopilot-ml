"""SwarmManager orchestrator for multi-agent ML experimentation.

Composes SwarmScoreboard, swarm_claims, and GitManager worktrees to
coordinate N parallel claude -p agents, each exploring different algorithm
families in isolated git worktrees.

No external dependencies -- stdlib only (subprocess, signal, time, json,
pathlib).

IMPORTANT: The swarm manager must be invoked from a terminal OUTSIDE of
Claude Code. Spawning claude -p from within an active Claude Code session
will fail (documented in Phase 7/8 findings).
"""

from __future__ import annotations

import json
import signal
import subprocess
import sys
import time
from pathlib import Path

from automl.drafts import ALGORITHM_FAMILIES
from automl.git_ops import GitManager
from automl.swarm_scoreboard import SwarmScoreboard
from automl.templates import render_swarm_claude_md


class SwarmManager:
    """Orchestrate N parallel claude -p agents for multi-agent ML experimentation.

    Each agent runs in an isolated git worktree under .swarm/agent-N/ and
    explores a non-overlapping subset of algorithm families during the draft
    phase. Agents coordinate through a file-locked scoreboard.tsv and
    TTL claim files for iteration-phase deduplication.

    Args:
        experiment_dir: Path to the scaffolded experiment directory.
        n_agents: Number of parallel agents to spawn.
        task_type: "classification" or "regression" (determines family list).
        metric: Metric name to optimize (e.g., "accuracy", "rmse").
        time_budget: Time budget in seconds per experiment run.
    """

    def __init__(
        self,
        experiment_dir: Path,
        n_agents: int,
        task_type: str,
        metric: str,
        time_budget: int,
    ) -> None:
        self.experiment_dir = experiment_dir
        self.task_type = task_type
        self.metric = metric
        self.time_budget = time_budget
        self.swarm_dir = experiment_dir / ".swarm"

        # Cap n_agents at number of available families
        families = ALGORITHM_FAMILIES.get(task_type, [])
        max_agents = len(families)
        if n_agents > max_agents:
            print(
                f"[swarm] Warning: n_agents={n_agents} exceeds available families "
                f"({max_agents}). Capping at {max_agents}.",
                file=sys.stderr,
            )
            n_agents = max_agents
        self.n_agents = n_agents

        self.scoreboard = SwarmScoreboard(self.swarm_dir)
        self.git = GitManager(repo_dir=str(experiment_dir))
        self.agents: list[subprocess.Popen] = []
        self._shutdown = False

    def setup(self) -> list[list[dict]]:
        """Create .swarm/ directory structure, worktrees, and config.json.

        Creates:
        - .swarm/ directory
        - .swarm/claims/ directory
        - .swarm/agent-N/ worktree for each agent (via git worktree add)
        - .swarm/config.json with run metadata and family assignments

        Returns:
            List of family assignment lists, one per agent. Each inner list
            contains the algorithm family dicts assigned to that agent.
        """
        self.swarm_dir.mkdir(exist_ok=True)
        (self.swarm_dir / "claims").mkdir(exist_ok=True)

        families = ALGORITHM_FAMILIES[self.task_type]
        assignments = self._divide_families(families, self.n_agents)

        run_tag = time.strftime("%Y%m%d-%H%M%S")
        for i in range(self.n_agents):
            agent_dir = self.swarm_dir / f"agent-{i}"
            branch = f"automl/run-{run_tag}/agent-{i}"
            self.git.create_worktree(str(agent_dir), branch)
            # Write rendered swarm coordination protocol into worktree
            family_names = ", ".join(f["name"] for f in assignments[i])
            rendered = render_swarm_claude_md(
                agent_id=i,
                n_agents=self.n_agents,
                family_names=family_names,
                swarm_dir=str(self.swarm_dir),
                metric=self.metric,
            )
            (agent_dir / "swarm_claude.md").write_text(rendered)

        (self.swarm_dir / "config.json").write_text(
            json.dumps(
                {
                    "n_agents": self.n_agents,
                    "task_type": self.task_type,
                    "metric": self.metric,
                    "run_tag": run_tag,
                    "assignments": [[f["name"] for f in a] for a in assignments],
                },
                indent=2,
            )
        )
        return assignments

    def run(self, assignments: list[list[dict]]) -> None:
        """Spawn agents and monitor until all complete or SIGINT received.

        Registers a SIGINT handler for graceful shutdown, spawns one
        subprocess per agent, then enters the monitor loop.

        Args:
            assignments: Family assignment lists from setup(), one per agent.
        """
        signal.signal(signal.SIGINT, self._handle_sigint)
        for i, assigned in enumerate(assignments):
            workdir = self.swarm_dir / f"agent-{i}"
            proc = spawn_agent(
                agent_id=i,
                workdir=workdir,
                assigned_families=assigned,
                metric=self.metric,
                time_budget=self.time_budget,
                swarm_dir=self.swarm_dir,
            )
            self.agents.append(proc)
        self._monitor_loop()

    def _monitor_loop(self) -> None:
        """Poll agents every 10 seconds and print alive count + global best.

        Exits when all agents have finished or _shutdown is set by SIGINT.
        """
        while not self._shutdown:
            alive = [p for p in self.agents if p.poll() is None]
            if not alive:
                break
            best_score, best_agent = self.scoreboard.read_best()
            print(
                f"[swarm] {len(alive)}/{self.n_agents} agents running | "
                f"global best: {best_score} ({best_agent})"
            )
            time.sleep(10)

    def _handle_sigint(self, sig, frame) -> None:
        """Handle SIGINT by terminating all agent processes."""
        print("\n[swarm] Shutdown signal received. Terminating agents...", file=sys.stderr)
        self._shutdown = True
        for proc in self.agents:
            proc.terminate()

    def _divide_families(
        self, families: list[dict], n_agents: int
    ) -> list[list[dict]]:
        """Assign families round-robin across agents.

        Agent-0 gets families [0, N, 2N...], agent-1 gets [1, N+1...], etc.
        Agents with index >= len(families) receive empty lists.

        Args:
            families: List of algorithm family dicts from ALGORITHM_FAMILIES.
            n_agents: Number of agents to distribute families across.

        Returns:
            List of n_agents lists, each containing the families for that agent.
        """
        assignments: list[list[dict]] = [[] for _ in range(n_agents)]
        for i, family in enumerate(families):
            assignments[i % n_agents].append(family)
        return assignments

    def teardown(self) -> None:
        """Remove agent worktrees and run git worktree prune.

        Tries to remove each agent's worktree. Errors are caught and ignored
        (the worktree may already be removed or in a bad state). Always
        runs git worktree prune at the end.
        """
        for i in range(self.n_agents):
            agent_dir = self.swarm_dir / f"agent-{i}"
            if agent_dir.exists():
                try:
                    self.git.remove_worktree(str(agent_dir))
                except Exception:
                    pass
        self.git._run("worktree", "prune")


def spawn_agent(
    agent_id: int,
    workdir: Path,
    assigned_families: list[dict],
    metric: str,
    time_budget: int,
    swarm_dir: Path,
) -> subprocess.Popen:
    """Spawn a claude -p subprocess for one swarm agent.

    Builds a prompt string with agent ID, assigned family names, scoreboard
    path, metric, and time budget. Passes --allowedTools for headless
    operation (required for claude -p per Phase 7/8 findings).

    Args:
        agent_id: Integer agent index (e.g., 0, 1, 2).
        workdir: Path to the agent's git worktree directory.
        assigned_families: Algorithm family dicts assigned to this agent.
        metric: Metric name to optimize (e.g., "accuracy").
        time_budget: Time budget in seconds per experiment.
        swarm_dir: Path to .swarm/ directory (for scoreboard path in prompt).

    Returns:
        subprocess.Popen with stdout=PIPE and stderr=PIPE.
    """
    family_names = ", ".join(f["name"] for f in assigned_families)
    prompt = (
        f"You are Agent-{agent_id} in a multi-agent ML experiment swarm.\n"
        f"Read swarm_claude.md for the full coordination protocol.\n"
        f"\n"
        f"YOUR ASSIGNED ALGORITHM FAMILIES: {family_names}\n"
        f"SWARM SCOREBOARD: {swarm_dir}/scoreboard.tsv\n"
        f"METRIC TO OPTIMIZE: {metric} (higher is better)\n"
        f"TIME BUDGET PER EXPERIMENT: {time_budget}s\n"
    )
    return subprocess.Popen(
        [
            "claude",
            "-p",
            prompt,
            "--allowedTools",
            "Bash(*)",
            "Edit(*)",
            "Write(*)",
            "Read",
            "Glob",
            "Grep",
            "--output-format",
            "json",
            "--max-turns",
            "50",
        ],
        cwd=str(workdir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
