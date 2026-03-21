# Phase 11: Fix Tabular Output + Stagnation Guard - Research

**Researched:** 2026-03-20
**Domain:** Cross-phase wiring fixes (tabular JSON output, CLAUDE.md protocol, stagnation guard)
**Confidence:** HIGH

## Summary

Phase 11 addresses three P0/P1 integration gaps identified in the v1.0 milestone audit (GAP-1, GAP-2, GAP-3). These are surgical wiring fixes, not new features. The root cause is clear: the tabular domain was built first but never aligned with the JSON output contract that the engine expects, and the stagnation handler lacks a None guard that becomes critical when all experiments revert.

The DL and FT templates already implement the correct pattern (`json.dumps({"metric_value": X})`), so the fix for tabular is straightforward copy of an established pattern. The CLAUDE.md output format rule is a missing protocol line. The stagnation guard is a 3-line None check.

**Primary recommendation:** Three surgical edits -- tabular_train.py.j2 output, base_claude.md.j2 output rule, and trigger_stagnation_branch() None guard. All three are small, isolated, and independently testable.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CORE-02 | Agent executes keep/revert experiment loop -- modifies code, evaluates, commits on improvement, resets on failure | GAP-1 fix: tabular train.py must emit JSON so engine can extract metric_value and make keep/revert decisions |
| CORE-03 | Protocol prompt system injects domain-specific CLAUDE.md templates into agent context at session start | GAP-2 fix: base_claude.md.j2 must include output format rule so agent knows to emit JSON metric |
| CORE-09 | Deviation handling auto-recovers from crashes (retry), OOM (reduce batch), and divergence (revert) | GAP-3 fix: trigger_stagnation_branch() must handle best_commit=None gracefully instead of crashing |
| INTL-04 | Branch-on-stagnation triggers after 3 consecutive reverts -- branches from best-ever commit, tries different approach | GAP-3 fix: stagnation branch cannot execute when no experiment has been kept yet (best_commit=None) |
</phase_requirements>

## Standard Stack

No new libraries required. All changes are to existing files using existing dependencies.

### Core (already in project)
| Library | Version | Purpose | Relevant to Phase |
|---------|---------|---------|-------------------|
| Jinja2 | existing | Template rendering for .j2 files | tabular_train.py.j2 and base_claude.md.j2 edits |
| json (stdlib) | N/A | JSON serialization | json.dumps in tabular train.py output |
| GitPython | existing | Git operations in stagnation.py | trigger_stagnation_branch guard |

### Installation
No new packages needed.

## Architecture Patterns

### Pattern 1: JSON Metric Output Contract
**What:** All train.py templates must output `json.dumps({"metric_value": X})` as their final print statement. The engine parses `claude -p --output-format json` stdout, which wraps the agent's last text output in a `"result"` field. Engine then does `json.loads(result["result"])` to extract `metric_value`.

**The contract chain:**
```
train.py prints json.dumps({"metric_value": X})
  -> agent relays this (guided by CLAUDE.md protocol)
    -> claude -p --output-format json wraps in {"result": "...", "total_cost_usd": ...}
      -> engine._run_one_experiment() does json.loads(stdout)
        -> engine._process_result() does json.loads(result["result"]) to get metric_value
```

**Current state of each domain:**
- DL (`dl_train.py.j2` line 229): `print(json.dumps(result))` -- CORRECT
- FT (`ft_train.py.j2` line 210): `print(json.dumps(result))` -- CORRECT
- Tabular (`tabular_train.py.j2` line 98): `print(f"Best value: {study.best_value:.4f}")` -- BROKEN

**Fix:** Replace tabular train.py output with `json.dumps({"metric_value": study.best_value})`, matching the DL/FT pattern. Must also `import json` at the top of the template.

### Pattern 2: CLAUDE.md Output Format Rule
**What:** The base_claude.md.j2 template should include an output format instruction telling the agent to emit the JSON metric as the last line of output. Without this, even if train.py outputs correct JSON, the agent may not relay it.

**Current base_claude.md.j2:** Has Role, Domain, Metric, Frozen Files, Mutable Files, Domain Rules, and optional Extra Sections. No output format section.

