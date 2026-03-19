# Architecture Patterns

**Domain:** Autonomous ML research framework (GSD-style architecture adapted for ML experimentation)
**Researched:** 2026-03-19
**Confidence:** HIGH (mapped from actual GSD source code at ~/.claude/get-shit-done/)

## GSD Architecture: Actual Source Map

### Directory Structure (from source)

```
~/.claude/get-shit-done/
  bin/
    gsd-tools.cjs              # Central CLI entry point — ALL tooling commands
    lib/
      core.cjs                 # Shared utilities: model profiles, git helpers, phase numbering, config loader
      state.cjs                # STATE.md CRUD: read/write/patch/advance/snapshot/frontmatter-sync
      config.cjs               # config.json CRUD: ensure-section, get, set (dot-notation paths)
      phase.cjs                # Phase lifecycle: list, find, add, insert, remove, complete, plan-index
      roadmap.cjs              # ROADMAP.md parsing: get-phase, analyze, update-plan-progress
      milestone.cjs            # Milestone lifecycle: requirements mark-complete, milestone archive
      verify.cjs               # Verification suite: summary check, plan-structure, phase-completeness, artifacts
      template.cjs             # Template fill: pre-fill PLAN.md, SUMMARY.md, VERIFICATION.md from frontmatter
      frontmatter.cjs          # YAML frontmatter extraction, reconstruction, validation
      init.cjs                 # Compound init commands: bootstrap context for each workflow type
      commands.cjs             # Command router: maps CLI subcommands to handler functions
  workflows/                   # ~35 markdown files — each is a "workflow prompt" consumed by Claude Code
    new-project.md             # Project initialization: questioning -> research -> requirements -> roadmap
    new-milestone.md           # Milestone setup: research -> requirements -> roadmap (reuses PROJECT.md)
    plan-phase.md              # Phase planning: discuss -> research -> plan breakdown
    execute-plan.md            # Plan execution: pattern routing (A/B/C), subagent spawning, SUMMARY creation
    verify-phase.md            # Goal-backward verification: must-haves check against codebase
    research-phase.md          # Phase research: spawn researcher subagent with context
    discuss-phase.md           # User discussion: gather implementation decisions -> CONTEXT.md
    transition.md              # Phase completion: mark done, advance state, update roadmap
    resume-project.md          # Session resume: read STATE.md, find interrupted work
    progress.md                # Progress display: phase overview, current position
    ...                        # ~25 more (settings, health, cleanup, add-todo, etc.)
  templates/                   # Document templates — define output format for each artifact
    state.md                   # STATE.md template (project short-term memory)
    config.json                # Default config.json template
    roadmap.md                 # ROADMAP.md template (phase structure)
    requirements.md            # REQUIREMENTS.md template
    phase-prompt.md            # PLAN.md template (executable plan format)
    summary.md                 # SUMMARY.md template (execution outcome)
    context.md                 # CONTEXT.md template (implementation decisions)
    verification-report.md     # VERIFICATION.md template
    research.md                # Phase research template
    ...
  references/                  # Reference docs — deep documentation on specific topics
    checkpoints.md             # Checkpoint types: human-verify, decision, human-action
    verification-patterns.md   # Stub detection, artifact verification patterns
    tdd.md                     # Test-driven development plan patterns
    git-integration.md         # Git branching, commit patterns
    model-profiles.md          # Model selection by agent type and budget
    ...
  VERSION                      # Framework version string
```

### Per-Project Structure (from templates)

```
.planning/
  PROJECT.md                   # Project identity: what, why, constraints, decisions
  ROADMAP.md                   # Phase breakdown with dependencies, goals, success criteria
  REQUIREMENTS.md              # Numbered requirements with traceability
  STATE.md                     # Living memory: current position, progress, blockers, session continuity
  config.json                  # Project-level settings: model profile, workflow toggles, parallelization
  agent-history.json           # Agent spawn/completion tracking
  current-agent-id.txt         # Interrupted agent recovery
  todos/pending/               # Captured ideas
  todos/completed/             # Addressed ideas
  codebase/                    # Codebase maps (brownfield projects)
  phases/
    01-foundation/
      01-01-PLAN.md            # Executable plan with frontmatter, tasks, verification
      01-01-SUMMARY.md         # Execution outcome (created AFTER plan completes)
      01-CONTEXT.md            # Implementation decisions from discussion
      01-RESEARCH.md           # Phase-specific research
      01-VERIFICATION.md       # Goal-backward verification report
    02-core-loop/
      ...
  milestones/
    v1.0-phases/               # Archived phase directories from completed milestones
    v1.0-ROADMAP.md            # Archived roadmap
```

