# Phase 2: Core Loop - Research

**Researched:** 2026-03-10
**Domain:** Autonomous experiment loop orchestration, multi-draft initialization, crash recovery, stagnation detection, domain context injection
**Confidence:** HIGH

## Summary

Phase 2 builds the autonomous experiment loop that composes Phase 1's foundation modules (ExperimentRunner, GitManager, ExperimentLogger) into a continuously running agent loop. The key insight from autoresearch's program.md is that this is NOT a Python program that loops -- it is a set of instructions that Claude Code (the LLM agent) follows. Claude Code IS the loop: it reads instructions from CLAUDE.md, edits train.py, runs experiments via subprocess, parses results, and makes keep/revert decisions. The Python code we build provides the helper functions and templates; the loop protocol is encoded in CLAUDE.md and program.md files that Claude Code reads at runtime.

The architecture has three layers: (1) a `program.md` template for domain context injection (human-written guidance about the dataset), (2) a `CLAUDE.md` template containing the complete loop protocol (the autoresearch "LOOP FOREVER" pattern adapted for tabular ML), and (3) Python orchestration helpers that encapsulate the multi-draft initialization, keep/revert decision logic, stagnation detection, and crash recovery counters -- callable by the agent but not the loop itself.

**Primary recommendation:** Build a `loop_protocol.py` module with helper functions (draft generation, keep/revert decision, stagnation detection, crash recovery tracking) that the agent calls from the CLAUDE.md loop instructions. Generate `program.md` and `CLAUDE.md` templates. The agent loop is Claude Code following CLAUDE.md instructions, NOT a Python while-loop.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LOOP-01 | Agent runs train.py, extracts metric, decides keep/revert | ExperimentRunner.run() returns ExperimentResult; compare metric_value against best_score; GitManager.commit() or .revert() |
| LOOP-02 | All stdout/stderr redirected to run.log | ExperimentRunner already writes run.log (implemented in Phase 1) |
| LOOP-03 | Agent reads metric via grep/regex from run.log | ExperimentRunner._extract_field() already does this (implemented in Phase 1); CLAUDE.md instructs `grep "^metric_value:" run.log` |
| LOOP-04 | Keep/revert: improved -> commit; worse -> reset | Decision helper compares new metric_value vs best; calls GitManager.commit() or .revert() |
| LOOP-05 | Agent runs autonomously and indefinitely ("NEVER STOP") | CLAUDE.md template includes "NEVER STOP" protocol from autoresearch |
| LOOP-06 | Timeout: experiments exceeding 2x budget killed as failures | ExperimentRunner already enforces hard_timeout = 2x budget (implemented in Phase 1) |
| LOOP-07 | Crash recovery: read traceback, attempt fix, give up after 3 | Crash counter tracks consecutive failures on same issue; agent reads tail of run.log |
| LOOP-08 | Stagnation detection: after 5 consecutive reverts, try different strategy | Revert counter + strategy category rotation (algorithm families, hyperparameter ranges, ensemble methods) |
| CTX-01 | program.md accepts human domain expertise | Template file with sections for data patterns, feature hints, known issues, strategy suggestions |
| CTX-02 | Agent reads program.md at each iteration | CLAUDE.md instructs agent to re-read program.md each iteration for strategy guidance |
| CTX-03 | CLAUDE.md provides the loop protocol | CLAUDE.md template encodes the complete experiment loop as agent instructions |
| DRAFT-01 | Generate 3-5 diverse drafts using different algorithm families | Draft generator creates train.py variants: LogisticRegression/Ridge, RandomForest, XGBoost, LightGBM, SVM/ElasticNet |
| DRAFT-02 | Each draft evaluated using frozen evaluation function | Each draft train.py runs via ExperimentRunner.run() and returns ExperimentResult |
| DRAFT-03 | Best draft selected as starting point | Compare all draft ExperimentResults, git checkout the commit with highest metric_value |
| DRAFT-04 | Draft results logged with "draft-keep" or "draft-discard" status | ExperimentLogger.log_result() with status field set to "draft-keep" or "draft-discard" |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | 1.8.x | Algorithm families for drafts (LogisticRegression, RandomForest, SVM, ElasticNet, Ridge) | Already installed; provides all baseline algorithms |
| xgboost | latest | Gradient boosted trees draft | Already installed; top performer on tabular data |
| lightgbm | latest | Alternative gradient boosting draft | Already installed; fast, memory-efficient |

