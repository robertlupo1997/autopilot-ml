# Phase 3: Scaffold, CLI + Run Engine - Research

**Researched:** 2026-03-19
**Domain:** CLI entry point, subprocess orchestration, resource guardrails, live terminal UI
**Confidence:** HIGH

## Summary

Phase 3 builds the user-facing surface of mlforge: the CLI entry point (`mlforge <dataset> <goal>`), the run engine that spawns `claude -p` sessions in a keep/revert loop, deviation handling for crashes/OOM/divergence, resource guardrails (cost caps, GPU hours, disk, timeouts), and live terminal progress display. This is the "overnight reliability" phase -- everything needed to leave mlforge running unattended.

The codebase already has all the internal machinery: SessionState, Config, checkpoint/resume, GitManager, journal, results tracker, plugin protocol, hook engine, templates, baselines, diagnostics, stagnation, and multi-draft. Phase 3 wires these together into a user-facing CLI and an autonomous run engine that spawns `claude -p` per experiment iteration. The old `automl` code (cli.py, runner.py, scaffold.py, loop_helpers.py) provides proven reference patterns.

**Primary recommendation:** Use argparse for the CLI (stdlib, no new deps), subprocess.run for `claude -p` invocation with `--output-format json` and `--max-budget-usd` for cost control, psutil for resource monitoring, and `rich.live.Live` for terminal progress display. The run engine is a Python loop that: scaffolds, creates a run branch, then iterates (spawn claude -p -> parse result -> keep/revert -> checkpoint -> check guardrails -> repeat).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CORE-01 | User can pip install mlforge and run `mlforge <dataset> <goal>` to start an autonomous experiment session | CLI module with argparse, pyproject.toml already has `[project.scripts] mlforge = "mlforge.cli:main"` |
| CORE-02 | Agent executes keep/revert experiment loop -- modifies code, evaluates, commits on improvement, resets on failure | RunEngine class orchestrating claude -p subprocess calls, using GitManager for keep/revert and SessionState for tracking |
| CORE-09 | Deviation handling auto-recovers from crashes (retry), OOM (reduce batch), and divergence (revert) | DeviationHandler class with retry logic, OOM detection via stderr parsing, divergence detection via metric comparison |
| GUARD-01 | Frozen file zone enforcement prevents agent from modifying infrastructure files | Already built in hooks.py (write_hook_files); scaffold step must call it for the experiment directory |
| GUARD-02 | Resource guardrails enforce cost caps, GPU hour limits, disk usage | ResourceGuardrails class using psutil for disk/GPU, cost tracking from claude -p JSON output, shutil.disk_usage for disk |
| GUARD-03 | Crash recovery automatically saves state before each experiment | Already built in checkpoint.py (save_checkpoint/load_checkpoint); run engine calls save_checkpoint before each iteration |
| GUARD-04 | Live progress monitoring shows current experiment, best metric, budget remaining | rich.live.Live with a custom renderable showing experiment count, best metric, cost spent, time remaining |
| GUARD-05 | Cost tracking records API token usage per experiment with running total and budget cap | Parse total_cost_usd from claude -p --output-format json response; accumulate in SessionState or dedicated CostTracker |
| INTL-07 | Experiment time/cost budget with per-experiment timeout and total session budget | Config already has budget_minutes and budget_experiments; add budget_usd; per-experiment timeout via subprocess timeout + --max-turns |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| argparse | stdlib | CLI argument parsing | Zero deps, already used in old automl.cli, pyproject.toml entry point is set |
| subprocess | stdlib | Spawning `claude -p` sessions | Only way to run CLI commands from Python; subprocess.run with timeout |
| psutil | >=6.0 | System resource monitoring (disk, memory, GPU hours) | Cross-platform, standard for resource monitoring, provides disk_usage and Process memory tracking |
| rich | >=13.0 | Live terminal progress display | De facto standard for terminal UIs in Python; Live, Table, Progress, Console |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shutil | stdlib | Disk usage (shutil.disk_usage) | Lightweight alternative to psutil for disk-only checks |
| signal | stdlib | Graceful shutdown on SIGINT/SIGTERM | Run engine cleanup on Ctrl+C |
| time | stdlib | Wall-clock budget enforcement | Tracking elapsed time per experiment and total session |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| argparse | click/typer | More deps, more magic; argparse is sufficient for `mlforge <dataset> <goal> [flags]` |
| rich | plain print | No live updating; Phase requires GUARD-04 live terminal display |
| psutil | /proc parsing | Linux-only; psutil is cross-platform |