### Key Architectural Patterns in GSD

**1. Init-Pattern (Context Bootstrapping)**
Every workflow calls `gsd-tools.cjs init <workflow-type> [args]` as its first step. The init command gathers ALL needed context (models, config, file paths, phase state, existing artifacts) into a single JSON blob. This prevents workflows from doing N file reads to understand context.

**2. Markdown-as-Database**
All state is stored in markdown files with optional YAML frontmatter. STATE.md uses `**Field:** value` format with regex-based CRUD. PLAN.md uses YAML frontmatter for machine-readable fields (wave, depends_on, files_modified, must_haves). The `state.cjs` module auto-syncs a YAML frontmatter block from the markdown body on every write.

**3. Workflow-as-Prompt**
Each workflow file (`.md`) is a structured prompt that Claude Code follows. Workflows reference other files via `@path/to/file.md` annotations. They define step-by-step processes with conditional branches. The workflow IS the execution logic -- there's no separate runtime engine interpreting it.

**4. Model Profile System**
A hardcoded MODEL_PROFILES table maps `(agent-type, budget-profile)` to model names. Agent types: gsd-planner, gsd-executor, gsd-verifier, gsd-phase-researcher, etc. Budget profiles: quality (opus for everything), balanced (opus for planning, sonnet for execution), budget (sonnet/haiku). Per-agent overrides in config.json.

**5. Subagent Spawning (Task)**
Claude Code's `Task()` function spawns fresh-context subagents. Each subagent gets a self-contained prompt with: objective, files_to_read, execution_context references, output format. The orchestrator (main context) stays lean while subagents do heavy work. Agent tracking via `agent-history.json` and `current-agent-id.txt` enables crash recovery.

**6. Wave-Based Parallelism**
Plans within a phase are assigned `wave` numbers at planning time. Wave 1 plans run in parallel (no dependencies, no file conflicts). Wave 2 plans wait for Wave 1 completion. The parallelism is declared (frontmatter), not discovered at runtime.

**7. Goal-Backward Verification**
Plans carry `must_haves` in frontmatter: truths (observable behaviors), artifacts (files that must exist with real content), key_links (wiring between components). After execution, a verification subagent checks these against the actual codebase. This catches "completed task but didn't achieve goal" failures.

---

## AutoLab Architecture: Recommended Design

### Design Principle: GSD Adapted for ML

GSD manages software development phases. AutoLab manages ML experiment loops. The core architectural patterns transfer, but the "what's being managed" changes:

| GSD Concept | AutoLab Analog |
|------------|----------------|
| Phase | Experiment campaign (e.g., "baseline", "feature engineering", "hyperparameter tuning") |
| Plan (PLAN.md) | Experiment protocol (what to try, how to evaluate) |
| Summary (SUMMARY.md) | Experiment result (metrics, artifacts, keep/revert decision) |
| STATE.md | Experiment state (best score, iteration count, stagnation tracking) |
| ROADMAP.md | Campaign plan (multi-draft start -> iterate -> branch-on-stagnation) |
| Workflow prompts | Protocol prompts (CLAUDE.md templates per domain) |
| Hooks | Guardrails (frozen file zones, cost caps, metric validation) |
| Verification | Metric validation (beats baseline? no leakage? reproducible?) |
| config.json | Experiment config (domain, metric, time budget, resource limits) |

### Component Diagram