### Supporting (all stdlib -- no new dependencies)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| string (stdlib) | - | Template rendering for train.py variants | Draft generation |
| textwrap (stdlib) | - | Dedented multiline strings for code generation | Draft train.py scripts |
| copy (stdlib) | - | Deep copy of template strings | Draft generation |
| dataclasses (stdlib) | - | Structured state tracking (LoopState) | Stagnation/crash counters |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| String template for train.py | Jinja2 | Jinja2 is overkill -- train.py is a simple Python script with a model section to swap |
| Dataclass for state | Plain dict | Dataclass gives type safety and default values for loop state |
| CLAUDE.md as protocol | Python while-loop | The agent IS the loop -- Python can't control Claude Code's iteration |

**Installation:**
```bash
# No new dependencies needed -- everything is already installed from Phase 1
```

## Architecture Patterns

### Understanding: Claude Code IS the Loop

This is the most important architectural insight for Phase 2. The experiment loop is NOT a Python program. It is a protocol that Claude Code follows by reading CLAUDE.md. The autoresearch pattern works exactly this way:

```
# In autoresearch, the loop is in program.md (instructions to the LLM agent):
# "LOOP FOREVER:
#   1. Look at the git state
#   2. Tune train.py
#   3. git commit
#   4. Run the experiment
#   5. Read results
#   6-9. Keep/revert logic
#   NEVER STOP"
```

Our Python code provides HELPER FUNCTIONS that the agent calls during its loop, but the loop control flow lives in CLAUDE.md.

### Recommended Module Structure
```
src/automl/
    prepare.py           # FROZEN (Phase 1)
    train_template.py    # MUTABLE template (Phase 1)
    runner.py            # ExperimentRunner (Phase 1)
    git_ops.py           # GitManager (Phase 1)
    experiment_logger.py # ExperimentLogger (Phase 1)
    drafts.py            # NEW: Multi-draft generation (DRAFT-01 through DRAFT-04)
    loop_helpers.py      # NEW: Keep/revert decision, stagnation, crash tracking (LOOP-*)
    templates/
        program.md.tmpl  # NEW: Template for program.md (CTX-01)
        claude.md.tmpl   # NEW: Template for CLAUDE.md (CTX-03)
```

### Pattern 1: Multi-Draft Generation
**What:** Generate 3-5 diverse train.py variants, each using a different algorithm family, run all, pick the best.
**When to use:** At the start of every experiment run, before the linear iteration loop begins.
**Example:**
```python
# drafts.py
"""Multi-draft initialization: generate diverse train.py variants."""

from __future__ import annotations
import os
import shutil
from dataclasses import dataclass

# Algorithm families for diverse drafts
# Each family represents a fundamentally different approach
ALGORITHM_FAMILIES = {
    "classification": [
        {
            "name": "LogisticRegression",
            "imports": "from sklearn.linear_model import LogisticRegression",
            "model_line": "model = LogisticRegression(max_iter=1000)",
        },
        {
            "name": "RandomForest",
            "imports": "from sklearn.ensemble import RandomForestClassifier",
            "model_line": "model = RandomForestClassifier(n_estimators=100, random_state=42)",
        },
        {
            "name": "XGBoost",
            "imports": "from xgboost import XGBClassifier",
            "model_line": "model = XGBClassifier(n_estimators=100, random_state=42, verbosity=0)",
        },
        {
            "name": "LightGBM",
            "imports": "from lightgbm import LGBMClassifier",
            "model_line": "model = LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)",
        },
        {
            "name": "SVM",
            "imports": "from sklearn.svm import SVC",
            "model_line": "model = SVC(probability=True, random_state=42)",
        },
    ],
    "regression": [
        {
            "name": "Ridge",
            "imports": "from sklearn.linear_model import Ridge",
            "model_line": "model = Ridge()",
        },
        {
            "name": "RandomForest",
            "imports": "from sklearn.ensemble import RandomForestRegressor",
            "model_line": "model = RandomForestRegressor(n_estimators=100, random_state=42)",
        },
        {
            "name": "XGBoost",
            "imports": "from xgboost import XGBRegressor",
            "model_line": "model = XGBRegressor(n_estimators=100, random_state=42, verbosity=0)",
        },
        {
            "name": "LightGBM",
            "imports": "from lightgbm import LGBMRegressor",
            "model_line": "model = LGBMRegressor(n_estimators=100, random_state=42, verbose=-1)",
        },
        {
            "name": "ElasticNet",
            "imports": "from sklearn.linear_model import ElasticNet",
            "model_line": "model = ElasticNet(random_state=42)",
        },
    ],
}


@dataclass
class DraftResult:
    """Result of a single draft evaluation."""
    name: str
    metric_value: float | None
    status: str  # "draft-keep" or "draft-discard"
    commit_hash: str
    description: str


def generate_draft_train_py(template_path: str, algorithm: dict) -> str:
    """Read the train.py template and swap in a different algorithm.

    Returns the modified train.py content as a string.
    """
    content = open(template_path).read()

    # Replace the model section (between markers)
    # The template has:
    #   # --- Model (agent edits this section) ---
    #   from sklearn.linear_model import LogisticRegression
    #   model = LogisticRegression(max_iter=1000)
    import re
    pattern = r"(# --- Model.*?---\n).*?(\n# --- Evaluate)"
    replacement = rf"\g<1>{algorithm['imports']}\n{algorithm['model_line']}\n\g<2>"
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    return new_content
```

