# Phase 22: Fix Swarm State Enforcement - Research

**Researched:** 2026-03-21
**Domain:** Swarm agent result collection, state persistence, fault tolerance
**Confidence:** HIGH

## Summary

Phase 22 closes INT-SWARM-STATE from the v1.0 audit. The core problem: `SwarmManager.run()` reads `state.json` from each agent worktree after agents complete, but `state.json` is only written by the AI agent following a text instruction in `swarm_claude.md.j2`. If the agent skips, crashes, or misformats the write, results are silently lost (the `except` clause at line 139 of `swarm/__init__.py` catches and passes).

The fix has two parts: (1) make the engine write `state.json` programmatically so it exists regardless of AI compliance, and (2) add fallback logic in `SwarmManager.run()` to extract results from `checkpoint.json` when `state.json` is missing/malformed.

**Primary recommendation:** Add a `_write_state_json()` call in `RunEngine`'s checkpoint-save path (the engine already calls `save_checkpoint()` which writes `checkpoint.json` with the same data), and add checkpoint.json fallback in `SwarmManager.run()`'s result collection loop.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SWARM-02 | File-locked scoreboard coordinates best result across parallel agents | Scoreboard itself works; the gap is that agents may not produce state.json for the coordinator to read. Fix: programmatic state.json write + checkpoint.json fallback ensures scoreboard always gets populated. |
| SWARM-03 | Budget inheritance prevents spawn explosion -- child agents inherit parent's remaining budget | Budget inheritance works (tested). The gap is that results from budget-constrained agents may be lost if state.json missing. Fix: same fallback mechanism ensures results are collected even on crash/non-compliance. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mlforge.state | existing | SessionState dataclass with to_json/from_json | Already has atomic write-then-rename via `.json.tmp` pattern |
| mlforge.checkpoint | existing | save_checkpoint/load_checkpoint with schema versioning | Already writes checkpoint.json in `.mlforge/` directory -- same location swarm reads state.json |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | n/a | JSON serialization | Already used throughout |
| pathlib (stdlib) | n/a | Path manipulation | Already used throughout |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Writing state.json from engine | Writing from CLAUDE.md template only | Current approach -- unreliable, text-instruction-only |
| checkpoint.json fallback | Re-running agent | Too expensive, defeats purpose of fault tolerance |

## Architecture Patterns

### Current Architecture (The Problem)

```
SwarmManager.run()
  -> spawns N claude -p subprocesses (leaf agents)
  -> each agent follows swarm_claude.md.j2 text instruction to write state.json
  -> SwarmManager reads state.json from each worktree after all agents complete
  -> If state.json missing/malformed: silently skipped (pass in except block)
  -> Results lost if AI agent doesn't comply
```

**Key files and their roles:**
- `src/mlforge/swarm/__init__.py:121-139` -- Result collection loop (the fragile part)
- `src/mlforge/swarm/scoreboard.py` -- File-locked TSV scoreboard (works correctly)
- `src/mlforge/engine.py:111,119` -- `save_checkpoint()` called before each experiment and in finally block
- `src/mlforge/state.py` -- SessionState with `to_json()` method (currently dead code per audit)
- `src/mlforge/checkpoint.py` -- `save_checkpoint()` writes checkpoint.json with `{"schema_version": 1, "state": {...}, "timestamp": "..."}`
- `src/mlforge/templates/swarm_claude.md.j2` -- Text instruction telling agent to write state.json

### Recommended Fix Architecture

```
RunEngine (running inside agent subprocess in worktree)
  -> save_checkpoint() already writes .mlforge/checkpoint.json after each experiment
  -> ADD: also write .mlforge/state.json with {best_metric, best_commit, experiment_count}
  -> This happens programmatically in engine code, not AI text instruction

SwarmManager.run() result collection
  -> Try reading .mlforge/state.json (primary, backwards compatible)
  -> If missing/malformed: fallback to .mlforge/checkpoint.json
  -> Extract best_metric, best_commit from checkpoint state dict
  -> If both missing: log warning, skip agent (explicit, not silent)
```

