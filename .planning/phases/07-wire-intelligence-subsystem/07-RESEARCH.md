# Phase 7: Wire Intelligence Subsystem to Engine - Research

**Researched:** 2026-03-19
**Domain:** Engine integration / wiring existing intelligence modules into RunEngine loop
**Confidence:** HIGH

## Summary

Phase 7 closes P2 gaps from the v1.0 audit: intelligence modules (baselines, diagnostics, stagnation, multi-draft, journal) exist as standalone functions with passing tests but are **never called** from the engine runtime loop. The gap is purely integration -- no new algorithms or data structures need to be invented.

The `RunEngine` class in `engine.py` currently runs a simple loop: checkpoint, spawn claude, process result (keep/revert/retry/stop), increment counter. It needs five integration points: (1) baselines before the first experiment, (2) journal writes after each experiment, (3) diagnostics after each experiment with results injected into the prompt, (4) stagnation detection after reverts, and (5) multi-draft generation at session start. Each integration point calls existing functions from `mlforge.intelligence.*`, `mlforge.tabular.baselines`, and `mlforge.journal`.

**Primary recommendation:** Modify `RunEngine` to call existing intelligence functions at the right lifecycle moments, adding new state fields to `SessionState` where needed (e.g., `baselines`, `task`). Keep changes localized to `engine.py`, `state.py`, and `config.py` -- the intelligence modules themselves should not change.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTL-01 | Baseline establishment runs naive + domain-specific baselines before agent starts experimenting | `compute_baselines()` exists in `tabular/baselines.py`, needs to be called in `RunEngine.run()` before loop starts. Requires dataset X/y access from `prepare.py` output. |
| INTL-02 | Dual-baseline gate requires agent to beat both baselines before keeping an experiment | `passes_baseline_gate()` exists in `tabular/baselines.py`, needs to be called in `_process_result()` before the keep decision. |
| INTL-03 | Diagnostics engine analyzes WHERE the model fails | `diagnose_regression()` and `diagnose_classification()` exist in `intelligence/diagnostics.py`, need to be called after each experiment and output appended to prompt context. |
| INTL-04 | Branch-on-stagnation triggers after 3 consecutive reverts | `check_stagnation()` and `trigger_stagnation_branch()` exist in `intelligence/stagnation.py`, need to be called in `_process_result()` after revert when `consecutive_reverts >= threshold`. |
| INTL-05 | Multi-draft start generates 3-5 diverse initial solutions, picks best, iterates linearly | `ALGORITHM_FAMILIES` and `select_best_draft()` exist in `intelligence/drafts.py`, need a `_run_draft_phase()` method in `RunEngine` before the main loop. |
| CORE-08 | Experiment journal accumulates structured knowledge that survives context resets | `append_journal_entry()`, `get_last_diff()`, `load_journal()`, `render_journal_markdown()` exist in `journal.py`, need to be called in `_process_result()` after each experiment. |
| INTL-06 | Diff-aware experimentation shows agent what changed between experiments via git diff | `get_last_diff()` exists in `journal.py`, needs to be called after keep actions and stored in journal entry's `diff` field. |
</phase_requirements>

## Standard Stack

### Core (already in codebase)
| Module | Location | Purpose | Status |
|--------|----------|---------|--------|
| `compute_baselines` | `tabular/baselines.py` | Naive + domain-specific baseline scores | EXISTS, untested in engine |
| `passes_baseline_gate` | `tabular/baselines.py` | Dual-baseline gate check | EXISTS, untested in engine |
| `diagnose_regression` | `intelligence/diagnostics.py` | Worst predictions, bias, feature correlations | EXISTS, untested in engine |
| `diagnose_classification` | `intelligence/diagnostics.py` | Misclassified samples, per-class accuracy, confused pairs | EXISTS, untested in engine |
| `check_stagnation` | `intelligence/stagnation.py` | Consecutive revert threshold check | EXISTS, untested in engine |
| `trigger_stagnation_branch` | `intelligence/stagnation.py` | Branch from best-ever commit | EXISTS, untested in engine |
| `select_best_draft` | `intelligence/drafts.py` | Pick best from multi-draft results | EXISTS, untested in engine |
| `ALGORITHM_FAMILIES` | `intelligence/drafts.py` | Model family definitions | EXISTS |
| `append_journal_entry` | `journal.py` | JSONL append for experiment entries | EXISTS, untested in engine |
| `get_last_diff` | `journal.py` | Git diff between HEAD and HEAD~1 | EXISTS, untested in engine |
| `load_journal` | `journal.py` | Load JSONL journal entries | EXISTS, untested in engine |
| `render_journal_markdown` | `journal.py` | Render journal as markdown table | EXISTS, untested in engine |