### Pattern 2: Keep/Revert Decision Logic
**What:** Compare new metric against best, decide whether to commit or revert.
**When to use:** After every experiment run.
**Example:**
```python
# loop_helpers.py
"""Loop orchestration helpers for the autonomous agent."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class LoopState:
    """Tracks the state of the experiment loop."""
    best_score: float | None = None
    best_commit: str | None = None
    consecutive_reverts: int = 0
    consecutive_crashes: int = 0
    last_crash_error: str | None = None
    total_experiments: int = 0
    total_keeps: int = 0
    total_reverts: int = 0
    total_crashes: int = 0
    strategy_categories_tried: list[str] = field(default_factory=list)

    # Thresholds
    stagnation_threshold: int = 5   # LOOP-08: reverts before strategy shift
    crash_threshold: int = 3        # LOOP-07: crashes before giving up


def should_keep(new_score: float, best_score: float | None) -> bool:
    """Decide whether to keep the new result.

    All metrics use sklearn convention: higher is better.
    """
    if best_score is None:
        return True  # First result always kept
    return new_score > best_score


def is_stagnating(state: LoopState) -> bool:
    """Check if loop has hit stagnation threshold (LOOP-08)."""
    return state.consecutive_reverts >= state.stagnation_threshold


def is_crash_stuck(state: LoopState) -> bool:
    """Check if we've exceeded crash recovery attempts (LOOP-07)."""
    return state.consecutive_crashes >= state.crash_threshold


# Strategy categories for stagnation escape
STRATEGY_CATEGORIES = [
    "hyperparameter_tuning",     # Adjust params of current model
    "algorithm_switch",          # Try entirely different algorithm
    "ensemble_methods",          # Combine multiple models
    "feature_preprocessing",     # Different preprocessing (scaling, etc.)
    "regularization_tuning",     # Adjust regularization strength
]


def suggest_strategy_shift(state: LoopState) -> str:
    """Suggest a different strategy category after stagnation."""
    tried = set(state.strategy_categories_tried)
    for category in STRATEGY_CATEGORIES:
        if category not in tried:
            return category
    # All tried -- cycle back to the beginning
    return STRATEGY_CATEGORIES[0]
```

