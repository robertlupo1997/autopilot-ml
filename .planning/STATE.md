---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: completed
stopped_at: Completed 20-01-PLAN.md
last_updated: "2026-03-21T03:14:42.805Z"
last_activity: 2026-03-21 -- Completed 17-01 (Domain-aware export + verifier + diagnostics mapping)
progress:
  total_phases: 30
  completed_phases: 30
  total_plans: 54
  completed_plans: 54
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-19)

**Core value:** Leave an ML research agent running overnight with full confidence it will follow protocol, respect resource boundaries, track state, and produce meaningful results -- without human intervention.
**Current focus:** Phase 17 in progress -- DL/FT artifact export and diagnostics wiring

## Current Position

Phase: 17 of 18 (Wire DL/FT Artifact Export + Diagnostics)
Plan: 2 of 2 complete
Status: Phase 17 complete
Last activity: 2026-03-21 -- Completed 17-01 (Domain-aware export + verifier + diagnostics mapping)

Progress: [██████████] 29/29 plans (100%)

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: 4 min
- Total execution time: 0.60 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-core-engine | 3 | 17 min | 6 min |
| 02-tabular-plugin | 3 | 6 min | 2 min |
| 03-scaffold-cli-run-engine | 3 | 10 min | 3 min |
| 04-e2e-validation-ux | 2 | 7 min | 4 min |
| 05-domain-plugins-swarm | 3 | 17 min | 4 min |