### Pattern: Programmatic State Write in Engine

The engine already writes checkpoint.json via `save_checkpoint(self.state, self._checkpoint_dir)` at two points:
1. Before each experiment iteration (line 111)
2. In the finally block after the loop ends (line 119)

The `state.json` write should happen at the same points, using `SessionState.to_json()` which is currently dead code (noted in tech_debt section of audit). This revives dead code while solving the problem.

### Pattern: Fallback Chain in Result Collection

```python
# In SwarmManager.run(), replace the current state.json-only read:
for i, _proc in enumerate(self._processes):
    metric, commit = self._collect_agent_result(i)
    if metric is not None:
        self.scoreboard.publish_result(...)

def _collect_agent_result(self, agent_index: int) -> tuple[float | None, str]:
    """Try state.json first, fall back to checkpoint.json."""
    wt_path = self._worktree_paths[agent_index]
    mlforge_dir = wt_path / ".mlforge"

    # Primary: state.json
    state_path = mlforge_dir / "state.json"
    result = self._read_state_json(state_path)
    if result is not None:
        return result

    # Fallback: checkpoint.json
    checkpoint_path = mlforge_dir / "checkpoint.json"
    result = self._read_checkpoint_json(checkpoint_path)
    if result is not None:
        return result

    return None, ""
```

### Anti-Patterns to Avoid
- **Silent failure on missing state:** Current `pass` in except block loses results without warning. Replace with explicit logging or at minimum a fallback attempt.
- **Relying on AI text compliance for infrastructure:** The core principle of this fix -- never rely on AI agent following a text instruction for critical state persistence.
- **Duplicate serialization logic:** Use existing `SessionState.to_json()` rather than hand-rolling JSON writes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| State JSON serialization | Manual json.dumps of selected fields | `SessionState.to_json()` | Already exists, uses atomic write-then-rename, forward-compatible |
| Checkpoint reading | Manual JSON parsing | `load_checkpoint()` from checkpoint.py | Already handles schema versioning and unknown field filtering |

**Key insight:** The checkpoint module already writes everything needed. The state.json write is just a thin wrapper calling `SessionState.to_json()`. The fallback reader just calls `load_checkpoint()` and extracts `best_metric`/`best_commit`.

## Common Pitfalls

### Pitfall 1: Breaking Swarm Agents That Don't Use RunEngine
**What goes wrong:** Swarm agents are spawned as `claude -p` subprocesses. They don't necessarily use `RunEngine` -- the agent is an AI that runs code directly. The engine is only used when mlforge orchestrates the loop.
**Why it happens:** Swarm agents ARE leaf agents running `claude -p`, not mlforge engine instances. The swarm template tells them to manually write state.json because there's no engine managing them.
**How to avoid:** The programmatic write must happen from the swarm agent's perspective. Two approaches: (a) add a post-experiment hook to the train template that writes state.json, or (b) have the swarm manager write state.json by parsing the agent's subprocess output (which is JSON from `--output-format json`).
**Warning signs:** If tests mock RunEngine but agents don't actually use it, the fix won't work in production.

### Pitfall 2: Checkpoint.json Schema Mismatch
**What goes wrong:** `checkpoint.json` wraps state in `{"schema_version": 1, "state": {...}}` while `state.json` is flat `{"best_metric": ..., "best_commit": ..., "experiment_count": ...}`.
**Why it happens:** Different serialization paths for the same data.
**How to avoid:** The fallback reader must know to look inside `data["state"]` for checkpoint.json, not at the top level.

### Pitfall 3: Agent Subprocess Output Already Contains Results
**What goes wrong:** Ignoring that `claude -p --output-format json` returns JSON with `result` key containing the agent's output, which may include metric_value.
**Why it happens:** The current code waits for all processes then reads files, but subprocess output is available via `proc.communicate()` or `proc.stdout`.
**How to avoid:** Consider parsing the subprocess return value directly as the most reliable source -- it's generated by claude itself, not dependent on file writes.