### Pattern 3: CLAUDE.md as Loop Protocol
**What:** The CLAUDE.md file IS the experiment loop. Claude Code reads it and follows the instructions.
**When to use:** Generated once per experiment project.
**Example (template):**
```markdown
# AutoML Experiment Loop Protocol

## Setup
You are an autonomous ML researcher. Your job is to improve the metric
by modifying train.py. You run experiments, keep improvements, revert
failures, and NEVER STOP until manually interrupted.

## Files
- `prepare.py` — FROZEN. Do not modify. Contains data loading, evaluation, preprocessing.
- `train.py` — MUTABLE. This is the ONLY file you edit.
- `program.md` — Domain context. Read this at each iteration for guidance.
- `results.tsv` — Experiment log. Append results after each run.
- `run.log` — Last experiment output. Read metrics via grep.

## Phase 1: Multi-Draft Initialization
1. Generate 3-5 diverse train.py versions using different algorithm families
2. For each draft: edit train.py, commit, run, extract metric, log result
3. Select the best-performing draft as the starting point
4. Log all drafts in results.tsv with status "draft-keep" or "draft-discard"

## Phase 2: Iterative Improvement Loop

LOOP FOREVER:

1. Read `program.md` for domain-specific guidance
2. Think about what to try next based on results.tsv history
3. Edit train.py with your experimental idea
4. `git add train.py && git commit -m "description of change"`
5. Run: `uv run train.py > run.log 2>&1`
6. Extract results: `grep "^metric_value:\|^elapsed_sec:" run.log`
7. If grep is empty → CRASH. Read `tail -n 50 run.log` for traceback.
   - If fixable: fix and retry (max 3 consecutive crash attempts)
   - If unfixable: log crash, revert, move on
8. Log result to results.tsv
9. If metric improved → KEEP (advance the branch)
10. If metric equal or worse → REVERT (`git reset --hard HEAD~1`)
11. After 5 consecutive reverts → STAGNATION. Try a completely different strategy:
    - Switch algorithm family (e.g., tree-based → linear → ensemble)
    - Try radically different hyperparameters
    - Add/remove preprocessing steps
12. Go to step 1

## Rules
- **NEVER STOP.** Do not ask if you should continue. Run indefinitely.
- **NEVER modify prepare.py.** It is frozen.
- **ALWAYS redirect output** to run.log. Never let training output flood your context.
- **ALWAYS log results** to results.tsv after every experiment.
- **Keep it simple.** A small improvement that adds ugly complexity is not worth it.
```

### Pattern 4: program.md Domain Context Template
**What:** Template for human-written domain expertise the agent reads each iteration.
**When to use:** Generated with placeholders when scaffolding an experiment project.
**Example:**
```markdown
# Program: {dataset_name}

## Goal
{goal_description}

## Metric
{metric_name} ({direction})

## Data Description
{auto_generated_data_summary}

## Domain Expertise
<!-- Human fills this in with dataset-specific knowledge -->
- Known patterns:
- Feature hints:
- Known issues:
- Suggested strategies:

## Baselines
{auto_generated_baselines}
```

### Anti-Patterns to Avoid
- **Python while-loop as the experiment loop:** The agent IS the loop. A Python while-loop cannot control Claude Code's behavior. The loop protocol lives in CLAUDE.md.
- **Hardcoding algorithm names in drafts:** Use data-driven algorithm families keyed by task type (classification vs regression).
- **Resetting crash counter on success:** Only reset consecutive crash counter on a successful run, not on a different type of failure.
- **Comparing raw metric values across different metrics:** Always use the sklearn convention (higher=better) for comparisons. This is already enforced by prepare.py's METRIC_MAP.
- **Modifying ExperimentLogger.log_result() signature:** The current signature handles "draft-keep"/"draft-discard" status strings -- no changes needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Algorithm diversity | Manual list of model configs | ALGORITHM_FAMILIES dict keyed by task type | Ensures coverage of all major algorithm families, easily extensible |
| Metric comparison | Custom comparison functions | Simple `new > best` (sklearn convention is always higher=better) | All metrics already normalized by prepare.py's METRIC_MAP |
| Template rendering | Jinja2 or custom template engine | Simple string replacement / f-strings | train.py is a small Python script; regex substitution is sufficient |
| Loop state persistence | Database or JSON file | Dataclass in memory (LoopState) | State only needs to last the duration of one agent session; results.tsv is the persistent log |

**Key insight:** The Python helpers are thin wrappers. The loop's intelligence comes from Claude Code (the LLM agent), not from complex Python control flow. Keep the helpers simple and let the agent reason.

## Common Pitfalls