**Installation:**
```bash
pip install psutil rich
```

These get added to `pyproject.toml` dependencies.

## Architecture Patterns

### Recommended Project Structure
```
src/mlforge/
├── cli.py              # CLI entry point (argparse, main())
├── scaffold.py         # NEW: Experiment directory scaffolding (wires plugin.scaffold + hooks + templates)
├── engine.py           # NEW: RunEngine class (the experiment loop)
├── guardrails.py       # NEW: ResourceGuardrails, CostTracker, DeviationHandler
├── progress.py         # NEW: LiveProgress display (rich.live.Live)
├── config.py           # EXISTING: Add budget_usd, per_experiment_timeout_sec fields
├── state.py            # EXISTING: Add cost_spent_usd field
├── checkpoint.py       # EXISTING: No changes needed
├── git_ops.py          # EXISTING: No changes needed
├── hooks.py            # EXISTING: No changes needed
├── journal.py          # EXISTING: No changes needed
├── results.py          # EXISTING: No changes needed
├── plugins.py          # EXISTING: No changes needed
├── templates/          # EXISTING: No changes needed
├── intelligence/       # EXISTING: No changes needed
└── tabular/            # EXISTING: No changes needed
```

### Pattern 1: Run Engine Loop
**What:** The core experiment orchestration loop that spawns `claude -p` sessions, evaluates results, and makes keep/revert decisions.
**When to use:** This is the heart of Phase 3 -- the autonomous overnight loop.
**Example:**
```python
# Source: Architecture derived from old automl/runner.py + loop_helpers.py + claude -p docs
class RunEngine:
    def __init__(self, experiment_dir: Path, config: Config, state: SessionState):
        self.experiment_dir = experiment_dir
        self.config = config
        self.state = state
        self.git = GitManager(experiment_dir)
        self.journal_path = experiment_dir / "experiments.jsonl"
        self.results = ResultsTracker(experiment_dir / "results.jsonl")
        self.guardrails = ResourceGuardrails(config)
        self.progress = LiveProgress(config, state)

    def run(self) -> None:
        """Main experiment loop: iterate until budget exhausted or guardrail tripped."""
        self.progress.start()
        try:
            while not self.guardrails.should_stop(self.state):
                save_checkpoint(self.state, self.experiment_dir / ".mlforge")
                result = self._run_one_experiment()
                self._process_result(result)
                self.state.experiment_count += 1
                self.progress.update(self.state)
        finally:
            self.progress.stop()
            self.git.close()

    def _run_one_experiment(self) -> dict:
        """Spawn a single claude -p session and parse the JSON output."""
        cmd = [
            "claude", "-p", self._build_prompt(),
            "--output-format", "json",
            "--max-turns", str(self.config.max_turns_per_experiment),
            "--max-budget-usd", str(self.config.per_experiment_budget_usd),
            "--allowedTools", "Bash,Read,Edit,Write,Glob,Grep",
            "--dangerously-skip-permissions",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.config.per_experiment_timeout_sec,
            cwd=str(self.experiment_dir),
        )
        return json.loads(result.stdout)
```

### Pattern 2: Deviation Handling
**What:** Auto-recovery from crashes, OOM, and divergence without human intervention.
**When to use:** Every experiment result goes through deviation handling before keep/revert.
**Example:**
```python
# Source: Architecture derived from old automl/loop_helpers.py + CORE-09 requirement
class DeviationHandler:
    MAX_RETRIES = 2

    def handle(self, result: dict, state: SessionState) -> str:
        """Returns action: 'keep', 'revert', 'retry', 'stop'."""
        # 1. Check for crash
        if result.get("status") == "crash":
            error = result.get("error", "")
            if "MemoryError" in error or "OOM" in error:
                return "retry"  # Will reduce batch size in prompt
            state.consecutive_reverts += 1
            return "revert"

        # 2. Check for metric divergence (NaN, inf, extreme values)
        metric = result.get("metric_value")
        if metric is None or not math.isfinite(metric):
            return "revert"

        # 3. Normal keep/revert based on improvement
        if self._is_improvement(metric, state):
            return "keep"
        return "revert"
```