### No new dependencies needed
This phase is purely integration wiring. All modules exist and are tested independently.

## Architecture Patterns

### Current Engine Loop (BEFORE wiring)
```
RunEngine.run():
  while not guardrails.should_stop():
    save_checkpoint()
    result = _run_one_experiment()    # spawns claude -p
    action = _process_result(result)  # keep/revert/retry/stop
    state.experiment_count += 1
```

### Target Engine Loop (AFTER wiring)
```
RunEngine.run():
  # 1. MULTI-DRAFT PHASE (INTL-05)
  if config.enable_drafts:
    draft_results = _run_draft_phase()  # Run 3-5 diverse models
    best = select_best_draft(draft_results, direction)
    git.checkout(best.commit_hash)  # Start from best draft

  # 2. BASELINE ESTABLISHMENT (INTL-01)
  baselines = _compute_baselines()  # Run before main loop
  state.baselines = baselines

  # 3. MAIN LOOP
  while not guardrails.should_stop():
    save_checkpoint()
    result = _run_one_experiment()
    action = _process_result(result)  # Enhanced with:
      # - BASELINE GATE (INTL-02): passes_baseline_gate() before keep
      # - JOURNAL (CORE-08, INTL-06): append_journal_entry() + get_last_diff()
      # - STAGNATION (INTL-04): check_stagnation() after revert
      # - DIAGNOSTICS (INTL-03): diagnose_*() after experiment
    state.experiment_count += 1
```

### Integration Point 1: Baselines (INTL-01, INTL-02)

**Where:** Before the main loop in `run()`, and in `_process_result()` keep path.

**Challenge:** `compute_baselines()` needs X, y arrays and a scoring string. The engine does not currently load the dataset -- it delegates everything to the spawned claude session. Two approaches:

**Option A (recommended):** Load prepare.py output in the engine. The scaffolded `prepare.py` produces X_train, y_train. The engine can `exec()` or `subprocess` the prepare script and capture the arrays. This is the simplest approach since prepare.py is a frozen, deterministic script.

**Option B:** Run baselines inside the first claude session and parse the output. This is fragile -- the agent might not output baselines in a parseable format.

**Baseline gate integration:** In `_process_result()`, before returning "keep", call `passes_baseline_gate(metric_value, state.baselines, config.direction)`. If it fails, treat as "revert" instead.

### Integration Point 2: Journal (CORE-08, INTL-06)

**Where:** In `_process_result()` after determining the action.

**Current state:** The engine already reads `experiments.md` in `_build_prompt()` and creates it during scaffold. But it never WRITES to it after experiments. The journal JSONL path (`experiments.jsonl`) is not used at all.

**Pattern:**
```python
# After keep:
diff = get_last_diff(self.experiment_dir)
entry = JournalEntry(
    experiment_id=exp_id,
    hypothesis="Agent experiment",  # From result if available
    result="Improvement",
    metric_value=metric_value,
    metric_delta=metric_value - (state.best_metric or 0),
    commit_hash=commit_hash,
    status="keep",
    diff=diff,
)
append_journal_entry(self._journal_jsonl_path, entry)

# Update experiments.md from JSONL
entries = load_journal(self._journal_jsonl_path)
self._journal_path.write_text(render_journal_markdown(entries))
```

**Key insight:** The engine writes JSONL (machine) and renders markdown (human-readable) after each experiment. The markdown file is what `_build_prompt()` reads for the agent's context.

### Integration Point 3: Diagnostics (INTL-03)

**Where:** After each experiment, inject diagnostics output into the agent's context.

**Challenge:** `diagnose_regression/classification()` needs y_true, y_pred arrays. The spawned claude session produces predictions but they are not returned to the engine. Two approaches:

**Option A (recommended):** Have the agent write predictions to a file (e.g., `predictions.csv`) as part of its experiment. The engine reads this file after each experiment and runs diagnostics. The CLAUDE.md template should include a rule requiring prediction output.

**Option B:** Run diagnostics inside the claude session. The diagnostics functions would be available in the experiment directory. This loses the "engine-level intelligence" design.

**Output injection:** Write diagnostics to a `diagnostics.md` file that `_build_prompt()` includes in the agent's context.

### Integration Point 4: Stagnation (INTL-04)

**Where:** In `_process_result()` after incrementing `consecutive_reverts`.

**Pattern:**
```python
if action == "revert":
    self.state.consecutive_reverts += 1
    if check_stagnation(self.state):
        # Pick a new family not yet tried
        new_family = _pick_untried_family(state)
        trigger_stagnation_branch(self.git, self.state, new_family)
```

**State tracking needed:** Track which algorithm families have been tried (to pick a new one on stagnation). Add `tried_families: list[str]` to SessionState or track in the engine.

### Integration Point 5: Multi-Draft (INTL-05)

**Where:** Before the main loop in `run()`.

**Pattern:**
```python
def _run_draft_phase(self) -> list[DraftResult]:
    results = []
    for family_name, family_info in ALGORITHM_FAMILIES.items():
        # Modify prompt to specify this family
        result = self._run_one_experiment_with_family(family_name)
        # Create DraftResult from outcome
        draft = DraftResult(name=family_name, ...)
        results.append(draft)
    return results
```

**Key design decision:** Each draft is a separate claude session. The engine tells the agent which model family to use via the prompt. After all drafts, `select_best_draft()` picks the winner and the engine checks out that commit.

### Recommended Project Structure Changes
```
src/mlforge/
  engine.py          # MODIFY: Add 5 integration points
  state.py           # MODIFY: Add baselines, task, tried_families fields
  config.py          # MODIFY: Add enable_drafts, stagnation_threshold fields
  journal.py         # NO CHANGE
  intelligence/
    diagnostics.py   # NO CHANGE
    drafts.py        # NO CHANGE
    stagnation.py    # NO CHANGE
  tabular/
    baselines.py     # NO CHANGE
```

### Anti-Patterns to Avoid
- **Modifying intelligence modules to fit the engine:** The modules are correct. The engine needs to call them, not the other way around.
- **Running baselines inside the claude session:** Baselines should be computed by the engine before the agent starts, so the agent receives them as ground truth context.
- **Storing diagnostics only in state:** Diagnostics need to be rendered as text and injected into the next experiment's prompt so the agent can act on them.
- **Branching without resetting state:** After `trigger_stagnation_branch()`, `consecutive_reverts` must reset to 0 (already handled by the function) and the prompt should inform the agent it is on a new exploration branch.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Baseline computation | Custom mean/mode baselines | `compute_baselines()` from `tabular/baselines.py` | Already handles classification/regression with proper CV |
| Baseline gate | Custom comparison logic | `passes_baseline_gate()` from `tabular/baselines.py` | Already handles direction-aware strict inequality |
| Stagnation detection | Custom counter check | `check_stagnation()` from `intelligence/stagnation.py` | Already parameterized with threshold |
| Stagnation branching | Custom git branch logic | `trigger_stagnation_branch()` from `intelligence/stagnation.py` | Already handles detached HEAD safely |
| Draft selection | Custom argmax/argmin | `select_best_draft()` from `intelligence/drafts.py` | Already direction-aware with None filtering |
| Journal persistence | Custom file writing | `append_journal_entry()` from `journal.py` | Already handles JSONL with timestamps |
| Diff extraction | Custom git diff calls | `get_last_diff()` from `journal.py` | Already handles missing commits gracefully |

**Key insight:** Every function needed for this phase already exists and is tested. The phase is 100% wiring.

## Common Pitfalls

### Pitfall 1: Baseline Data Access
**What goes wrong:** `compute_baselines()` needs X, y arrays but the engine never loads the dataset.
**Why it happens:** The engine delegates all ML work to spawned claude sessions.
**How to avoid:** Load prepare.py output in the engine before the loop. The scaffold guarantees prepare.py exists and is deterministic.
**Warning signs:** Trying to parse agent output for baseline data instead of loading it directly.

