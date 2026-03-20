# Phase 14: Fix Swarm Agent Subprocess - Research

**Researched:** 2026-03-20
**Domain:** Subprocess orchestration, claude CLI flags, git worktree file management
**Confidence:** HIGH

## Summary

Phase 14 fixes four specific gaps in `src/mlforge/swarm/__init__.py` that prevent swarm mode from working end-to-end. The current `_build_agent_command()` method returns a bare `["claude", "-p", prompt]` command missing permission flags, budget enforcement, and system prompt injection. Additionally, worktrees lack the CLAUDE.md protocol file that agents need to follow experiment rules, and agents have no mechanism to write `state.json` so the scoreboard can read results.

The engine module (`src/mlforge/engine.py` lines 158-168) already demonstrates the correct subprocess pattern: `--dangerously-skip-permissions`, `--max-budget-usd`, `--output-format json`, and `--append-system-prompt`. The swarm command builder just needs to follow the same pattern. CLAUDE.md must be copied into each worktree during `setup()`, and the swarm protocol template must instruct agents to persist state.json.

**Primary recommendation:** Mirror the engine's `_run_one_experiment()` CLI flags in `_build_agent_command()`, copy CLAUDE.md into worktrees during `setup()`, and add state.json write instruction to the swarm template.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SWARM-01 | Swarm mode spawns parallel agents in git worktrees exploring different model families simultaneously | _build_agent_command() needs --dangerously-skip-permissions so agents can actually write files in worktrees |
| SWARM-02 | File-locked scoreboard coordinates best result across parallel agents | Agents must write state.json so run() can read results and publish to scoreboard (lines 114-131 of swarm/__init__.py) |
| SWARM-03 | Budget inheritance prevents spawn explosion -- child agents inherit parent's remaining budget | _build_agent_command() must pass --max-budget-usd with child_config.budget_usd to enforce per-agent budget |
| SWARM-04 | Verification agent checks metric improvement claims against actual holdout performance | Agents need state.json with best_metric and best_commit for verifier to have data to check |
</phase_requirements>

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| subprocess | stdlib | Spawn claude CLI agents | Already used in swarm/__init__.py and engine.py |
| shutil | stdlib | Copy CLAUDE.md to worktrees | Already used in scaffold.py |
| pathlib | stdlib | Path manipulation | Already used everywhere |
| GitPython | existing | Worktree management | Already used in swarm module |

### No New Dependencies
This phase requires zero new libraries. All fixes are wiring changes to existing code.

## Architecture Patterns

### Pattern 1: Engine CLI Flag Pattern (the model to follow)
**What:** The engine already builds the correct claude subprocess command
**When to use:** Wherever claude -p is spawned
**Example:**
```python
# Source: src/mlforge/engine.py lines 158-168
cmd = [
    "claude",
    "-p", prompt,
    "--output-format", "json",
    "--dangerously-skip-permissions",
    "--max-budget-usd", str(self.config.per_experiment_budget_usd),
]
if system_prompt:
    cmd.extend(["--append-system-prompt", system_prompt])
```

### Pattern 2: Current Broken Swarm Command
**What:** The swarm _build_agent_command() returns a bare command
**Where:** `src/mlforge/swarm/__init__.py` lines 157-181
```python
# CURRENT (broken): missing all required flags
return ["claude", "-p", prompt]
```

### Pattern 3: CLAUDE.md Copy During Setup
**What:** Copy protocol file into worktrees so agents have context
**When to use:** During setup() after worktree creation
```python
# Copy CLAUDE.md to each worktree
claude_md_src = self.experiment_dir / "CLAUDE.md"
if claude_md_src.exists():
    shutil.copy2(claude_md_src, wt_path / "CLAUDE.md")
```

### Pattern 4: State.json Write in Swarm Template
**What:** Template instructs agent to write state.json so scoreboard can read results
**Where:** `src/mlforge/templates/swarm_claude.md.j2`
```markdown
## State Persistence
After each experiment, write your current state to `.mlforge/state.json`:
{"best_metric": <value>, "best_commit": "<hash>", "experiment_count": N}
```