## Code Examples

### Current Result Collection (fragile)
```python
# src/mlforge/swarm/__init__.py:121-139
for i, _proc in enumerate(self._processes):
    if i < len(self._worktree_paths):
        state_path = self._worktree_paths[i] / ".mlforge" / "state.json"
        if state_path.exists():
            try:
                agent_state = json.loads(state_path.read_text())
                metric = agent_state.get("best_metric")
                commit = agent_state.get("best_commit", "")
                if metric is not None:
                    self.scoreboard.publish_result(...)
            except (json.JSONDecodeError, OSError):
                pass  # Agent crashed or state corrupted -- RESULTS LOST
```

### SessionState.to_json() (existing, currently dead code)
```python
# src/mlforge/state.py:31-37
def to_json(self, path: Path) -> None:
    """Atomic write: write to .tmp file then rename."""
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(asdict(self), indent=2) + "\n")
    tmp.rename(path)
```

### Checkpoint Structure (fallback source)
```python
# src/mlforge/checkpoint.py -- payload written:
{
    "schema_version": 1,
    "state": {
        "experiment_count": 5,
        "best_metric": 0.92,
        "best_commit": "abc123",
        "budget_remaining": 3.0,
        # ... all SessionState fields
    },
    "timestamp": "2026-03-21T..."
}
```