### Pitfall 2: Journal File Path Confusion
**What goes wrong:** The engine uses `experiments.md` (markdown) but the journal module uses JSONL (`experiments.jsonl`).
**Why it happens:** Two different file formats for the same conceptual data.
**How to avoid:** Use JSONL as the source of truth. Render markdown from JSONL after each update. The engine reads the markdown file for prompt building.

### Pitfall 3: Diagnostics Data Dependency
**What goes wrong:** `diagnose_*()` needs predictions (y_pred) which only exist inside the claude session.
**Why it happens:** The engine does not run ML models -- the agent does.
**How to avoid:** Add a CLAUDE.md rule requiring the agent to save predictions to `predictions.csv`. The engine reads this file after each experiment. If the file does not exist, skip diagnostics for that iteration.

### Pitfall 4: Multi-Draft Git State
**What goes wrong:** After running 5 drafts, the git repo has 5 different committed states but the engine needs to checkout the best one.
**Why it happens:** Each draft commits its changes, but only the best should be the starting point for iteration.
**How to avoid:** Use `git.checkout(best_draft.commit_hash)` after `select_best_draft()`. The other draft commits remain in history but are not on the active branch.

### Pitfall 5: SessionState Serialization
**What goes wrong:** Adding new fields to SessionState (baselines, tried_families) breaks existing checkpoints.
**Why it happens:** `SessionState.from_json()` already handles unknown fields gracefully (ignores them), but new fields need defaults.
**How to avoid:** All new SessionState fields MUST have default values. The existing `from_json()` already filters to known fields, so forward compatibility is handled.

### Pitfall 6: Domain-Specific Baseline Gating
**What goes wrong:** Calling `compute_baselines()` for non-tabular domains (DL, fine-tuning) where it makes no sense.
**Why it happens:** Baselines are tabular-specific (sklearn DummyClassifier/DummyRegressor).
**How to avoid:** Guard baseline calls with `if config.domain == "tabular"`. Other domains can add their own baseline logic later.

## Code Examples

### Baseline Integration in run()
```python
# Source: tabular/baselines.py (existing) + engine.py (new integration)
from mlforge.tabular.baselines import compute_baselines, passes_baseline_gate

def _compute_baselines(self) -> dict | None:
    """Compute baselines before the main loop. Tabular domain only."""
    if self.config.domain != "tabular":
        return None

    # Load dataset via prepare.py
    prepare_path = self.experiment_dir / "prepare.py"
    if not prepare_path.exists():
        return None

    # Execute prepare.py to get X, y
    import importlib.util
    spec = importlib.util.spec_from_file_location("prepare", prepare_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    X_train, y_train = mod.X_train, mod.y_train

    task = self.config.plugin_settings.get("task", "classification")
    scoring = self.config.metric
    return compute_baselines(X_train, y_train, scoring, task)
```

### Journal Integration in _process_result()
```python
# Source: journal.py (existing) + engine.py (new integration)
from mlforge.journal import (
    JournalEntry, append_journal_entry, get_last_diff,
    load_journal, render_journal_markdown,
)

def _write_journal(self, exp_id, status, metric_value, commit_hash, hypothesis=""):
    """Append journal entry and update markdown."""
    diff = get_last_diff(self.experiment_dir) if status == "keep" else None

    prev_best = self.state.best_metric
    delta = (metric_value - prev_best) if metric_value and prev_best else None

    entry = JournalEntry(
        experiment_id=exp_id,
        hypothesis=hypothesis or f"experiment-{exp_id}",
        result=status,
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
```