### Pitfall 1: Building a Python Loop Instead of Agent Instructions
**What goes wrong:** Developer builds `while True: run_experiment()` in Python, but Claude Code can't be controlled by Python.
**Why it happens:** Natural instinct is to write the loop in code.
**How to avoid:** Remember: Claude Code reads CLAUDE.md and follows instructions. The "loop" is Claude Code repeatedly executing tool calls. Python provides helpers, not control flow.
**Warning signs:** A `main()` function with a while loop that calls the LLM API.

### Pitfall 2: Draft Selection Without Proper Comparison
**What goes wrong:** Selecting the "best" draft based on raw metric values that mix different direction conventions.
**Why it happens:** Some metrics are naturally "lower is better" (RMSE) but sklearn returns them negated.
**How to avoid:** All comparisons use the sklearn-convention values from ExperimentResult.metric_value (always higher=better). The train_template.py already prints the sklearn-convention value.
**Warning signs:** A Ridge regression draft with RMSE -5.0 being selected over one with -3.0.

### Pitfall 3: Stagnation Detection Resets on Wrong Event
**What goes wrong:** Resetting the consecutive_reverts counter on a crash instead of only on a keep.
**Why it happens:** A crash is "not a revert" so it seems like progress.
**How to avoid:** Only reset consecutive_reverts to 0 when a keep occurs. Crashes increment a separate counter.
**Warning signs:** Agent keeps crashing but never triggers stagnation escape.

### Pitfall 4: Crash Recovery Attempting Same Fix Repeatedly
**What goes wrong:** Agent keeps trying the same fix for the same traceback, wasting 3 attempts.
**Why it happens:** Without tracking the specific error, the agent may not realize it's repeating.
**How to avoid:** Store the last crash error message. If the new crash error matches the previous one, increment the counter. If it's a different error, reset the counter.
**Warning signs:** 3 identical tracebacks in a row with the same "fix" applied each time.

### Pitfall 5: SVM Draft Taking Too Long on Large Datasets
**What goes wrong:** SVC with default kernel on a large dataset takes minutes instead of seconds, hitting the timeout.
**Why it happens:** SVM has O(n^2) to O(n^3) complexity. With 10k+ rows, it's very slow.
**How to avoid:** Use `SVC(kernel='linear')` for large datasets or skip SVM draft when dataset has >5000 rows. The time budget already protects against this (signal.alarm + subprocess timeout), but it wastes a draft slot.
**Warning signs:** SVM draft consistently timing out or taking 10x longer than tree-based drafts.

### Pitfall 6: Git Commit Before Run Creates Empty Reverts
**What goes wrong:** Autoresearch pattern is "edit, commit, run, maybe revert." If the agent commits before running and the run fails, it reverts with `git reset --hard HEAD~1` (not `HEAD`).
**Why it happens:** Autoresearch commits before running so that "revert" means going back to the pre-edit state.
**How to avoid:** Follow the same pattern: edit train.py, commit, run, then revert with `HEAD~1` (not `HEAD`). The current GitManager.revert() uses `HEAD` which would NOT undo the commit. This needs to be addressed.
**Warning signs:** After a revert, train.py still contains the failed experiment's code.

## Code Examples

### Draft Evaluation Flow
```python
# Example of how the agent uses the draft system
# (This is pseudo-code showing what CLAUDE.md instructs the agent to do)

# 1. Read task type from prepare.py output
task = "classification"  # or "regression"

# 2. Get algorithm families for this task
families = ALGORITHM_FAMILIES[task]

# 3. For each family, generate draft train.py, run, evaluate
draft_results = []
for algo in families:
    # Generate modified train.py
    new_content = generate_draft_train_py("train.py", algo)
    write_file("train.py", new_content)

    # Commit before run (autoresearch pattern)
    git.commit(f"Draft: {algo['name']}")

    # Run experiment
    result = runner.run()

    # Log result
    if result.status == "success":
        status = "draft-keep"  # tentatively; best one gets "draft-keep"
    else:
        status = "draft-discard"
    logger.log_result(commit, result.metric_value or 0.0, 0.0,
                      result.elapsed_sec, status, f"Draft: {algo['name']}")
    draft_results.append((algo['name'], result, commit))

# 4. Select best draft
best = max(draft_results, key=lambda x: x[1].metric_value or float('-inf'))
# Checkout the best commit
git._run("checkout", best[2])  # checkout best commit hash
```