### Anti-Patterns to Avoid
- **Reading CLAUDE.md from parent dir in worktree:** Git worktrees are isolated checkouts -- they do not share untracked files with the parent. CLAUDE.md must be physically copied in.
- **Passing budget in prompt text only:** Text instructions are advisory; `--max-budget-usd` is enforced by the claude CLI itself.
- **Using `--cwd` flag:** This was already identified as invalid in Phase 10 and removed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Budget enforcement | Prompt text telling agent to stop | `--max-budget-usd` CLI flag | Claude CLI enforces it at the API level |
| Permission management | Custom file permission system | `--dangerously-skip-permissions` | Agents need to write files; hooks handle frozen enforcement |
| State serialization | Custom format | SessionState.to_json() pattern | Already proven, JSON with atomic write |

## Common Pitfalls

### Pitfall 1: Worktrees Don't Share Untracked Files
**What goes wrong:** CLAUDE.md is generated during scaffold into experiment_dir but worktrees are git checkouts of tracked commits. Untracked files (CLAUDE.md, experiments.md, dataset) are NOT present in worktrees.
**Why it happens:** Git worktrees share the .git database but each gets its own working tree from the commit.
**How to avoid:** Explicitly copy CLAUDE.md (and potentially the dataset, mlforge.config.toml) into each worktree during setup().
**Warning signs:** Agents running without protocol rules, producing unstructured output.

### Pitfall 2: state.json Directory Must Exist
**What goes wrong:** Agent tries to write `.mlforge/state.json` but `.mlforge/` directory does not exist in the worktree.
**Why it happens:** `.mlforge/` is created by checkpoint code in engine.py, not by scaffold.
**How to avoid:** Create `.mlforge/` directory in each worktree during setup(), or instruct template to create it.

### Pitfall 3: --append-system-prompt Content Size
**What goes wrong:** CLAUDE.md can be large; passing as --append-system-prompt inline string may hit shell argument length limits.
**Why it happens:** CLAUDE.md for tabular can be 2-3KB, well within typical ARG_MAX (~2MB on Linux), but worth noting.
**How to avoid:** Engine already uses this pattern successfully. Just follow the same approach.

### Pitfall 4: Budget Math for Child Agents
**What goes wrong:** Child budget_usd used for --max-budget-usd but per_experiment_budget_usd passed instead.
**Why it happens:** Config has both budget_usd (total) and per_experiment_budget_usd (per experiment).
**How to avoid:** Pass child_config.budget_usd as the total session budget for the agent. The agent's own engine handles per-experiment budgeting internally. Since swarm agents run as full claude -p sessions (not engine loops), use child_config.budget_usd directly.

### Pitfall 5: Old Tests Reference automl.swarm, Not mlforge.swarm
**What goes wrong:** test_swarm.py imports from `automl.swarm` and tests `spawn_agent` function (old API).
**Why it happens:** Tests were written for the v1-v3 codebase, not the current mlforge rewrite.
**How to avoid:** New tests for Phase 14 should test `mlforge.swarm.SwarmManager._build_agent_command()` directly. Old tests can be left as-is (they pass and test old code).

## Code Examples

### Fix 1: _build_agent_command() with Required Flags
```python
# Source: pattern from engine.py adapted for swarm
def _build_agent_command(
    self, agent_index: int, child_config: Config
) -> list[str]:
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

    # Read CLAUDE.md from worktree (copied there during setup)
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
```

### Fix 2: Copy CLAUDE.md in setup()
```python
# Inside setup() loop, after worktree creation:
import shutil

claude_md_src = self.experiment_dir / "CLAUDE.md"
for wt_path in self._worktree_paths:
    if claude_md_src.exists():
        shutil.copy2(claude_md_src, wt_path / "CLAUDE.md")
    # Ensure .mlforge dir exists for state.json writes
    (wt_path / ".mlforge").mkdir(parents=True, exist_ok=True)
```

### Fix 3: Swarm Template State Persistence Rule
```markdown
## State Persistence
After each successful experiment, update `.mlforge/state.json` with:
```json
{
  "best_metric": <your best metric value>,
  "best_commit": "<git commit hash of best experiment>",
  "experiment_count": <number of experiments run>
}
```
This file is read by the swarm coordinator to publish your results to the scoreboard.
```

## Key Analysis: What the Swarm run() Method Already Does

