# Phase 13: Wire Dead Code + Rich Profile Display - Research

**Researched:** 2026-03-20
**Domain:** Dead code wiring (git_ops.tag_best, swarm scoreboard.publish_result) + CLI profile display
**Confidence:** HIGH

## Summary

Phase 13 closes three audit gaps by wiring existing but orphaned functions into their intended call sites: (1) `GitManager.tag_best()` at engine session end, (2) `SwarmScoreboard.publish_result()` in the swarm agent completion path, and (3) `DatasetProfile` rich fields into CLI output. All three functions already exist, are tested in isolation, and have stable APIs. The work is purely integration wiring -- no new modules or libraries needed.

The key challenge is identifying the correct call sites. `tag_best()` belongs in `RunEngine.run()` after the experiment loop, using `state.best_commit` and `state.run_id`. `publish_result()` belongs in `SwarmManager.run()` after each agent completes (reading results from worktree state). The CLI profile display is a straightforward expansion of the existing `print()` call in `cli.py` that currently shows only task/metric/rows/features.

**Primary recommendation:** Wire three existing functions to their call sites with guard conditions, expand one print statement. No new modules or dependencies.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CORE-10 | Git-based state management: branch per run, commit per kept experiment, reset on revert, tag best model | `tag_best()` exists in `git_ops.py:77`, tested in `test_git_ops.py:92`. Wire into `engine.py` post-loop. Branch/commit/revert already wired in phases 1-7. |
| SWARM-01 | Swarm mode spawns parallel agents in git worktrees exploring different model families simultaneously | Swarm spawning works. `publish_result()` exists in `scoreboard.py:49`. Wire into `SwarmManager.run()` after agent completion. |
| SWARM-02 | File-locked scoreboard coordinates best result across parallel agents | `SwarmScoreboard` class fully implemented with `fcntl.LOCK_EX`. `publish_result()` is the write path -- currently dead code. Wiring it makes the scoreboard active. |
| UX-04 | Dataset profiling analyzes schema, feature types, target distribution, and temporal patterns before experiments start | `DatasetProfile` has `missing_pct`, `numeric_features`, `categorical_features`, `leakage_warnings` fields. CLI currently prints only task/metric/rows/features. Expand print. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| GitPython | >=3.1 | `tag_best()` uses `repo.create_tag()` | Already used throughout `git_ops.py` |

### Supporting
No new libraries needed. All work uses existing mlforge modules.

## Architecture Patterns

### Pattern 1: Post-Loop Finalization in Engine
**What:** `RunEngine.run()` already has a `finally` block that exports artifacts and writes retrospective. `tag_best()` wiring follows the same pattern.
**When to use:** After the experiment loop completes, before `git.close()`.
**Example:**
```python
# In engine.py RunEngine.run(), inside the finally block, before git.close()
if self.state.best_commit:
    tag_name = f"best-{self.state.run_id or 'unknown'}"
    try:
        self.git.tag_best(tag_name, f"Best experiment: {self.state.best_metric}")
    except ValueError:
        pass  # Tag already exists (resume case)
```

**Key details:**
- Guard on `self.state.best_commit` being non-None (no experiments kept = no tag)
- Guard on `self.state.run_id` being available for the tag name
- Catch `ValueError` for idempotency (tag already exists on resume)
- Tag format: `best-{run_id}` per success criteria #4
- Must happen before `self.git.close()` (line 123 in current engine.py)

### Pattern 2: Swarm Agent Result Collection
**What:** After `proc.wait()` for each agent, read the agent's results from its worktree and call `publish_result()`.
**When to use:** In `SwarmManager.run()` after agent subprocess completes.

**Key challenge:** The swarm agents are `claude -p` subprocesses. Their results need to be extracted somehow. Current architecture has agents writing to the worktree. Options:
1. Read agent's `results.jsonl` from its worktree after completion
2. Have the agent protocol template instruct agents to write to the scoreboard directly (current approach via text protocol -- but this is what GAP-7 identified as insufficient)
3. Read agent's state JSON from worktree's `.mlforge/state.json`