### Keep/Revert Decision Flow
```python
# After each experiment run:
result = runner.run()

if result.status == "success" and result.metric_value is not None:
    if should_keep(result.metric_value, state.best_score):
        # KEEP: advance the branch
        state.best_score = result.metric_value
        state.best_commit = git.get_current_commit()
        state.consecutive_reverts = 0
        state.total_keeps += 1
        logger.log_result(commit, result.metric_value, 0.0,
                          result.elapsed_sec, "keep", result.description)
    else:
        # REVERT: go back to last good commit
        git._run("reset", "--hard", "HEAD~1")
        state.consecutive_reverts += 1
        state.total_reverts += 1
        logger.log_result(commit, result.metric_value, 0.0,
                          result.elapsed_sec, "discard", result.description)

        if is_stagnating(state):
            strategy = suggest_strategy_shift(state)
            state.strategy_categories_tried.append(strategy)
            state.consecutive_reverts = 0
            # Agent reads strategy suggestion and changes approach

elif result.status == "crash":
    state.consecutive_crashes += 1
    state.total_crashes += 1
    git._run("reset", "--hard", "HEAD~1")
    logger.log_result(commit, 0.0, 0.0, result.elapsed_sec,
                      "crash", result.description)

    if is_crash_stuck(state):
        state.consecutive_crashes = 0
        # Agent gives up on this approach, moves on
```