The `run()` method in `swarm/__init__.py` (lines 88-153) already has the right *reading* logic:
1. Spawns agents (lines 104-107)
2. Waits for completion (lines 110-111)
3. Reads each agent's `.mlforge/state.json` (lines 114-131)
4. Publishes results to scoreboard
5. Reads best from scoreboard
6. Runs verification

The gap is that agents never *write* state.json because:
- They lack permissions (no `--dangerously-skip-permissions`)
- They lack budget enforcement (no `--max-budget-usd`)
- They lack protocol context (no CLAUDE.md in worktree)
- They lack instruction to write state.json (template doesn't mention it)

## Files That Need Changes

| File | Change | Reason |
|------|--------|--------|
| `src/mlforge/swarm/__init__.py` | Add flags to `_build_agent_command()`, copy CLAUDE.md in `setup()` | SWARM-01, SWARM-03 |
| `src/mlforge/templates/swarm_claude.md.j2` | Add state.json write instruction | SWARM-02, SWARM-04 |
| `tests/test_swarm.py` or new `tests/test_mlforge_swarm.py` | Test new command flags, CLAUDE.md copy, state.json template | All requirements |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml |
| Quick run command | `python3 -m pytest tests/test_swarm_scoreboard.py tests/test_swarm_claims.py -x -q` |
| Full suite command | `python3 -m pytest -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SWARM-01 | _build_agent_command includes --dangerously-skip-permissions | unit | `python3 -m pytest tests/test_mlforge_swarm.py::TestBuildAgentCommand::test_includes_skip_permissions -x` | Wave 0 |
| SWARM-02 | state.json template instruction exists, scoreboard reads it | unit | `python3 -m pytest tests/test_mlforge_swarm.py::TestBuildAgentCommand::test_template_has_state_json -x` | Wave 0 |
| SWARM-03 | --max-budget-usd passed with child budget | unit | `python3 -m pytest tests/test_mlforge_swarm.py::TestBuildAgentCommand::test_includes_max_budget -x` | Wave 0 |
| SWARM-04 | CLAUDE.md copied to worktrees, agents can write state | unit | `python3 -m pytest tests/test_mlforge_swarm.py::TestSetup::test_copies_claude_md -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_mlforge_swarm.py -x -q`
- **Per wave merge:** `python3 -m pytest -x -q`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
- [ ] `tests/test_mlforge_swarm.py` -- new test file for mlforge.swarm module (existing test_swarm.py tests automl.swarm, different API)
- [ ] Tests for _build_agent_command() flag verification
- [ ] Tests for setup() CLAUDE.md copy behavior
- [ ] Test for swarm_claude.md.j2 state.json instruction

## Open Questions

1. **Should dataset and config.toml also be copied to worktrees?**
   - What we know: CLAUDE.md is critical (agents need protocol). Worktrees get tracked files from git but not untracked scaffold artifacts.
   - What's unclear: Whether agents need the dataset directly or if the protocol prompt is sufficient guidance.
   - Recommendation: Copy CLAUDE.md at minimum. The dataset is tracked (copied by scaffold then committed by git init), so it should be in worktrees. Config.toml is also tracked. Only CLAUDE.md is generated post-commit and needs explicit copying.

2. **Should swarm agents use --output-format json?**
   - What we know: Engine uses it. Swarm run() reads state.json not stdout.
   - What's unclear: Whether stdout parsing matters for swarm agents.
   - Recommendation: Include it for consistency -- the run() method doesn't parse stdout, but having structured output makes debugging easier.

## Sources

### Primary (HIGH confidence)
- `src/mlforge/swarm/__init__.py` -- current broken implementation, read directly
- `src/mlforge/engine.py` -- working subprocess pattern (lines 158-168)
- `src/mlforge/templates/swarm_claude.md.j2` -- current template missing state instructions
- `src/mlforge/state.py` -- SessionState JSON format
- `tests/test_swarm.py` -- existing tests (for old automl.swarm API)

### Secondary (MEDIUM confidence)
- Claude CLI flags (`--dangerously-skip-permissions`, `--max-budget-usd`, `--append-system-prompt`) verified via engine.py usage

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all wiring changes
- Architecture: HIGH -- engine.py provides exact pattern to follow
- Pitfalls: HIGH -- gaps identified by reading source code directly

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable -- internal wiring, no external dependencies)