**Fix:** Add an "Output Format" section after Domain Rules:
```markdown
## Output Format
After running train.py, emit the metric result as the LAST line of your response:
{"metric_value": <number>}
This JSON line is parsed by the engine to make keep/revert decisions. If the engine cannot find it, the experiment will be reverted.
```

### Pattern 3: Graceful None Guard in Stagnation
**What:** `trigger_stagnation_branch()` currently raises `ValueError` when `state.best_commit is None`. This crashes the session. The fix should be in the caller (engine.py `_process_result`) or in the function itself.

**Two options:**
1. Guard in `trigger_stagnation_branch()` itself -- return early (e.g., return `""`) when best_commit is None
2. Guard in `engine._process_result()` -- skip the stagnation branch call when `state.best_commit is None`

**Recommendation:** Guard in `trigger_stagnation_branch()` itself. Change the ValueError to a graceful skip (return empty string or None). This makes the function safe to call from any context. Also update the docstring.

**Rationale:** The function's docstring says "Raises ValueError if best_commit is None" -- that was an intentional design. But at runtime, it is perfectly valid to reach stagnation (3 reverts) without ever having a successful commit (when metric_value is always None). The function should handle this gracefully since the caller should not need to know about this edge case.

### Anti-Patterns to Avoid
- **Adding metric parsing logic to engine.py:** The engine already correctly parses JSON from `result["result"]`. The fix belongs in the template that generates the output, not in additional parsing fallbacks.
- **Multiple output formats:** Do not add plain-text parsing as a fallback. Enforce JSON-only output so the contract is clean.
- **Logging the stagnation skip silently:** When best_commit is None and stagnation triggers, log a message (via Python logging) so the user knows branching was skipped due to no successful commits.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON output format | Custom text parsing regex | json.dumps / json.loads | Already the contract for DL/FT; consistent across all domains |

## Common Pitfalls

### Pitfall 1: Forgetting `import json` in tabular_train.py.j2
**What goes wrong:** The template renders train.py but `json` is not imported, causing ImportError at runtime.
**How to avoid:** Add `import json` to the imports section of the template. Check that the rendered output includes the import.

### Pitfall 2: Best params output line interfering
**What goes wrong:** The current template has two print lines: `print(f"Best value: ...")` and `print(f"Best params: ...")`. If only the metric line is changed to JSON but the params line remains as plain text, the agent might relay both, and the engine may not find the JSON metric as the last line.
**How to avoid:** Either (a) include best_params in the JSON dict, or (b) ensure the JSON metric line is the very last print. Recommend including both in the JSON output: `json.dumps({"metric_value": study.best_value, "best_params": study.best_params})`.

### Pitfall 3: Stagnation guard test regression
**What goes wrong:** Existing test `test_no_best_commit_raises` asserts that ValueError IS raised. Changing the behavior will break this test.
**How to avoid:** Update the test to assert the new behavior (graceful return) instead of the ValueError.

### Pitfall 4: Engine stagnation call site still vulnerable
**What goes wrong:** Even if `trigger_stagnation_branch()` handles None, the engine.py line 257 calls it unconditionally when stagnation is detected and untried families exist. If the function now returns None or empty string, the `tried_families.append()` on line 258 still runs, consuming a family name without actually branching.
**How to avoid:** Have `trigger_stagnation_branch()` return None (not a branch name) when best_commit is None. Engine should check the return value before appending to tried_families.

## Code Examples

### Fix 1: tabular_train.py.j2 -- JSON output (last ~6 lines)

Current (BROKEN):
```python
if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=20, timeout=TIME_BUDGET * 60)

    print(f"Best value: {study.best_value:.4f}")
    print(f"Best params: {study.best_params}")
```

Fixed:
```python
if __name__ == "__main__":
    import json

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=20, timeout=TIME_BUDGET * 60)

    print(json.dumps({"metric_value": study.best_value, "best_params": study.best_params}))
```

Note: `import json` can go at the top of the file with other imports instead. Placing it in `__main__` keeps the diff minimal but top-level is cleaner.