### Stagnation Escape
```python
# When is_stagnating() returns True, CLAUDE.md instructs:
# "You have reverted 5 times in a row. Your current approach is not working.
#  Try a RADICALLY different strategy from this list:
#  1. Switch to a completely different algorithm family
#  2. Try a very different hyperparameter range (10x larger/smaller)
#  3. Add ensemble methods (VotingClassifier, StackingClassifier)
#  4. Change preprocessing (add StandardScaler, try different imputation)
#  5. Simplify: remove features, reduce model complexity"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pure linear iteration (autoresearch) | Multi-draft + linear (AIDE insight) | 2024-2025 | Algorithm choice matters more than hyperparameter tuning; diverse starts prevent local optima |
| LLM-as-judge for metrics (AIDE) | Structured output + regex parsing | autoresearch pattern | Simpler, faster, no additional LLM calls needed |
| Tree search (AIDE, SELA) | Linear keep/revert after best draft | v1 design decision | Sufficient for v1; tree search deferred to v2 |
| Python orchestrator loop | Agent-as-loop (CLAUDE.md protocol) | autoresearch pattern | LLM reasons about what to try; Python just provides helpers |

## Open Questions

1. **Git revert depth for pre-committed changes**
   - What we know: Autoresearch commits BEFORE running, then reverts with reset. Our GitManager.revert() uses `reset --hard HEAD` which does NOT undo the commit.
   - What's unclear: Should we add a `revert_last_commit()` that does `reset --hard HEAD~1`?
   - Recommendation: YES. Add `GitManager.revert_last_commit()` that does `git reset --hard HEAD~1`. Keep the existing `revert()` (reset to HEAD) for reverting uncommitted changes. The CLAUDE.md protocol commits before running, matching autoresearch.

2. **Memory tracking in results.tsv**
   - What we know: ExperimentLogger.log_result() requires memory_mb but ExperimentResult doesn't track memory.
   - What's unclear: Should we add memory tracking to ExperimentRunner or pass 0.0?
   - Recommendation: Pass 0.0 for now. Memory tracking is nice-to-have for tabular ML where memory is rarely a constraint. Can add tracemalloc integration later.

3. **Draft count configurability**
   - What we know: Requirements say "3-5 diverse initial drafts."
   - What's unclear: Should this be configurable or fixed?
   - Recommendation: Default to 5 drafts (one per algorithm family). The ALGORITHM_FAMILIES dict already has 5 per task type. Let the agent skip drafts that timeout.

4. **CLAUDE.md placement**
   - What we know: CLAUDE.md is typically at the root of a project for Claude Code to read.
   - What's unclear: Should it be in the experiment directory or the project root?
   - Recommendation: In the experiment directory. Each experiment project is standalone. The CLI (Phase 3) will copy it there during scaffolding.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest, already installed) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOOP-01 | Run train.py, extract metric, decide keep/revert | integration | `uv run pytest tests/test_loop_helpers.py::test_keep_revert_decision -x` | No -- Wave 0 |
| LOOP-02 | stdout/stderr redirected to run.log | unit | Already tested in `tests/test_runner.py::TestExperimentRun::test_run_captures_log` | Yes |
| LOOP-03 | Agent reads metric via grep/regex | unit | Already tested in `tests/test_runner.py::TestMetricExtraction` | Yes |
| LOOP-04 | Keep/revert logic: improved -> commit; worse -> reset | unit | `uv run pytest tests/test_loop_helpers.py::test_should_keep -x` | No -- Wave 0 |
| LOOP-05 | Agent runs autonomously and indefinitely | manual-only | Verify CLAUDE.md contains "NEVER STOP" and loop protocol | N/A |
| LOOP-06 | Timeout enforcement at 2x budget | unit | Already tested in `tests/test_runner.py::TestErrorHandling::test_run_timeout` | Yes |
| LOOP-07 | Crash recovery with 3-attempt limit | unit | `uv run pytest tests/test_loop_helpers.py::test_crash_recovery_threshold -x` | No -- Wave 0 |
| LOOP-08 | Stagnation detection after 5 reverts | unit | `uv run pytest tests/test_loop_helpers.py::test_stagnation_detection -x` | No -- Wave 0 |
| CTX-01 | program.md template accepts domain expertise | unit | `uv run pytest tests/test_templates.py::test_program_md_template -x` | No -- Wave 0 |
| CTX-02 | Agent reads program.md each iteration | manual-only | Verify CLAUDE.md instructs re-reading program.md | N/A |
| CTX-03 | CLAUDE.md provides loop protocol | unit | `uv run pytest tests/test_templates.py::test_claude_md_template -x` | No -- Wave 0 |
| DRAFT-01 | Generate 3-5 diverse drafts | unit | `uv run pytest tests/test_drafts.py::test_generate_drafts -x` | No -- Wave 0 |
| DRAFT-02 | Each draft evaluated via frozen evaluation | integration | `uv run pytest tests/test_drafts.py::test_draft_evaluation -x` | No -- Wave 0 |
| DRAFT-03 | Best draft selected as starting point | unit | `uv run pytest tests/test_drafts.py::test_select_best_draft -x` | No -- Wave 0 |
| DRAFT-04 | Draft results logged with draft-keep/draft-discard | unit | `uv run pytest tests/test_drafts.py::test_draft_logging_status -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_drafts.py` -- covers DRAFT-01 through DRAFT-04 (draft generation, evaluation, selection, logging)
- [ ] `tests/test_loop_helpers.py` -- covers LOOP-01, LOOP-04, LOOP-07, LOOP-08 (keep/revert, crash tracking, stagnation)
- [ ] `tests/test_templates.py` -- covers CTX-01, CTX-03 (program.md and CLAUDE.md template generation)

*(LOOP-02, LOOP-03, LOOP-06 already tested by Phase 1's test_runner.py. LOOP-05, CTX-02 are manual verification of document content.)*

## Sources

### Primary (HIGH confidence)
- Autoresearch program.md (`/tmp/autoresearch/program.md`) -- complete loop protocol, NEVER STOP pattern, keep/revert logic, crash recovery, results.tsv format
- Phase 1 source code (runner.py, git_ops.py, experiment_logger.py, train_template.py, prepare.py) -- all APIs verified by reading actual implementation
- Phase 1 test suite (test_runner.py, test_git.py, test_logging.py) -- verified existing test coverage

### Secondary (MEDIUM confidence)
- AIDE research (from PROJECT.md analysis) -- multi-draft initialization pattern, algorithm diversity insight
- scikit-learn algorithm families -- standard algorithms for classification and regression verified from training knowledge + Phase 1 METRIC_MAP

### Tertiary (LOW confidence)
- None -- all findings derived from existing codebase and autoresearch reference

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies; all libraries already installed from Phase 1
- Architecture: HIGH -- directly derived from autoresearch program.md (read in full) and existing Phase 1 APIs
- Pitfalls: HIGH -- git revert depth issue identified by comparing autoresearch protocol with current GitManager implementation
- Multi-draft: HIGH -- algorithm families are well-established scikit-learn/xgboost/lightgbm patterns

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain, all patterns from existing codebase)