**Recent Trend:**
- Last 5 plans: 04-01 (3 min), 04-02 (4 min), 05-01 (4 min), 05-02 (5 min), 05-03 (4 min)
- Trend: Stable at ~3-4 min/plan
| Phase 05 P01 | 4min | 3 tasks | 5 files |
| Phase 05 P02 | 5min | 3 tasks | 4 files |
| Phase 06 P01 | 2min | 2 tasks | 2 files |
| Phase 07 P01 | 3min | 2 tasks | 4 files |
| Phase 07 P02 | 4min | 2 tasks | 2 files |
| Phase 08 P01 | 2min | 2 tasks | 2 files |
| Phase 08 P02 | 3min | 2 tasks | 4 files |
| Phase 09 P01 | 3min | 2 tasks | 5 files |
| Phase 10 P01 | 2min | 2 tasks | 6 files |
| Phase 11 P01 | 4min | 2 tasks | 7 files |
| Phase 12 P01 | 3min | 2 tasks | 2 files |
| Phase 13 P01 | 4min | 2 tasks | 6 files |
| Phase 14 P01 | 3min | 2 tasks | 3 files |
| Phase 15 P01 | 2min | 2 tasks | 2 files |
| Phase 16 P01 | 3min | 2 tasks | 3 files |
| Phase 17 P02 | 2min | 2 tasks | 5 files |
| Phase 17 P01 | 2min | 2 tasks | 6 files |
| Phase 18 P01 | 2min | 2 tasks | 2 files |
| Phase 19 P01 | 3min | 2 tasks | 6 files |
| Phase 20 P01 | 3min | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Fresh rewrite -- no code carried from v1-v3, old code is reference only
- [Roadmap]: Plugin architecture via typing.Protocol (structural subtyping, no ABC inheritance)
- [Roadmap]: JSON for machine state, markdown for human journal (rejected GSD's markdown-as-database)
- [Roadmap]: Tabular plugin built first to validate architecture before DL/fine-tuning
- [01-01]: Guarded old conftest.py numpy/pandas imports to allow mlforge tests without heavy ML deps
- [01-01]: Package renamed from automl to mlforge in pyproject.toml; old src/automl/ left intact
- [01-02]: JournalEntry as dataclass with typed fields rather than free-form dict args
- [01-02]: Journal takes Path to file directly (not directory + filename constant)
- [01-02]: GitManager checks for no-changes via index.diff('HEAD') before committing
- [01-03]: Templates package: rendering functions in templates/__init__.py to coexist with .j2 files
- [01-03]: Guard script uses python3 fallback for JSON parsing (no jq dependency)
- [01-03]: Hook settings use both permissions.deny and PreToolUse hook for defense in depth
- [Phase 02]: Correlate abs_error (not signed error) with features for actionable diagnostics
- [Phase 02]: ALGORITHM_FAMILIES stores class names as strings to avoid heavy deps at import time
- [Phase 02]: trigger_stagnation_branch uses git.checkout + create_head for detached-HEAD-safe branching
- [02-01]: ML deps added as required (not optional) -- this is an ML tool
- [02-01]: prepare.py copied via Path.read_text for scaffold -- avoids import-time ML dep issues
- [02-01]: Baseline gate uses strict inequality (must beat, not tie) for both directions
- [Phase 02]: Diff rendered in collapsible details sections, not as extra table column
- [03-01]: CLI overrides Config defaults (not TOML merge) for simplicity
- [03-01]: Auto-register TabularPlugin in scaffold if not in registry
- [03-02]: ResourceGuardrails.should_stop delegates to stop_reason for DRY single-source-of-truth
- [03-02]: CostTracker updates SessionState.cost_spent_usd directly for crash-safe persistence
- [03-02]: DeviationHandler resets retry count on keep (not on revert) to prevent retry leak
- [03-02]: min_free_disk_gb defaults to 1.0 GB as instance attribute (not Config field)
- [03-01]: TOML serialization via string formatting (no tomli_w dependency)
- [03-03]: RunEngine extracts metric_value from nested JSON result string (claude -p envelope)
- [03-03]: OOM retry recursively calls _process_result with fresh _run_one_experiment
- [03-03]: SIGINT handler sets _stop_requested flag for clean checkpoint save in finally block
- [03-03]: CLI resume returns error 1 if no checkpoint found (not silent failure)
- [04-01]: Binary classification uses accuracy, multi-class uses f1_weighted, regression uses r2
- [04-01]: Numeric target with <=20 unique values treated as classification
- [04-01]: Date detection samples head(20) with >80% parse threshold
- [04-01]: Target column extracted from goal via 'predict X' regex with last-word fallback
- [04-01]: Simple mode profiling failure falls back silently to defaults
- [04-01]: Custom frozen/mutable replace plugin defaults entirely (not merge)
- [04-02]: LiveProgress.log() added for post-loop messages (console.print when live, plain print otherwise)
- [04-02]: Results recorded in _process_result alongside existing deviation logic (not replacing)
- [04-02]: Stop action records as crash status in results tracker
- [05-03]: fcntl.LOCK_EX for atomic publish, lockless reads for display
- [05-03]: dataclasses.replace() for child config creation -- clean budget splitting
- [05-03]: Append-only TSV format survives agent crashes without data loss
- [05-03]: Platform guard: RuntimeError on non-Unix (no fcntl) with WSL recommendation
- [Phase 05]: Module-level torch imports in prepare.py are safe -- standalone file copied during scaffold, never imported by mlforge core
- [Phase 05]: Both dl and ft pyproject.toml optional deps added in Plan 01 to avoid parallel write conflicts with Plan 02
- [Phase 05]: Custom task renders minimal nn.Module skeleton with TODO placeholder, time budget and early stopping pre-wired
- [05-02]: All peft/trl/bitsandbytes imports lazy (in-method) for GPU-free import
- [05-02]: LoRA config targets all-linear modules for broad adapter coverage
- [05-02]: Template variables as Python constants (LORA_R, LORA_ALPHA) for readable rendered train.py
- [Phase 06]: Read CLAUDE.md via Path.read_text() inline rather than passing file path to CLI
- [Phase 06]: Omit --append-system-prompt entirely when CLAUDE.md missing (graceful skip)
- [Phase 06]: Keep max_turns_per_experiment in Config for forward compatibility, stop passing to CLI
- [07-01]: Baseline gate checks BEFORE git commit in keep path (prevents sub-baseline code from persisting)
- [07-01]: Previous best_metric saved before state update so journal delta is accurate
- [07-01]: Stagnation check runs after every revert, not just after baseline gate downgrades
- [07-01]: importlib.util used to load prepare.py dynamically for baseline computation
- [Phase 07]: Diagnostics called after both keep and revert in _process_result (always analyze latest predictions)
- [Phase 07]: Lazy pandas import inside _run_diagnostics() to avoid import-time dependency
- [Phase 07]: prompt_override parameter on _run_one_experiment() for draft prompt injection
- [08-01]: Dispatch map (_REGISTRATION_FUNCTIONS dict) rather than if/elif chain for extensibility
- [08-01]: Unknown domains silently ignored (no-op) rather than raising errors
- [Phase 08]: Lazy import of SwarmManager inside if-args.swarm block to avoid heavy imports when not using swarm
- [Phase 08]: Lazy import of verify_best_result inside SwarmManager.run() try block to avoid circular imports
- [Phase 09]: Default task is classification when plugin_settings has no task key
- [Phase 09]: csv_path stored as filename only (dataset_path.name) not full path
- [Phase 10]: Use plugin_settings csv_path/target_column to feed prepare.load_data()+split_data() in _compute_baselines()
- [11-01]: Return None from trigger_stagnation_branch instead of raising ValueError for graceful degradation
- [11-01]: Output Format section added to base_claude.md.j2 (all domains) not just tabular-specific template
- [12-01]: Task mapping mutates config in-place (established pattern from CLI override)
- [12-01]: Mapping runs before validation so profiler outputs pass DL validation
- [12-01]: Fixed test_scaffold_finetuning_domain to use valid FT config (metric+model_name)
- [Phase 13]: Tag name format: best-{run_id} with unknown fallback, ValueError caught for resume idempotency
- [14-01]: Use child_config.budget_usd (total session budget) for --max-budget-usd, not per_experiment_budget_usd
- [14-01]: Read CLAUDE.md content inline via Path.read_text() for --append-system-prompt (matching engine.py pattern)
- [14-01]: Omit --append-system-prompt entirely when CLAUDE.md missing (graceful skip)
- [Phase 15]: Lazy import FineTuningPlugin._VALID_METRICS inside _map_task_for_domain to avoid import-time dependency
- [Phase 15]: Override metric only when NOT in plugin _VALID_METRICS (preserves expert mode explicit metrics)
- [Phase 15]: Auto-default model_name for FT domain replaces hard rejection -- test updated accordingly
- [Phase 16]: Data reload in __main__ is intentional duplication -- objective() runs many trials, __main__ retrain is single run
- [Phase 16]: Artifact writes placed before JSON print to maintain engine's last-line JSON parsing contract
- [17-02]: DL predictions from best_model.pt state dict reload, not last epoch weights
- [17-02]: FT predictions guarded to loss/perplexity only (ROUGE produces text, not numeric)
- [17-02]: FT y_true=0.0 placeholder since loss is self-referential
- [17-01]: Ordered candidate list with first-match-wins for artifact discovery priority
- [17-01]: _CLASSIFICATION_TASKS as module-level frozenset for reuse and testability
- [17-01]: Normalized task_type passed to _format_diagnostics instead of raw task value
- [Phase 18]: Direct import of validate_no_leakage (not try/except) since pandas is already a profiler dependency
- [Phase 19]: Refactored _compute_baselines into domain-dispatch with helper methods per domain
- [Phase 19]: DL label extraction scans directory structure (class folders) for image classification datasets
- [Phase 19]: FT baselines are purely theoretical using log(vocab_size), no model loading required
- [Phase 20]: Domain-keyed nested dict with get_families_for_domain helper for algorithm family dispatch

### Pending Todos

None yet.

### Blockers/Concerns

- Package name "mlforge" PyPI availability needs confirmation before pyproject.toml is written (Phase 1)

## Session Continuity

Last session: 2026-03-21T03:11:35.473Z
Stopped at: Completed 20-01-PLAN.md
Resume file: None