**Recommended approach:** After each agent process completes, read the agent's `results.jsonl` or `state.json` from the worktree to get best metric/commit, then call `scoreboard.publish_result()` programmatically. This ensures the scoreboard is populated even if the agent's text-based protocol fails to write to it.

```python
# In SwarmManager.run(), after proc.wait()
for i, proc in enumerate(self._processes):
    proc.wait()
    wt_path = self._worktree_paths[i]
    state_path = wt_path / ".mlforge" / "state.json"
    if state_path.exists():
        import json
        agent_state = json.loads(state_path.read_text())
        metric = agent_state.get("best_metric")
        commit = agent_state.get("best_commit", "")
        if metric is not None:
            self.scoreboard.publish_result(
                agent=f"agent-{i}",
                commit=commit or "",
                metric_value=metric,
                elapsed_sec=0.0,  # or compute from timestamps
                status="complete",
                description=f"Agent {i} best result",
            )
```

### Pattern 3: Rich CLI Profile Display
**What:** Expand the single `print()` line in `cli.py:169-172` to show additional DatasetProfile fields.
**When to use:** In the simple mode branch when profiling succeeds.

```python
# Current (line 169-172):
print(
    f"Auto-detected: {profile.task} task, metric={profile.metric}, "
    f"{profile.n_rows} rows, {profile.n_features} features"
)

# Expanded:
print(f"Auto-detected: {profile.task} task, metric={profile.metric}")
print(f"  Rows: {profile.n_rows}, Features: {profile.n_features}")
print(f"  Numeric: {len(profile.numeric_features)}, Categorical: {len(profile.categorical_features)}")
print(f"  Missing: {profile.missing_pct:.1f}%")
if profile.leakage_warnings:
    for warning in profile.leakage_warnings:
        print(f"  WARNING: {warning}")
```

### Anti-Patterns to Avoid
- **Tagging without guard:** `tag_best()` raises `ValueError` if tag exists. Must catch or check first.
- **Tagging when no best exists:** If all experiments were reverted, `state.best_commit` is None. Must guard.
- **Assuming scoreboard file exists:** `publish_result()` creates the file if needed, but the `.swarm/` directory must exist.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Git tagging | Custom git subprocess calls | `GitManager.tag_best()` | Already handles duplicate check, annotated tags |
| Scoreboard writes | Direct TSV file manipulation | `SwarmScoreboard.publish_result()` | Already handles fcntl locking, atomic writes, header creation |

## Common Pitfalls

### Pitfall 1: Tag on Detached HEAD
**What goes wrong:** If stagnation branching left the repo in a detached HEAD state, tagging still works (tags point to commits, not branches).
**How to avoid:** No action needed -- `repo.create_tag()` works on detached HEAD.

### Pitfall 2: Resume Creates Duplicate Tag
**What goes wrong:** If a session is resumed, the engine might try to create `best-{run_id}` again.
**How to avoid:** Catch `ValueError` from `tag_best()` when tag already exists. Or check `self.repo.tags` first.

### Pitfall 3: Swarm Agent State File Missing
**What goes wrong:** If a swarm agent crashes before writing state, `state.json` won't exist in the worktree.
**How to avoid:** Guard `state_path.exists()` before reading. Skip agents with no state.

### Pitfall 4: leakage_warnings Never Populated
**What goes wrong:** `DatasetProfile.leakage_warnings` defaults to empty list and is never populated by `profile_dataset()`. Displaying it will always show nothing.
**How to avoid:** This is acceptable for now -- the field is a forward-compatible placeholder. The CLI code should handle it (print only if non-empty), so when leakage detection is added later, it will display automatically.

## Code Examples

### tag_best() API (from git_ops.py:77)
```python
def tag_best(self, tag_name: str, message: str = "") -> None:
    """Create an annotated tag on the current HEAD.
    Raises ValueError if tag already exists.
    """
    existing_tags = [t.name for t in self.repo.tags]
    if tag_name in existing_tags:
        raise ValueError(f"Tag '{tag_name}' already exists")
    self.repo.create_tag(tag_name, message=message)
```

### publish_result() API (from scoreboard.py:49)
```python
def publish_result(
    self,
    agent: str,
    commit: str,
    metric_value: float,
    elapsed_sec: float,
    status: str,
    description: str,
) -> bool:
    """Append a result row and return True if it is a new global best.
    Uses fcntl.LOCK_EX for atomic read-check-write.
    """
```