### Pattern 3: Resource Guardrails
**What:** Hard stops for cost, time, disk, and experiment count.
**When to use:** Checked before each experiment iteration.
**Example:**
```python
# Source: GUARD-02, GUARD-05, INTL-07 requirements
class ResourceGuardrails:
    def should_stop(self, state: SessionState) -> bool:
        """Return True if any guardrail is tripped."""
        if state.experiment_count >= self.config.budget_experiments:
            return True  # Experiment count limit
        if state.cost_spent_usd >= self.config.budget_usd:
            return True  # Cost cap
        if time.time() - self.start_time >= self.config.budget_minutes * 60:
            return True  # Wall clock limit
        if self._disk_usage_exceeded():
            return True  # Disk usage limit
        return False

    def _disk_usage_exceeded(self) -> bool:
        usage = shutil.disk_usage(self.experiment_dir)
        free_gb = usage.free / (1024 ** 3)
        return free_gb < self.config.min_free_disk_gb  # Default: 1 GB
```

### Pattern 4: Live Progress Display
**What:** Rich Live display showing experiment status in terminal.
**When to use:** GUARD-04 requirement -- live terminal output during unattended runs.
**Example:**
```python
# Source: rich.readthedocs.io/en/latest/live.html
from rich.live import Live
from rich.table import Table

class LiveProgress:
    def __init__(self, config: Config, state: SessionState):
        self.config = config
        self.state = state
        self._live = None

    def start(self):
        self._live = Live(self._render(), refresh_per_second=1)
        self._live.start()

    def update(self, state: SessionState):
        self.state = state
        if self._live:
            self._live.update(self._render())

    def _render(self) -> Table:
        table = Table(title="mlforge")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Experiment", f"{self.state.experiment_count}/{self.config.budget_experiments}")
        table.add_row("Best Metric", f"{self.state.best_metric or 'N/A'}")
        table.add_row("Cost", f"${self.state.cost_spent_usd:.2f}/${self.config.budget_usd:.2f}")
        table.add_row("Keeps/Reverts", f"{self.state.total_keeps}/{self.state.total_reverts}")
        return table
```

### Pattern 5: Scaffold (New mlforge version)
**What:** Creates a complete experiment directory from dataset + config, using the plugin system.
**When to use:** First step of `mlforge <dataset> <goal>` -- before the run engine starts.
**Example:**
```python
# Source: Derived from old automl/scaffold.py + mlforge plugin architecture
def scaffold_experiment(config: Config, dataset_path: Path, target_dir: Path) -> Path:
    """Create experiment directory using plugin system."""
    plugin = get_plugin(config.domain)

    # 1. Create directory
    target_dir.mkdir(parents=True, exist_ok=True)

    # 2. Plugin scaffolds domain-specific files
    plugin.scaffold(target_dir, config)

    # 3. Render CLAUDE.md from plugin template context
    claude_md = render_claude_md(plugin, config)
    (target_dir / "CLAUDE.md").write_text(claude_md)

    # 4. Render experiments.md journal template
    experiments_md = render_experiments_md(config, config.run_id)
    (target_dir / "experiments.md").write_text(experiments_md)

    # 5. Write hook files for frozen file enforcement
    write_hook_files(target_dir, plugin.frozen_files)

    # 6. Copy dataset
    shutil.copy2(dataset_path, target_dir / dataset_path.name)

    # 7. Init git repo + initial commit
    ...

    return target_dir
```

### Anti-Patterns to Avoid
- **Running claude interactively from Python:** Always use `claude -p` (print mode). Never try to automate the interactive REPL.
- **Parsing text output from claude -p:** Always use `--output-format json` for reliable parsing. Text output has no guaranteed format.
- **Global state for cost tracking:** Keep cost tracking in SessionState (JSON-persisted). Do not use module-level variables that die on crash.
- **Blocking on rich.Live without cleanup:** Always use try/finally to stop the Live display, or it corrupts the terminal.
- **Hard-coding model names:** Use `--model` flag passthrough from config, not hardcoded model strings.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Disk space monitoring | Custom /proc/diskstats parser | `shutil.disk_usage()` or `psutil.disk_usage()` | Cross-platform, handles mount points correctly |
| Terminal live display | Custom ANSI escape code manipulation | `rich.live.Live` with `rich.table.Table` | Handles resize, flicker-free updates, Windows support |
| Process memory monitoring | Custom /proc/pid/status parser | `psutil.Process().memory_info()` | Cross-platform, handles zombie processes |
| Cost tracking from claude -p | Custom token counting + pricing math | `total_cost_usd` field from `--output-format json` | Authoritative; includes cache tokens, model-specific pricing |
| Graceful shutdown | Custom signal handling boilerplate | `signal.signal(SIGINT, handler)` + context manager pattern | Ensures checkpoint save + git cleanup on Ctrl+C |
| CLI argument parsing | Custom argv parsing | `argparse` (stdlib) | Handles --help, type validation, defaults, error messages |

