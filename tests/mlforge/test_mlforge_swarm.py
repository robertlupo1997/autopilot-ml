"""Tests for swarm command flags, CLAUDE.md copy, .mlforge dir creation, and state.json template.

Phase 14-01: Fix swarm agent subprocess command.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mlforge.config import Config
from mlforge.swarm import SwarmManager
from mlforge.templates import get_template_env


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def swarm_setup(tmp_path: Path):
    """Create a SwarmManager with a real git repo so setup() can create worktrees."""
    import subprocess

    # Init a git repo with an initial commit so worktrees work
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "--allow-empty", "-m", "init"],
        check=True, capture_output=True,
        env={"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t",
             "HOME": str(tmp_path), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )

    # Write CLAUDE.md in experiment_dir
    claude_md_content = "# Test Protocol\nMetric: accuracy\n"
    (tmp_path / "CLAUDE.md").write_text(claude_md_content)

    config = Config(
        budget_usd=6.0,
        budget_minutes=60,
        budget_experiments=30,
        metric="accuracy",
        direction="maximize",
    )
    sm = SwarmManager(config=config, experiment_dir=tmp_path, n_agents=3)
    worktrees = sm.setup()
    child_configs = sm.create_child_configs()

    yield {
        "sm": sm,
        "config": config,
        "tmp_path": tmp_path,
        "worktrees": worktrees,
        "child_configs": child_configs,
        "claude_md_content": claude_md_content,
    }

    sm.teardown()


# ---------------------------------------------------------------------------
# TestBuildAgentCommand -- flag tests
# ---------------------------------------------------------------------------

class TestBuildAgentCommandFlags:
    """Tests for _build_agent_command() return value including required CLI flags."""

    def test_build_command_includes_skip_permissions(self, swarm_setup: dict) -> None:
        sm = swarm_setup["sm"]
        child_configs = swarm_setup["child_configs"]
        cmd = sm._build_agent_command(0, child_configs[0])
        assert "--dangerously-skip-permissions" in cmd

    def test_build_command_includes_max_budget(self, swarm_setup: dict) -> None:
        sm = swarm_setup["sm"]
        child_configs = swarm_setup["child_configs"]
        cmd = sm._build_agent_command(0, child_configs[0])
        assert "--max-budget-usd" in cmd
        budget_idx = cmd.index("--max-budget-usd") + 1
        assert float(cmd[budget_idx]) == pytest.approx(2.0)  # 6.0 / 3

    def test_build_command_includes_output_format(self, swarm_setup: dict) -> None:
        sm = swarm_setup["sm"]
        child_configs = swarm_setup["child_configs"]
        cmd = sm._build_agent_command(0, child_configs[0])
        assert "--output-format" in cmd
        fmt_idx = cmd.index("--output-format") + 1
        assert cmd[fmt_idx] == "json"

    def test_build_command_includes_append_system_prompt(self, swarm_setup: dict) -> None:
        """When CLAUDE.md exists in worktree, command should include --append-system-prompt."""
        sm = swarm_setup["sm"]
        child_configs = swarm_setup["child_configs"]
        cmd = sm._build_agent_command(0, child_configs[0])
        assert "--append-system-prompt" in cmd

    def test_build_command_no_system_prompt_when_missing(self, swarm_setup: dict) -> None:
        """When CLAUDE.md does NOT exist in worktree, command should NOT include --append-system-prompt."""
        sm = swarm_setup["sm"]
        child_configs = swarm_setup["child_configs"]
        # Remove CLAUDE.md from the worktree
        wt_claude = sm._worktree_paths[0] / "CLAUDE.md"
        if wt_claude.exists():
            wt_claude.unlink()
        cmd = sm._build_agent_command(0, child_configs[0])
        assert "--append-system-prompt" not in cmd


# ---------------------------------------------------------------------------
# TestSetup -- CLAUDE.md copy + .mlforge dir creation
# ---------------------------------------------------------------------------

class TestSetupCopiesAndDirs:
    """Tests for setup() side effects: CLAUDE.md copy and .mlforge dir creation."""

    def test_setup_copies_claude_md(self, swarm_setup: dict) -> None:
        """After setup(), each worktree has CLAUDE.md copied from experiment_dir."""
        worktrees = swarm_setup["worktrees"]
        expected_content = swarm_setup["claude_md_content"]
        for wt_path in worktrees:
            claude_md = wt_path / "CLAUDE.md"
            assert claude_md.exists(), f"CLAUDE.md missing in {wt_path}"
            assert claude_md.read_text() == expected_content

    def test_setup_creates_mlforge_dir(self, swarm_setup: dict) -> None:
        """After setup(), each worktree has .mlforge/ directory."""
        worktrees = swarm_setup["worktrees"]
        for wt_path in worktrees:
            mlforge_dir = wt_path / ".mlforge"
            assert mlforge_dir.exists(), f".mlforge/ missing in {wt_path}"
            assert mlforge_dir.is_dir()


# ---------------------------------------------------------------------------
# TestTemplate -- state.json instruction in swarm_claude.md.j2
# ---------------------------------------------------------------------------

class TestTemplateStateJson:
    """Test swarm_claude.md.j2 rendered output contains state.json instruction."""

    def test_template_has_state_json_instruction(self) -> None:
        env = get_template_env()
        template = env.get_template("swarm_claude.md.j2")
        rendered = template.render(
            agent_id="agent-0",
            scoreboard_path="/tmp/scoreboard.tsv",
            metric="accuracy",
            direction="maximize",
            budget_usd=2.0,
            budget_minutes=10,
            budget_experiments=5,
        )
        assert "state.json" in rendered
        assert "best_metric" in rendered
        assert "best_commit" in rendered
        assert "experiment_count" in rendered