### Current CLI profile print (cli.py:169-172)
```python
print(
    f"Auto-detected: {profile.task} task, metric={profile.metric}, "
    f"{profile.n_rows} rows, {profile.n_features} features"
)
```

### State fields available (state.py)
```python
best_metric: float | None = None
best_commit: str | None = None
```

## State of the Art

No changes needed -- all APIs are stable and tested. This phase is purely integration wiring.

## Open Questions

1. **Swarm agent result extraction**
   - What we know: Agents are `claude -p` subprocesses in worktrees. They should write state/results.
   - What's unclear: Do agents actually save state.json to their worktree? The engine saves checkpoints, but swarm agents run through `claude -p` prompt, not through `RunEngine`.
   - Recommendation: Read `results.jsonl` or parse `claude -p` JSON output from each agent process. If neither available, fall back to scoreboard-only reads (current behavior). The swarm template already tells agents to write to the scoreboard path -- `publish_result()` call should be a programmatic backup.

2. **run_id availability for tag name**
   - What we know: `SessionState.run_id` is set in `cli.py` before engine creation.
   - What's unclear: Could `run_id` ever be None at tag time?
   - Recommendation: Default to `"unknown"` if None. `run_id` is always set in normal flow.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/mlforge/test_engine.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-10 | tag_best() called at session end with best-{run_id} | unit | `python -m pytest tests/mlforge/test_engine.py -x -q -k tag_best` | Wave 0 |
| CORE-10 | tag_best() skipped when no best_commit | unit | `python -m pytest tests/mlforge/test_engine.py -x -q -k tag_best_skip` | Wave 0 |
| CORE-10 | tag_best() handles duplicate tag on resume | unit | `python -m pytest tests/mlforge/test_engine.py -x -q -k tag_best_dup` | Wave 0 |
| SWARM-01 | publish_result() called after agent completion | unit | `python -m pytest tests/mlforge/test_swarm.py -x -q -k publish` | Wave 0 |
| SWARM-02 | scoreboard populated after swarm run | unit | `python -m pytest tests/mlforge/test_swarm.py -x -q -k scoreboard_populated` | Wave 0 |
| UX-04 | CLI prints missing_pct, numeric/categorical counts | unit | `python -m pytest tests/mlforge/test_cli.py -x -q -k profile_display` | Wave 0 |
| UX-04 | CLI prints leakage_warnings when present | unit | `python -m pytest tests/mlforge/test_cli.py -x -q -k leakage` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/mlforge/test_engine.py tests/mlforge/test_swarm.py tests/mlforge/test_cli.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/mlforge/test_engine.py` -- add tag_best wiring tests (3 tests)
- [ ] `tests/mlforge/test_swarm.py` -- add publish_result wiring tests (2 tests)
- [ ] `tests/mlforge/test_cli.py` -- add profile display tests (2 tests)

## Sources

### Primary (HIGH confidence)
- `src/mlforge/git_ops.py:77-90` -- `tag_best()` implementation and API
- `src/mlforge/swarm/scoreboard.py:49-90` -- `publish_result()` implementation and API
- `src/mlforge/profiler.py:16-30` -- `DatasetProfile` dataclass fields
- `src/mlforge/engine.py:69-125` -- `RunEngine.run()` post-loop structure
- `src/mlforge/swarm/__init__.py:87-131` -- `SwarmManager.run()` structure
- `src/mlforge/cli.py:153-175` -- Current profile print and simple mode flow
- `src/mlforge/state.py:19-20` -- `best_metric` and `best_commit` fields

### Secondary (MEDIUM confidence)
- `tests/test_git_ops.py:92-106` -- Existing `tag_best` unit tests confirming API behavior
- `tests/mlforge/test_engine.py` -- Existing engine test patterns for mocking

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new libraries, all existing code
- Architecture: HIGH - Call sites clearly identified from source code review
- Pitfalls: HIGH - Edge cases identifiable from existing code (None guards, duplicate tags)

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable internal wiring, no external dependency risk)