### Recommended: Enhanced Result Collection with Fallback
```python
def _collect_agent_result(self, agent_index: int) -> tuple[float | None, str]:
    """Collect best result from agent, trying multiple sources."""
    wt_path = self._worktree_paths[agent_index]
    mlforge_dir = wt_path / ".mlforge"

    # Source 1: state.json (written by agent or engine)
    state_path = mlforge_dir / "state.json"
    if state_path.exists():
        try:
            data = json.loads(state_path.read_text())
            metric = data.get("best_metric")
            if metric is not None:
                return float(metric), data.get("best_commit", "")
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    # Source 2: checkpoint.json (written by engine's save_checkpoint)
    checkpoint_path = mlforge_dir / "checkpoint.json"
    if checkpoint_path.exists():
        try:
            data = json.loads(checkpoint_path.read_text())
            state_data = data.get("state", {})
            metric = state_data.get("best_metric")
            if metric is not None:
                return float(metric), state_data.get("best_commit", "")
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    return None, ""
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Text instruction only (state.json) | Programmatic write + fallback chain | Phase 22 | Swarm results reliably collected even if AI agent non-compliant |
| Silent skip on missing state | Explicit fallback with checkpoint.json | Phase 22 | No silent result loss |
| SessionState.to_json() dead code | Revived for state.json writes | Phase 22 | Removes tech debt item |

## Critical Design Decision: Where Does State.json Get Written?

The swarm agents run as `claude -p` subprocesses -- they are AI agents, NOT RunEngine instances. The swarm manager spawns them via `subprocess.Popen`. This means:

**Option A: Write state.json from SwarmManager after agent completes (RECOMMENDED)**
- Parse the subprocess output (already JSON from `--output-format json`)
- Extract metric_value from the claude output
- Write state.json programmatically from SwarmManager
- Pro: Works regardless of what the agent does inside
- Pro: SwarmManager already has access to worktree paths
- Con: Requires parsing claude's JSON envelope for the result

**Option B: Write state.json from within train.py template**
- Add state.json write to train template code
- Pro: Happens at source
- Con: Only works if agent runs train.py successfully and doesn't modify the write
- Con: Template changes affect non-swarm runs

**Option C: Have SwarmManager capture subprocess output**
- Change `proc.wait()` to `proc.communicate()` to capture stdout
- Parse the JSON output for metric_value
- Write state.json + publish to scoreboard directly
- Pro: Most reliable -- captures output regardless of file system state
- Pro: Already getting JSON output via `--output-format json`
- Con: Need to handle Popen stdout capture for parallel processes

**Recommendation: Option C (capture subprocess output) combined with checkpoint.json fallback**
- Change Popen to capture stdout (pipe)
- After each agent completes, parse stdout JSON for metric/result
- Write state.json from SwarmManager AND publish to scoreboard directly
- Keep checkpoint.json fallback for crash cases where subprocess output is lost

## Open Questions

1. **Subprocess Output Capture with Parallel Agents**
   - What we know: Current code uses `proc.wait()` which discards stdout. Using `stdout=subprocess.PIPE` with Popen enables capture.
   - What's unclear: Whether long-running agents might have buffer issues with piped stdout.
   - Recommendation: Use `stdout=subprocess.PIPE` and read after `proc.wait()` returns. Buffer size is unlikely an issue since `--output-format json` produces compact output.

2. **Should state.json Text Instruction Be Removed from Template?**
   - What we know: After this fix, state.json will be written programmatically.
   - What's unclear: Whether removing the template instruction could break anything else.
   - Recommendation: Keep the template instruction as defense-in-depth but it's no longer the primary mechanism.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml [tool.pytest] |
| Quick run command | `python3 -m pytest tests/mlforge/test_mlforge_swarm.py tests/mlforge/test_swarm.py -x -q` |
| Full suite command | `python3 -m pytest tests/mlforge/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SWARM-02 | Scoreboard populated even without AI-written state.json | unit | `python3 -m pytest tests/mlforge/test_swarm_state_enforcement.py::test_result_collection_from_subprocess_output -x` | No -- Wave 0 |
| SWARM-02 | Fallback to checkpoint.json when state.json missing | unit | `python3 -m pytest tests/mlforge/test_swarm_state_enforcement.py::test_fallback_to_checkpoint -x` | No -- Wave 0 |
| SWARM-02 | Handles malformed state.json gracefully | unit | `python3 -m pytest tests/mlforge/test_swarm_state_enforcement.py::test_malformed_state_json -x` | No -- Wave 0 |
| SWARM-03 | Budget-split agents produce scoreboard entries even on non-compliance | unit | `python3 -m pytest tests/mlforge/test_swarm_state_enforcement.py::test_budget_agents_result_collection -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/mlforge/test_mlforge_swarm.py tests/mlforge/test_swarm.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/mlforge/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/mlforge/test_swarm_state_enforcement.py` -- covers SWARM-02, SWARM-03 with fallback and subprocess capture tests
- Existing test infrastructure (fixtures, conftest) is sufficient -- no additional setup needed

## Sources

### Primary (HIGH confidence)
- Source code: `src/mlforge/swarm/__init__.py` -- SwarmManager.run() result collection (lines 121-139)
- Source code: `src/mlforge/engine.py` -- RunEngine checkpoint save pattern (lines 111, 119)
- Source code: `src/mlforge/state.py` -- SessionState.to_json() dead code (lines 31-37)
- Source code: `src/mlforge/checkpoint.py` -- save_checkpoint/load_checkpoint schema
- Source code: `src/mlforge/templates/swarm_claude.md.j2` -- text instruction for state.json
- Audit: `.planning/v1.0-MILESTONE-AUDIT.md` -- INT-SWARM-STATE gap definition

### Secondary (MEDIUM confidence)
- Existing tests: `tests/mlforge/test_swarm.py` (31 passing) -- current coverage baseline
- Existing tests: `tests/mlforge/test_mlforge_swarm.py` -- Phase 14 flag tests

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all code is internal, fully readable
- Architecture: HIGH - clear problem with clear fix paths, all code reviewed
- Pitfalls: HIGH - identified the critical subtlety (agents are not RunEngine instances)

**Research date:** 2026-03-21
**Valid until:** Indefinite (internal codebase, no external dependencies)