### Stagnation Check in _process_result()
```python
# Source: intelligence/stagnation.py (existing) + engine.py (new integration)
from mlforge.intelligence.stagnation import check_stagnation, trigger_stagnation_branch
from mlforge.intelligence.drafts import ALGORITHM_FAMILIES

# In the revert branch of _process_result():
if action == "revert":
    self.state.consecutive_reverts += 1
    if check_stagnation(self.state, threshold=self.config.stagnation_threshold):
        tried = getattr(self.state, 'tried_families', [])
        untried = [f for f in ALGORITHM_FAMILIES if f not in tried]
        if untried:
            new_family = untried[0]
            trigger_stagnation_branch(self.git, self.state, new_family)
            self.state.tried_families.append(new_family)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CLAUDE.md text rules for baselines | Programmatic engine-level baseline gate | Phase 7 (this phase) | Agent cannot bypass baseline requirement |
| No diagnostics in agent context | Engine injects diagnostics after each experiment | Phase 7 (this phase) | Agent gets actionable WHERE-it-fails info |
| No stagnation recovery | Automatic branch-on-stagnation after 3 reverts | Phase 7 (this phase) | Prevents infinite revert loops |
| Single initial model | Multi-draft diverse start | Phase 7 (this phase) | Better initial solution before linear iteration |
| No persistent journal | JSONL journal with markdown rendering | Phase 7 (this phase) | Knowledge survives context resets |

## Open Questions

1. **Prepare.py execution in engine**
   - What we know: `compute_baselines()` needs X, y arrays. The engine does not currently load the dataset.
   - What's unclear: Whether `prepare.py` can be safely `exec()`d in the engine process or needs subprocess isolation.
   - Recommendation: Use `importlib.util` to load prepare.py as a module. It is frozen and deterministic, so this is safe. If it imports heavy ML deps, they are already required deps of mlforge.

2. **Diagnostics y_pred source**
   - What we know: `diagnose_*()` needs y_pred arrays which only exist inside the claude session.
   - What's unclear: Whether to require agent to write predictions to a file, or skip engine-level diagnostics.
   - Recommendation: Add a CLAUDE.md rule requiring `predictions.csv` output. If the file does not exist after an experiment, skip diagnostics gracefully.

3. **Multi-draft prompt engineering**
   - What we know: Each draft needs to use a specific algorithm family.
   - What's unclear: Exact prompt wording to reliably direct the agent to a specific model family.
   - Recommendation: Use explicit prompt like "Use {family_info['classification']} from {family_info['description']}. Do NOT use other model families."

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (stdlib) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `python3 -m pytest tests/mlforge/test_engine.py -x -q` |
| Full suite command | `python3 -m pytest tests/mlforge/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTL-01 | `compute_baselines()` called in engine before loop | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k baseline` | No -- Wave 0 |
| INTL-02 | `passes_baseline_gate()` rejects sub-baseline keeps | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k gate` | No -- Wave 0 |
| INTL-03 | `diagnose_*()` called after experiment, output in prompt | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k diagnos` | No -- Wave 0 |
| INTL-04 | `check_stagnation()` + `trigger_stagnation_branch()` on revert threshold | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k stagnation` | No -- Wave 0 |
| INTL-05 | `select_best_draft()` called in draft phase | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k draft` | No -- Wave 0 |
| CORE-08 | `append_journal_entry()` called after each experiment | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k journal` | No -- Wave 0 |
| INTL-06 | `get_last_diff()` captured in journal on keep | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k diff` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/mlforge/test_engine.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/mlforge/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/mlforge/test_engine.py` -- new test classes for each integration point (baseline, diagnostics, stagnation, draft, journal). Existing test file structure should be extended, not replaced.
- [ ] Existing tests (421 total) must continue passing -- no regressions.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `engine.py`, `journal.py`, `intelligence/diagnostics.py`, `intelligence/drafts.py`, `intelligence/stagnation.py`, `tabular/baselines.py` -- all functions read and verified
- `state.py` -- SessionState fields and JSON serialization verified
- `config.py` -- Config fields and TOML loading verified
- `tests/mlforge/test_engine.py` -- existing test patterns verified (28 tests)

### Secondary (MEDIUM confidence)
- `ROADMAP.md` -- Phase 7 requirements and success criteria
- `REQUIREMENTS.md` -- INTL-01 through INTL-06, CORE-08 definitions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all modules exist, read source code directly
- Architecture: HIGH - engine loop is simple and well-understood, integration points are clear
- Pitfalls: HIGH - identified from actual code structure (data access patterns, file paths)
- Open questions: MEDIUM - prepare.py exec and diagnostics data flow need validation during implementation

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable -- internal codebase, no external deps changing)