**Key insight:** Claude Code's `--output-format json` response includes `total_cost_usd` directly -- no need to count tokens and multiply by pricing. The `--max-budget-usd` flag provides per-experiment hard cost caps at the CLI level, so the run engine gets cost control for free.

## Common Pitfalls

### Pitfall 1: claude -p Hanging Without Timeout
**What goes wrong:** `subprocess.run(["claude", "-p", ...])` hangs indefinitely if Claude enters a long tool-use loop or hits API rate limits.
**Why it happens:** No timeout parameter set; Claude retries API errors internally.
**How to avoid:** Always set `timeout` parameter on `subprocess.run()`. Use `--max-turns` to limit agentic turns. Use `--max-budget-usd` for cost protection.
**Warning signs:** Process running for hours on a single experiment.

### Pitfall 2: JSON Parse Failure on claude -p Output
**What goes wrong:** `json.loads(result.stdout)` fails because stderr is mixed into stdout, or the process was killed mid-output.
**Why it happens:** Non-zero exit code, OOM kill, or timeout produces partial/no JSON.
**How to avoid:** Check `result.returncode` first. Wrap JSON parsing in try/except. On timeout, `subprocess.TimeoutExpired` gives partial output via `e.stdout`.
**Warning signs:** `json.JSONDecodeError` in logs.

### Pitfall 3: Rich Live Display Corrupts Terminal on Crash
**What goes wrong:** If the process crashes while `rich.Live` is active, terminal state is corrupted (no cursor, garbled output).
**Why it happens:** Live display uses alternate screen buffer and ANSI codes that need cleanup.
**How to avoid:** Always use `Live` as a context manager or with explicit start/stop in try/finally. Register signal handlers that call `live.stop()`.
**Warning signs:** Terminal becomes unusable after Ctrl+C.

### Pitfall 4: Checkpoint Not Saved Before Experiment
**What goes wrong:** Process crashes during an experiment; on resume, state is from 2+ experiments ago.
**Why it happens:** Checkpoint saved after experiment completion, not before.
**How to avoid:** Call `save_checkpoint()` BEFORE spawning each `claude -p` session. The checkpoint captures "about to run experiment N" state.
**Warning signs:** Resumed sessions repeat already-completed experiments.

### Pitfall 5: Disk Full During Experiment
**What goes wrong:** Claude generates large files (model artifacts, logs), fills disk, causes cascading failures.
**Why it happens:** No disk check between experiments; git objects accumulate.
**How to avoid:** Check `shutil.disk_usage()` before each experiment. Set a minimum free disk threshold (default 1 GB). Stop early if below threshold.
**Warning signs:** `OSError: No space left on device` in logs.

### Pitfall 6: Git State Corruption After Failed Revert
**What goes wrong:** `git_manager.revert_to_last_commit()` fails or is skipped, leaving dirty working tree for next experiment.
**Why it happens:** Exception during revert, or revert called on wrong branch.
**How to avoid:** Verify clean working tree after revert. If dirty, force reset. Log git status after every keep/revert.
**Warning signs:** Experiments build on top of failed/reverted code.

### Pitfall 7: Cost Tracking Across Experiments Losing Data
**What goes wrong:** Cost accumulator resets to zero on resume because it was in-memory only.
**Why it happens:** Cost stored in Python variable, not persisted to JSON.
**How to avoid:** Add `cost_spent_usd` field to SessionState. Persist via the existing `to_json()`/`from_json()` mechanism. Update after each experiment.
**Warning signs:** Budget never reached despite many experiments; resumed sessions report $0 spent.

## Code Examples

### CLI Entry Point
```python
# Source: Derived from old automl/cli.py + mlforge requirements
import argparse
import sys
from pathlib import Path

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mlforge",
        description="Autonomous ML research framework",
    )
    parser.add_argument("dataset", help="Path to dataset (CSV or Parquet)")
    parser.add_argument("goal", help="What to predict or optimize")
    parser.add_argument("--domain", default="tabular", help="Plugin domain")
    parser.add_argument("--metric", default=None, help="Metric to optimize")
    parser.add_argument("--budget-minutes", type=int, default=60)
    parser.add_argument("--budget-usd", type=float, default=5.0)
    parser.add_argument("--budget-experiments", type=int, default=50)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--model", default=None, help="Claude model to use")

    if argv is not None and len(argv) == 0:
        parser.print_usage(sys.stderr)
        return 1

    args = parser.parse_args(argv)
    # ... scaffold + run engine
    return 0
```