### Fix 2: base_claude.md.j2 -- Output format section

Add after `## Domain Rules` block, before the `{% if extra_sections %}` block:

```jinja2
## Output Format
After running train.py, emit the result as the LAST line of your response in this exact format:
{"metric_value": <number>}
This JSON is parsed by the engine. If missing, the experiment is automatically reverted.
```

### Fix 3: stagnation.py -- None guard

Current (CRASHES):
```python
def trigger_stagnation_branch(git_manager, state, new_family):
    if state.best_commit is None:
        raise ValueError("Cannot branch: best_commit is None")
    ...
```

Fixed:
```python
def trigger_stagnation_branch(git_manager, state, new_family):
    if state.best_commit is None:
        return None
    ...
    return branch_name
```

Engine call site update:
```python
# In engine.py _process_result, revert branch:
if untried:
    new_family = untried[0]
    branch = trigger_stagnation_branch(self.git, self.state, new_family)
    if branch is not None:
        self.state.tried_families.append(new_family)
```

## State of the Art

Not applicable -- this phase is fixing existing wiring, not adopting new technology.

## Open Questions

None. All three fixes are well-understood with clear evidence from the audit and existing code patterns.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/mlforge/test_stagnation.py tests/mlforge/test_engine.py tests/mlforge/test_templates.py -x -q` |
| Full suite command | `python3 -m pytest tests/mlforge/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-02 | tabular_train.py.j2 renders json.dumps metric output | unit | `python3 -m pytest tests/mlforge/test_templates.py -x -q -k "tabular"` | Needs new test |
| CORE-03 | base_claude.md.j2 contains output format section | unit | `python3 -m pytest tests/mlforge/test_templates.py -x -q -k "claude"` | Needs new test |
| CORE-09 | trigger_stagnation_branch returns None when best_commit=None | unit | `python3 -m pytest tests/mlforge/test_stagnation.py -x -q` | Exists (needs update) |
| INTL-04 | Engine skips tried_families append when stagnation branch returns None | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -q -k "stagnation"` | Needs new/updated test |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/mlforge/test_stagnation.py tests/mlforge/test_engine.py tests/mlforge/test_templates.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/mlforge/ -x -q`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
- [ ] `tests/mlforge/test_templates.py` -- add test: rendered tabular_train.py contains `json.dumps` and `metric_value`
- [ ] `tests/mlforge/test_templates.py` -- add test: rendered CLAUDE.md contains output format section
- [ ] `tests/mlforge/test_stagnation.py::test_no_best_commit_raises` -- update: assert returns None instead of ValueError
- [ ] `tests/mlforge/test_engine.py` -- add test: stagnation with best_commit=None does not crash and does not append to tried_families

## Sources

### Primary (HIGH confidence)
- Direct source code inspection: `src/mlforge/templates/tabular_train.py.j2` (line 98 -- plain text print)
- Direct source code inspection: `src/mlforge/templates/dl_train.py.j2` (line 229 -- correct json.dumps)
- Direct source code inspection: `src/mlforge/templates/ft_train.py.j2` (line 210 -- correct json.dumps)
- Direct source code inspection: `src/mlforge/templates/base_claude.md.j2` (no output format section)
- Direct source code inspection: `src/mlforge/intelligence/stagnation.py` (line 44 -- ValueError on None)
- Direct source code inspection: `src/mlforge/engine.py` (lines 203-210 -- metric extraction, lines 253-258 -- stagnation call)
- `.planning/v1.0-MILESTONE-AUDIT.md` -- GAP-1, GAP-2, GAP-3 definitions

### Secondary (MEDIUM confidence)
- Existing test patterns: `tests/mlforge/test_engine.py` -- confirms JSON contract via `_make_claude_response`
- Existing test patterns: `tests/mlforge/test_stagnation.py` -- confirms current ValueError behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all fixes use existing patterns
- Architecture: HIGH -- DL/FT templates already demonstrate the correct pattern
- Pitfalls: HIGH -- all identified from direct code reading, test file inspection

**Research date:** 2026-03-20
**Valid until:** indefinite (fixes to existing code, not external dependencies)