```
                           autolab CLI
                               |
                    +----------+----------+
                    |                     |
              ScaffoldEngine         RunEngine
              (setup experiment)     (run experiment loop)
                    |                     |
                    v                     v
            +-------+-------+     +------+------+
            |               |     |             |
        DomainPlugin    ProtocolGen  StateManager
        (tabular/dl/ft) (CLAUDE.md)  (experiment state)
            |               |             |
            v               v             v
        DataLoader      TemplateEngine  GitOps
        Evaluator       PromptRenderer  Checkpoint
        Baselines       RuleSet         Journal
        Diagnostics                     Scoreboard
```

### Component Boundaries

| Component | Responsibility | Inputs | Outputs | Communicates With |
|-----------|---------------|--------|---------|-------------------|
| **CLI** | Parse user command, route to engine | User args (dataset, goal, mode) | Exit code, log output | ScaffoldEngine, RunEngine |
| **ScaffoldEngine** | Create experiment directory from dataset | CSV/Parquet + config | Complete experiment dir | DomainPlugin, ProtocolGen, DataLoader |
| **RunEngine** | Orchestrate the experiment loop | Experiment dir path | Final results, best model | StateManager, GitOps, DomainPlugin |
| **DomainPlugin** | Domain-specific logic (data prep, baselines, diagnostics) | Raw data + config | Prepared data, baseline scores, diagnostics | DataLoader, Evaluator, Baselines, Diagnostics |
| **ProtocolGen** | Generate CLAUDE.md protocol prompt | Domain config + plugin metadata | CLAUDE.md file | TemplateEngine, DomainPlugin |
| **StateManager** | Track experiment state across iterations | Keep/revert decisions, metrics | STATE.json, experiments.md | GitOps, Checkpoint, Journal |
| **GitOps** | Git branch/commit/revert operations | Commit messages, file lists | Commit hashes, branch names | StateManager |
| **Checkpoint** | Save/restore experiment state for resume | LoopState object | checkpoint.json | StateManager |
| **Journal** | Structured knowledge accumulation | Experiment results, diagnostics | experiments.md updates | StateManager, Diagnostics |
| **Scoreboard** | Multi-agent coordination (swarm mode) | Agent results | Ranked results, claims | RunEngine |

### Data Flow: Single Experiment Run

```
1. USER: autolab run ./experiment-housing/ --mode=tabular

2. CLI parses args -> RunEngine.start(experiment_dir, mode="tabular")

3. RunEngine:
   a. StateManager.load()             # Read checkpoint.json if exists
   b. plugin = PluginRegistry.get("tabular")
   c. protocol = ProtocolGen.render(plugin, experiment_dir)  # Write CLAUDE.md
   d. GitOps.init_branch("experiment-main")

4. EXPERIMENT LOOP (Claude Code executes CLAUDE.md):
   a. Read experiments.md             # Journal: what worked, what didn't
   b. Read program.md                 # Domain expertise
   c. Modify train.py                 # The mutable zone
   d. Run: python train.py            # Execute experiment
   e. Evaluator.parse(run.log)        # Extract metrics
   f. Baselines.compare(metrics)      # Beat naive baseline?

   g. IF improvement:
      - GitOps.commit("keep: MAPE 0.029 -> 0.025")
      - Journal.record_success(hypothesis, metrics, what_worked)
      - StateManager.update(best_score, best_commit, reset_reverts)
      - Checkpoint.save()

   h. IF regression:
      - GitOps.revert()
      - Journal.record_failure(hypothesis, metrics, why_failed)
      - StateManager.increment_reverts()
      - IF reverts >= 3: branch_on_stagnation()

   i. Diagnostics.analyze(predictions, actuals)  # WHERE does model fail?
   j. GOTO (a) -- NEVER STOP
```

### Plugin System Design

The plugin system is the central architectural decision. Each ML domain (tabular, deep learning, fine-tuning) provides:

```python
class DomainPlugin(Protocol):
    """Interface every domain plugin must implement."""

    name: str                          # "tabular", "deeplearning", "finetune"
    display_name: str                  # "Tabular ML", "Deep Learning", "LLM Fine-Tuning"

    # --- Scaffold Phase ---
    def validate_data(self, data_path: Path, config: dict) -> DataSummary:
        """Check dataset is valid for this domain. Return summary stats."""
        ...

    def create_prepare_module(self, data_summary: DataSummary, output_dir: Path) -> Path:
        """Generate the frozen prepare.py for this domain."""
        ...

    def create_train_template(self, data_summary: DataSummary, output_dir: Path) -> Path:
        """Generate the initial mutable train.py."""
        ...

    def get_baselines(self, data_summary: DataSummary) -> list[Baseline]:
        """Compute baseline scores the agent must beat."""
        ...

    def get_evaluator(self) -> Evaluator:
        """Return metric evaluation function for this domain."""
        ...

    # --- Protocol Phase ---
    def get_protocol_rules(self) -> list[str]:
        """Domain-specific rules for CLAUDE.md."""
        ...

    def get_frozen_files(self) -> list[str]:
        """Files the agent must not modify (enforced by hooks/protocol)."""
        ...

    def get_mutable_files(self) -> list[str]:
        """Files the agent IS allowed to modify."""
        ...

    # --- Runtime Phase ---
    def get_diagnostics(self) -> Diagnostics:
        """Return diagnostic analyzer for this domain."""
        ...

    def get_search_space(self) -> dict | None:
        """Optional Optuna search space definition."""
        ...

    # --- Resource Limits ---
    def default_time_budget(self) -> int:
        """Default seconds per experiment run."""
        ...

    def default_resource_limits(self) -> ResourceLimits:
        """GPU hours, disk space, cost caps."""
        ...
```

**Plugin Registration:**
```python
# autolab/plugins/__init__.py
from autolab.plugins.tabular import TabularPlugin
from autolab.plugins.deeplearning import DeepLearningPlugin
from autolab.plugins.finetune import FineTunePlugin

REGISTRY: dict[str, type[DomainPlugin]] = {
    "tabular": TabularPlugin,
    "deeplearning": DeepLearningPlugin,
    "finetune": FineTunePlugin,
}

def get_plugin(name: str) -> DomainPlugin:
    cls = REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown domain: {name}. Available: {list(REGISTRY.keys())}")
    return cls()
```

**Plugin Lifecycle:**
1. **Registration:** Plugin class registered in REGISTRY dict at import time
2. **Instantiation:** `get_plugin(mode)` creates instance when CLI runs
3. **Scaffold:** Plugin's `validate_data`, `create_prepare_module`, `create_train_template`, `get_baselines` called during `autolab scaffold`
4. **Protocol:** Plugin's `get_protocol_rules`, `get_frozen_files`, `get_mutable_files` used to generate CLAUDE.md
5. **Runtime:** Plugin's `get_diagnostics`, `get_evaluator` used during experiment loop
6. **No hot-loading:** Plugins are selected at scaffold time and fixed for the experiment's lifetime

### Protocol Prompt System (CLAUDE.md)

The protocol prompt is the primary behavior control mechanism. GSD uses workflow `.md` files consumed by Claude Code. AutoLab uses CLAUDE.md files consumed by Claude Code in headless (`claude -p`) mode.

**Template Architecture:**
```
autolab/templates/
  base_protocol.md.tmpl          # Shared rules: never-stop loop, keep/revert, checkpoint
  tabular_protocol.md.tmpl       # Tabular-specific: scikit-learn patterns, Optuna, feature engineering
  deeplearning_protocol.md.tmpl  # DL-specific: PyTorch patterns, learning rate schedules, early stopping
  finetune_protocol.md.tmpl      # Fine-tuning-specific: LoRA config, quantization, evaluation
  diagnostics_section.md.tmpl    # Shared diagnostics protocol (injected by all domains)
  journal_section.md.tmpl        # Shared journal protocol (read/write experiments.md)
  stagnation_section.md.tmpl     # Shared branch-on-stagnation protocol
```