### Spawning claude -p with JSON Output
```python
# Source: https://code.claude.com/docs/en/headless
import json
import subprocess

def spawn_experiment(experiment_dir: Path, prompt: str, config: Config) -> dict:
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "json",
        "--allowedTools", "Bash,Read,Edit,Write,Glob,Grep",
        "--dangerously-skip-permissions",
    ]
    if config.max_turns_per_experiment:
        cmd.extend(["--max-turns", str(config.max_turns_per_experiment)])
    if config.per_experiment_budget_usd:
        cmd.extend(["--max-budget-usd", str(config.per_experiment_budget_usd)])
    if config.model:
        cmd.extend(["--model", config.model])
    # Append system prompt with CLAUDE.md content
    cmd.extend(["--append-system-prompt-file", str(experiment_dir / "CLAUDE.md")])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=config.per_experiment_timeout_sec,
            cwd=str(experiment_dir),
        )
        if result.returncode != 0:
            return {"status": "crash", "error": result.stderr[:500]}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": "Exceeded per-experiment timeout"}
    except json.JSONDecodeError:
        return {"status": "crash", "error": "Failed to parse claude output as JSON"}
```

### Extracting Cost from claude -p JSON
```python
# Source: https://platform.claude.com/docs/en/agent-sdk/cost-tracking
def extract_cost(claude_response: dict) -> float:
    """Extract total_cost_usd from claude -p --output-format json response."""
    return claude_response.get("total_cost_usd", 0.0)

def extract_session_id(claude_response: dict) -> str:
    """Extract session_id for potential --resume continuation."""
    return claude_response.get("session_id", "")
```

### Resource Guardrail Check
```python
# Source: psutil docs + shutil stdlib
import shutil
import time

def check_disk_space(path: Path, min_free_gb: float = 1.0) -> bool:
    """Return True if enough disk space remains."""
    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024 ** 3)
    return free_gb >= min_free_gb

def check_wall_clock(start_time: float, budget_minutes: int) -> bool:
    """Return True if within time budget."""
    elapsed_minutes = (time.time() - start_time) / 60
    return elapsed_minutes < budget_minutes
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `claude -p` text output parsing | `claude -p --output-format json` with structured fields | 2025 | Reliable cost tracking, session IDs, structured results |
| Manual token counting for cost | `total_cost_usd` field in JSON response | 2025 | No need to track pricing manually |
| No per-experiment cost limit | `--max-budget-usd` flag | 2025 | Hard cost cap per claude -p invocation |
| No turn limit | `--max-turns` flag | 2025 | Prevents runaway tool-use loops |
| `--append-system-prompt` string only | `--append-system-prompt-file` from file | 2025 | Can inject full CLAUDE.md protocol from file |
| Custom settings file generation | `--settings` flag for passing settings JSON | Recent | Alternative to generating .claude/settings.json |

**Deprecated/outdated:**
- The old `automl` codebase used `automl.runner.ExperimentRunner` to run `train.py` directly. The new pattern runs `claude -p` which itself runs train.py -- this is the "fresh context per iteration" pattern required by CORE-02.

## Open Questions

1. **How does mlforge detect the experiment outcome from claude -p output?**
   - What we know: claude -p returns JSON with `result` (text), `session_id`, `total_cost_usd`. The agent's text result would describe what it did.
   - What's unclear: How to extract the specific metric value from the agent's work. The agent modifies train.py, runs it, and reports results in its text output.
   - Recommendation: After each claude -p call, parse the experiments.jsonl file (which the agent writes to) for the latest entry, OR have the prompt instruct the agent to output a JSON block with the metric. Alternatively, use `--json-schema` to force structured output from the agent.

2. **Should mlforge use `--continue` to maintain session context or fresh sessions each time?**
   - What we know: The requirement says "fresh-context-per-iteration" (CORE-02). `--continue` carries context forward.
   - What's unclear: Whether experiments.md + CLAUDE.md provides enough context, or if session continuation adds value.
   - Recommendation: Use fresh sessions (no `--continue`). The agent reads experiments.md for context -- this is the proven autopilot-ml pattern that prevents context window overflow during overnight runs.

3. **GPU hour tracking for non-tabular domains?**
   - What we know: GUARD-02 mentions GPU hour limits. The tabular plugin is CPU-only.
   - What's unclear: How to track GPU hours when the agent spawns GPU training processes.
   - Recommendation: Defer GPU tracking to Phase 5 (DL plugin). For now, implement the guardrail interface with a no-op GPU check. Add psutil-based nvidia-smi parsing when DL plugin lands.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/mlforge/ -x -q` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-01 | CLI parses args and calls scaffold + engine | unit | `python -m pytest tests/mlforge/test_cli.py -x` | No - Wave 0 |
| CORE-02 | RunEngine spawns claude -p and processes keep/revert | unit (mocked subprocess) | `python -m pytest tests/mlforge/test_engine.py -x` | No - Wave 0 |
| CORE-09 | DeviationHandler retries on crash, reverts on divergence | unit | `python -m pytest tests/mlforge/test_guardrails.py::test_deviation_handler -x` | No - Wave 0 |
| GUARD-01 | Scaffold writes hook files for frozen zones | unit | `python -m pytest tests/mlforge/test_scaffold.py -x` | No - Wave 0 |
| GUARD-02 | ResourceGuardrails stops on cost/disk/time exceeded | unit | `python -m pytest tests/mlforge/test_guardrails.py::test_resource_guardrails -x` | No - Wave 0 |
| GUARD-03 | Checkpoint saved before each experiment | unit | `python -m pytest tests/mlforge/test_engine.py::test_checkpoint_before_experiment -x` | No - Wave 0 |
| GUARD-04 | LiveProgress renders correct state | unit | `python -m pytest tests/mlforge/test_progress.py -x` | No - Wave 0 |
| GUARD-05 | CostTracker accumulates total_cost_usd across experiments | unit | `python -m pytest tests/mlforge/test_guardrails.py::test_cost_tracker -x` | No - Wave 0 |
| INTL-07 | Budget enforcement (experiments, minutes, USD) | unit | `python -m pytest tests/mlforge/test_guardrails.py::test_budget_enforcement -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/mlforge/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/mlforge/test_cli.py` -- covers CORE-01 (CLI parsing, help, missing args)
- [ ] `tests/mlforge/test_scaffold.py` -- covers GUARD-01 (scaffold output structure)
- [ ] `tests/mlforge/test_engine.py` -- covers CORE-02, GUARD-03 (run engine with mocked subprocess)
- [ ] `tests/mlforge/test_guardrails.py` -- covers CORE-09, GUARD-02, GUARD-05, INTL-07
- [ ] `tests/mlforge/test_progress.py` -- covers GUARD-04 (LiveProgress rendering)
- [ ] `tests/mlforge/conftest.py` -- shared fixtures (mock claude -p responses, tmp experiment dirs)

## Sources

### Primary (HIGH confidence)
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) - All CLI flags including `--max-budget-usd`, `--max-turns`, `--output-format`, `--allowedTools`, `--dangerously-skip-permissions`, `--append-system-prompt-file`, `--model`
- [Claude Code Headless Mode](https://code.claude.com/docs/en/headless) - `claude -p` usage patterns, subprocess integration
- [Claude Agent SDK Cost Tracking](https://platform.claude.com/docs/en/agent-sdk/cost-tracking) - `total_cost_usd` field, per-query cost accumulation, cache tokens
- [Rich Live Display Docs](https://rich.readthedocs.io/en/latest/live.html) - Live context manager, refresh rates, custom renderables
- [Python subprocess docs](https://docs.python.org/3/library/subprocess.html) - timeout, capture_output, return codes

### Secondary (MEDIUM confidence)
- [psutil documentation](https://psutil.readthedocs.io/en/latest/) - disk_usage, Process.memory_info, cross-platform resource monitoring
- Old `automl` codebase (cli.py, runner.py, scaffold.py, loop_helpers.py) - Proven patterns for CLI, subprocess execution, keep/revert loop

### Tertiary (LOW confidence)
- GPU hour tracking approach (deferred to Phase 5; nvidia-smi parsing via psutil not verified)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib (argparse, subprocess) + well-established libraries (rich, psutil)
- Architecture: HIGH - patterns proven in old automl code + official claude -p docs
- Pitfalls: HIGH - derived from production experience with the old codebase
- Claude -p integration: HIGH - verified against official docs (cli-reference, headless mode, cost-tracking)

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable domain; claude CLI flags are the only moving target)