**Rendering:**
```python
def render_protocol(plugin: DomainPlugin, experiment_dir: Path, config: dict) -> str:
    """Compose CLAUDE.md from base + domain templates + plugin rules."""
    base = load_template("base_protocol.md.tmpl")
    domain = load_template(f"{plugin.name}_protocol.md.tmpl")
    diagnostics = load_template("diagnostics_section.md.tmpl")
    journal = load_template("journal_section.md.tmpl")
    stagnation = load_template("stagnation_section.md.tmpl")

    context = {
        "frozen_files": plugin.get_frozen_files(),
        "mutable_files": plugin.get_mutable_files(),
        "protocol_rules": plugin.get_protocol_rules(),
        "baselines": plugin.get_baselines(data_summary),
        "metric": config["metric"],
        "time_budget": config.get("time_budget", plugin.default_time_budget()),
        **config,
    }

    return compose(base, domain, diagnostics, journal, stagnation, context)
```

### State Management

**Experiment State (adapted from GSD's STATE.md pattern):**

```json
// experiment_dir/state.json
{
    "version": "1.0",
    "domain": "tabular",
    "metric": "rmse",
    "metric_direction": "minimize",
    "best_score": 0.0291,
    "best_commit": "abc1234",
    "iteration": 47,
    "loop_phase": "iteration",
    "consecutive_reverts": 0,
    "consecutive_crashes": 0,
    "strategy_categories_tried": ["linear", "tree"],
    "stagnation_branches": ["explore-neural"],
    "total_experiments": 47,
    "total_keeps": 12,
    "total_reverts": 35,
    "session_start": "2026-03-19T22:00:00Z",
    "last_activity": "2026-03-20T06:30:00Z",
    "cost_spent_usd": 3.19,
    "cost_cap_usd": 10.00
}
```

**Journal (experiments.md) -- Structured Knowledge:**
```markdown
## What Works
- Ridge regression with lag features: MAPE 0.029
- Shift-first pattern prevents leakage

## What Doesn't Work
- Random Forest overfits on small datasets
- Raw date features add noise

## Hypotheses Queue
1. Try gradient boosting with regularization
2. Add rolling mean features with larger windows

## Error Patterns
- Model consistently overpredicts Q4 values
- Weekend patterns not captured
```

### Guardrails System

GSD uses Claude Code hooks (PreToolUse/PostToolUse) for boundary enforcement. AutoLab adapts this via protocol-first guardrails (CLAUDE.md rules) reinforced by runtime validation.

**Protocol-Level Guardrails (CLAUDE.md rules):**
- Frozen file zones: "NEVER modify prepare.py"
- Dual-baseline gate: "Only keep if beats BOTH naive and seasonal naive"
- Commit protocol: "Commit on keep with structured message"
- Resource limits: "Stop if cost exceeds $X"

**Runtime Guardrails (code enforcement):**
```python
class GuardrailEngine:
    def check_frozen_files(self, modified_files: list[str]) -> bool:
        """Verify no frozen files were modified since last commit."""

    def check_metric_improvement(self, current: float, best: float, direction: str) -> bool:
        """Verify metric actually improved (handles minimize vs maximize)."""

    def check_cost_cap(self, spent: float, cap: float) -> bool:
        """Verify cost hasn't exceeded budget."""

    def check_time_budget(self, elapsed: float, budget: float) -> bool:
        """Verify single experiment run didn't exceed time limit."""

    def check_leakage(self, train_data, test_data, features) -> list[str]:
        """Check for common data leakage patterns."""
```

### Swarm Mode Architecture

Multiple Claude Code agents running in parallel git worktrees, coordinated via file-locked scoreboard (proven in v1.0):

```
experiment-housing/           # Main worktree
experiment-housing-worker-1/  # Worktree 1 (claude -p agent)
experiment-housing-worker-2/  # Worktree 2 (claude -p agent)
experiment-housing-worker-3/  # Worktree 3 (claude -p agent)

Shared:
  scoreboard.json             # File-locked, ranked results
  claims.json                 # Strategy claims to prevent duplication
```

---

## Recommended Package Structure

```
autolab/
  __init__.py
  cli.py                       # Click/Typer CLI entry point
  engine/
    __init__.py
    scaffold.py                # ScaffoldEngine: create experiment directory
    run.py                     # RunEngine: orchestrate experiment loop
    swarm.py                   # SwarmEngine: parallel agent coordination
  core/
    __init__.py
    state.py                   # StateManager: experiment state CRUD
    git_ops.py                 # GitOps: branch/commit/revert
    checkpoint.py              # Checkpoint: save/restore for resume
    journal.py                 # Journal: experiments.md read/write
    evaluator.py               # Evaluator: metric parsing and comparison
    guardrails.py              # GuardrailEngine: frozen files, cost caps, leakage
    diagnostics.py             # Base diagnostics interface
  plugins/
    __init__.py                # Plugin registry
    base.py                    # DomainPlugin protocol/ABC
    tabular/
      __init__.py              # TabularPlugin implementation
      prepare.py               # Frozen data preparation
      train_template.py        # Initial train.py generator
      baselines.py             # Naive, seasonal-naive, mean baselines
      diagnostics.py           # Tabular-specific error analysis
      search_space.py          # Optuna search space definitions
    deeplearning/
      __init__.py              # DeepLearningPlugin implementation
      prepare.py               # Dataset/DataLoader setup
      train_template.py        # PyTorch training loop generator
      baselines.py             # Simple model baselines
      diagnostics.py           # Loss curves, gradient analysis
    finetune/
      __init__.py              # FineTunePlugin implementation
      prepare.py               # Dataset formatting (chat, instruction)
      train_template.py        # LoRA/QLoRA training script generator
      baselines.py             # Pre-fine-tune evaluation baseline
      diagnostics.py           # Perplexity analysis, generation quality
  templates/
    __init__.py                # Template loader and renderer
    base_protocol.md.tmpl      # Shared CLAUDE.md base
    tabular_protocol.md.tmpl   # Tabular CLAUDE.md
    deeplearning_protocol.md.tmpl
    finetune_protocol.md.tmpl
    diagnostics_section.md.tmpl
    journal_section.md.tmpl
    stagnation_section.md.tmpl
    program.md.tmpl            # Domain expertise template
    experiments.md.tmpl        # Journal template
  scoreboard/
    __init__.py
    scoreboard.py              # Scoreboard read/write with file locking
    claims.py                  # Strategy claim/release
tests/
  ...
```

## Patterns to Follow

### Pattern 1: Protocol-First Behavior Control
**What:** All agent behavior rules are text in CLAUDE.md, not code enforcement. Code enforces only what protocol cannot (file integrity, metric math).
**When:** Always. This is the core insight from v1-v3.
**Why:** Claude Code follows text instructions reliably. Code enforcement creates brittleness. Protocol can be updated without code changes.

### Pattern 2: Plugin Interface via Protocol (Python)
**What:** Use Python's Protocol class (typing.Protocol) for the plugin interface, not ABC.
**When:** Defining the DomainPlugin contract.
**Why:** Structural subtyping -- plugins work if they have the right methods, no inheritance required. Better for third-party plugins.

### Pattern 3: Init-Pattern for Context Loading
**What:** Each engine method starts by loading all needed context in one call, not N separate file reads.
**When:** Any function that needs experiment state + config + plugin info.
**Why:** Reduces I/O, prevents partial-state bugs, mirrors GSD's init pattern.

### Pattern 4: Markdown + JSON Dual State
**What:** Human-readable state in experiments.md (journal), machine-readable state in state.json (checkpoint).
**When:** Always for experiment state.
**Why:** Humans read the journal. Code reads the JSON. Both are authoritative for their domain.

## Anti-Patterns to Avoid

### Anti-Pattern 1: God Module
**What:** Putting all logic in one file (like v1.0's runner.py + loop_helpers.py doing everything)
**Why Bad:** Impossible to test, modify, or extend one concern without touching others
**Instead:** Separate concerns into engine/, core/, plugins/ as shown above

### Anti-Pattern 2: Code-Enforced Behavior
**What:** Writing Python code to enforce every agent behavior rule
**Why Bad:** Fragile, hard to update, creates arms race between agent and guardrails
**Instead:** Protocol-first (CLAUDE.md rules) with code only for integrity checks

### Anti-Pattern 3: Monolithic Plugin
**What:** One giant class per domain with all methods
**Why Bad:** Can't test baselines independently from diagnostics, can't reuse across domains
**Instead:** Composed plugins: each plugin delegates to focused modules (baselines.py, diagnostics.py, etc.)

### Anti-Pattern 4: Implicit State
**What:** Tracking experiment state in memory only, or spread across many files
**Why Bad:** Crashes lose state, can't resume, can't inspect
**Instead:** state.json + experiments.md, updated after every decision

## Build Order (Dependency Chain)

The following build order respects component dependencies:

```
Phase 1: Core Foundation
  - core/state.py (StateManager)
  - core/git_ops.py (GitOps)
  - core/checkpoint.py (Checkpoint)
  - core/evaluator.py (Evaluator)
  - plugins/base.py (DomainPlugin Protocol)
  Dependencies: None. Everything else depends on these.

Phase 2: Plugin Infrastructure
  - plugins/__init__.py (Registry)
  - templates/__init__.py (Template loader/renderer)
  - templates/base_protocol.md.tmpl
  Dependencies: Phase 1 (needs DomainPlugin protocol)

Phase 3: Tabular Plugin (first domain)
  - plugins/tabular/* (full implementation)
  - templates/tabular_protocol.md.tmpl
  Dependencies: Phase 1 + 2 (needs base protocol, registry, evaluator)

Phase 4: Scaffold Engine
  - engine/scaffold.py
  - cli.py (scaffold subcommand)
  Dependencies: Phase 1 + 2 + 3 (needs plugin, templates, state to create experiment dir)

Phase 5: Run Engine
  - engine/run.py
  - core/journal.py
  - core/guardrails.py
  - core/diagnostics.py
  - cli.py (run subcommand)
  Dependencies: Phase 1 + 2 + 3 + 4 (needs everything above to orchestrate loop)

Phase 6: E2E Validation
  - Run scaffold + experiment on real dataset
  - Validate full loop works end-to-end
  Dependencies: Phase 1-5

Phase 7: Additional Domains
  - plugins/deeplearning/*
  - plugins/finetune/*
  Dependencies: Phase 1-5 (plugin interface proven with tabular)

Phase 8: Swarm Mode
  - engine/swarm.py
  - scoreboard/*
  Dependencies: Phase 1-6 (needs working single-agent loop first)
```

## Scalability Considerations

| Concern | Single Agent | Swarm (3-5 agents) | Future |
|---------|-------------|-------------------|--------|
| State management | state.json per experiment | state.json per worktree + scoreboard | Could add Redis for real-time coordination |
| Git operations | Sequential commits | File-locked scoreboard, worktree isolation | Git LFS for large model artifacts |
| Cost tracking | Per-experiment cost cap | Per-agent + total cost cap | Could add cost-aware scheduling |
| Disk usage | Train artifacts in experiment dir | Worktree duplication ~3-5x | Shared dataset, copy-on-write worktrees |
| Plugin loading | Import at scaffold time | Same (each worktree imports independently) | Lazy loading for large plugin dependencies |

## Sources

- GSD source code at `~/.claude/get-shit-done/` (directly read and mapped)
- autopilot-ml v1.0-v3.0 source at `/home/tlupo/AutoML/src/automl/` (existing implementation)
- GSD `bin/lib/state.cjs` -- State management patterns (frontmatter sync, field extraction)
- GSD `bin/lib/init.cjs` -- Context bootstrapping pattern (compound init commands)
- GSD `bin/lib/core.cjs` -- Model profile system, config loading
- GSD `workflows/execute-plan.md` -- Subagent spawning patterns (Pattern A/B/C)
- GSD `workflows/verify-phase.md` -- Goal-backward verification pattern
- GSD `templates/phase-prompt.md` -- Plan structure with must_haves
- GSD `references/checkpoints.md` -- Checkpoint types and execution protocol
- autopilot-ml `src/automl/scaffold.py` -- Existing scaffold pattern
- autopilot-ml `src/automl/templates/claude.md.tmpl` -- Existing protocol prompt
