# Roadmap: mlforge

## Overview

mlforge is a ground-up rebuild of autopilot-ml into a multi-domain autonomous ML research framework. The roadmap delivers a shared core engine with plugin architecture, validates it end-to-end with the proven tabular domain, then expands to deep learning and LLM fine-tuning. Five phases move from foundation through validated tabular pipeline to full three-domain support with swarm mode.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core Engine + Plugin Infrastructure** - State management, git ops, checkpoint/resume, config system, plugin protocol, and template rendering (completed 2026-03-19)
- [ ] **Phase 2: Tabular Plugin + Experiment Intelligence** - Tabular ML plugin validating the architecture, plus baselines, diagnostics, stagnation, and multi-draft
- [x] **Phase 3: Scaffold, CLI + Run Engine** - User entry point, experiment loop orchestration, guardrails, and overnight reliability (completed 2026-03-20)
- [x] **Phase 4: E2E Validation + UX** - End-to-end tabular validation on real data, user experience modes, artifact export, and run summaries (completed 2026-03-20)
- [x] **Phase 5: Domain Plugins + Swarm** - Deep learning plugin, LLM fine-tuning plugin, and multi-agent swarm mode (completed 2026-03-20)

## Phase Details

### Phase 1: Core Engine + Plugin Infrastructure
**Goal**: The foundational engine exists -- state tracking, git operations, checkpoint/resume, configuration, plugin protocol, and protocol template rendering are all operational
**Depends on**: Nothing (first phase)
**Requirements**: CORE-03, CORE-04, CORE-05, CORE-06, CORE-07, CORE-08, CORE-10
**Success Criteria** (what must be TRUE):
  1. State can be created, persisted to JSON, and restored across simulated context resets with experiment count, best metric, and budget remaining intact
  2. Git operations create a branch per run, commit on keep, reset on revert, and tag best model -- all programmatically via GitPython
  3. A crashed session can be resumed from the last checkpoint and continues from where it left off
  4. A domain plugin conforming to the typing.Protocol interface can register, scaffold files, and render its CLAUDE.md template via Jinja2
  5. Hook engine intercepts tool calls and blocks writes to files marked as frozen in config
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md -- Package skeleton + State + Config + Checkpoint (CORE-04, CORE-06, CORE-05)
- [x] 01-02-PLAN.md -- Git ops + Experiment journal (CORE-10, CORE-08)
- [x] 01-03-PLAN.md -- Plugin protocol + Templates + Hook engine (CORE-03, CORE-07)

### Phase 2: Tabular Plugin + Experiment Intelligence
**Goal**: The tabular ML plugin proves the plugin architecture works, and the experiment intelligence features (baselines, diagnostics, stagnation, multi-draft, diff-aware iteration) are operational
**Depends on**: Phase 1
**Requirements**: TABL-01, TABL-02, TABL-03, TABL-04, TABL-05, INTL-01, INTL-02, INTL-03, INTL-04, INTL-05, INTL-06, INTL-08
**Success Criteria** (what must be TRUE):
  1. Tabular plugin handles CSV/Parquet input for classification and regression, generating frozen prepare.py and mutable train.py with scikit-learn/XGBoost/LightGBM support
  2. Baseline establishment runs naive and domain-specific baselines, and the dual-baseline gate rejects experiments that do not beat both
  3. Diagnostics engine reports worst predictions, bias direction, and feature correlations -- telling the agent WHERE the model fails
  4. After 3 consecutive reverts, branch-on-stagnation triggers and creates a new branch from the best-ever commit
  5. Multi-draft start generates 3-5 diverse initial solutions across model families and picks the best before iterating linearly
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md -- TabularPlugin + prepare.py + baselines + train.py template (TABL-01, TABL-02, TABL-03, TABL-04, TABL-05, INTL-01, INTL-02)
- [ ] 02-02-PLAN.md -- Diagnostics engine + multi-draft + branch-on-stagnation (INTL-03, INTL-04, INTL-05)
- [ ] 02-03-PLAN.md -- Diff-aware journal + structured results tracking (INTL-06, INTL-08)

### Phase 3: Scaffold, CLI + Run Engine
**Goal**: Users can install mlforge, run it from the command line, and it orchestrates the full experiment loop with guardrails for unattended overnight execution
**Depends on**: Phase 2
**Requirements**: CORE-01, CORE-02, CORE-09, GUARD-01, GUARD-02, GUARD-03, GUARD-04, GUARD-05, INTL-07
**Success Criteria** (what must be TRUE):
  1. User can pip install mlforge and run `mlforge <dataset> <goal>` to start an autonomous experiment session
  2. The run engine executes fresh-context-per-iteration experiment loops -- spawning `claude -p` sessions that keep improvements and revert failures
  3. Deviation handling auto-recovers from crashes (retry), OOM (reduce batch), and divergence (revert) without human intervention
  4. Resource guardrails enforce cost caps, GPU hour limits, disk usage, and per-experiment timeouts with hard stops
  5. Live terminal output shows current experiment number, best metric, and remaining budget
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md -- CLI entry point + experiment scaffolding (CORE-01, GUARD-01)
- [x] 03-02-PLAN.md -- Guardrails + cost tracking + deviation handling + live progress (GUARD-02, GUARD-04, GUARD-05, INTL-07, CORE-09)
- [x] 03-03-PLAN.md -- Run engine + CLI wiring (CORE-02, GUARD-03)

### Phase 4: E2E Validation + UX
**Goal**: The full tabular pipeline is validated end-to-end on real data, and user experience features (simple/expert modes, artifact export, run summaries) are complete
**Depends on**: Phase 3
**Requirements**: UX-01, UX-02, UX-03, UX-04, UX-05, GUARD-06, TABL-03
**Success Criteria** (what must be TRUE):
  1. A complete mlforge run on a real tabular dataset scaffolds, iterates, checkpoints, resumes, and produces a best model that beats both baselines
  2. Simple mode auto-detects task type, selects metrics, and runs with minimal user input (just dataset + goal)
  3. Expert mode accepts custom CLAUDE.md, custom frozen/mutable zones, custom baselines, and plugin API access
  4. Best model artifact is exported with metadata (metric value, config, training history) after session completes
  5. Run retrospective summarizes approaches tried, what worked, what failed, cost breakdown, and recommendations
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md -- Dataset profiler + simple/expert mode CLI integration (UX-01, UX-02, UX-04, TABL-03)
- [x] 04-02-PLAN.md -- Artifact export + run retrospective + engine post-loop wiring (UX-03, UX-05, GUARD-06)

### Phase 5: Domain Plugins + Swarm
**Goal**: Deep learning and LLM fine-tuning plugins extend mlforge to all three domains, and swarm mode enables parallel agent exploration
**Depends on**: Phase 4
**Requirements**: DL-01, DL-02, DL-03, DL-04, DL-05, FT-01, FT-02, FT-03, FT-04, FT-05, SWARM-01, SWARM-02, SWARM-03, SWARM-04
**Success Criteria** (what must be TRUE):
  1. Deep learning plugin trains PyTorch models for image/text classification with GPU management, LR scheduling, early stopping, and fixed time budgets per run
  2. Fine-tuning plugin runs LoRA/QLoRA fine-tuning of open models with VRAM management, quantization config, and evaluation metrics (perplexity, ROUGE)
  3. Both new plugins generate domain-specific CLAUDE.md protocols and work through the same scaffold/run/iterate pipeline as tabular
  4. Swarm mode spawns parallel agents in git worktrees with file-locked scoreboard coordination and budget inheritance preventing spawn explosion
  5. Verification agent checks metric improvement claims against actual holdout performance
**Plans**: 3 plans

Plans:
- [ ] 05-01-PLAN.md -- Deep learning plugin: DeepLearningPlugin + frozen prepare.py + dl_train.py.j2 template (DL-01, DL-02, DL-03, DL-04, DL-05)
- [ ] 05-02-PLAN.md -- Fine-tuning plugin: FineTuningPlugin + frozen prepare.py + ft_train.py.j2 template (FT-01, FT-02, FT-03, FT-04, FT-05)
- [x] 05-03-PLAN.md -- Swarm mode: SwarmManager + file-locked scoreboard + budget inheritance + verification agent (SWARM-01, SWARM-02, SWARM-03, SWARM-04)

### Phase 6: Fix Engine Subprocess Flags
**Goal**: Fix invalid claude CLI flags in engine.py subprocess invocation so experiments can actually run
**Depends on**: Phase 3
**Requirements**: CORE-02, CORE-03, INTL-07, GUARD-03
**Gap Closure**: Closes P0 gaps from v1.0 audit — subprocess flags that prevent all experiments from running
**Success Criteria** (what must be TRUE):
  1. `--append-system-prompt-file` replaced with `--append-system-prompt` using inline string content
  2. `--max-turns` replaced with valid claude CLI flag or removed
  3. Simple mode and expert mode E2E flows reach experiment execution without subprocess crash
**Plans**: 1 plan

Plans:
- [x] 06-01-PLAN.md -- Fix invalid CLI flags in engine.py subprocess command (CORE-02, CORE-03, INTL-07, GUARD-03)

### Phase 7: Wire Intelligence Subsystem to Engine
**Goal**: Connect all intelligence modules (baselines, diagnostics, stagnation, multi-draft, journal) to the engine runtime loop
**Depends on**: Phase 6
**Requirements**: INTL-01, INTL-02, INTL-03, INTL-04, INTL-05, CORE-08, INTL-06
**Gap Closure**: Closes P2 gaps from v1.0 audit — intelligence modules that exist and pass tests but are never called
**Success Criteria** (what must be TRUE):
  1. `compute_baselines()` and `passes_baseline_gate()` called programmatically during engine loop (not just CLAUDE.md text rules)
  2. `diagnose_regression/classification()` called after experiments and output injected into agent context
  3. `check_stagnation()` and `trigger_stagnation_branch()` called when `consecutive_reverts` threshold reached
  4. `select_best_draft()` called during multi-draft start phase
  5. `append_journal_entry()` and `get_last_diff()` called after each experiment to persist knowledge
**Plans**: 2 plans

Plans:
- [x] 07-01-PLAN.md -- Baselines + journal + stagnation wiring into engine loop (INTL-01, INTL-02, CORE-08, INTL-06, INTL-04)
- [x] 07-02-PLAN.md -- Multi-draft phase + diagnostics engine wiring (INTL-05, INTL-03)

### Phase 8: Register Domain Plugins + Swarm CLI
**Goal**: Register DL/FT plugins in scaffold.py and add swarm CLI entry point so all Phase 5 features are reachable
**Depends on**: Phase 6
**Requirements**: DL-01, DL-02, DL-03, DL-04, DL-05, FT-01, FT-02, FT-03, FT-04, FT-05, SWARM-01, SWARM-02, SWARM-03, SWARM-04
**Gap Closure**: Closes P1 gaps from v1.0 audit — Phase 5 features that are implemented but unreachable
**Success Criteria** (what must be TRUE):
  1. `get_plugin('deeplearning')` returns `DeepLearningPlugin` without KeyError
  2. `get_plugin('finetuning')` returns `FineTuningPlugin` without KeyError
  3. CLI accepts `--swarm` / `--n-agents` flags and invokes `SwarmManager`
  4. `verify_best_result()` called within `SwarmManager.run()` after agents complete
**Plans**: 2 plans

Plans:
- [x] 08-01-PLAN.md -- Register DL/FT plugins in scaffold.py with domain-aware dispatch (DL-01, DL-02, DL-03, DL-04, DL-05, FT-01, FT-02, FT-03, FT-04, FT-05)
- [x] 08-02-PLAN.md -- Add swarm CLI flags and wire verify_best_result into SwarmManager.run() (SWARM-01, SWARM-02, SWARM-03, SWARM-04)

### Phase 9: Wire Simple Mode Task Propagation
**Goal**: Propagate auto-detected task type from dataset profiler through to plugin settings so simple mode works correctly
**Depends on**: Phase 6
**Requirements**: UX-01, TABL-03
**Gap Closure**: Closes P3 gaps from v1.0 audit — simple mode task type not propagated
**Success Criteria** (what must be TRUE):
  1. `profile_dataset()` result (task, csv_path, target_column) propagated to `plugin_settings`
  2. `TabularPlugin.scaffold()` renders `train.py` with correct task type (not hardcoded classification)
**Plans**: 1 plan

Plans:
- [x] 09-01-PLAN.md -- Wire CLI propagation + task-aware template rendering (UX-01, TABL-03)

### Phase 10: Fix Runtime Wiring Bugs
**Goal**: Fix three residual integration bugs found by v1.0 milestone audit — baseline gate dead code, unreachable multi-draft, invalid swarm CLI flag
**Depends on**: Phase 7, Phase 8
**Requirements**: INTL-01, INTL-02, INTL-05, SWARM-01
**Gap Closure**: Closes integration gaps from v1.0 audit
**Success Criteria** (what must be TRUE):
  1. `_compute_baselines()` calls `prepare.load_data()` + `prepare.split_data()` to get actual data, and `state.baselines` is populated for tabular runs
  2. `--enable-drafts` CLI flag exists and sets `config.enable_drafts = True`, making multi-draft reachable
  3. `--cwd` removed from swarm agent command list in `swarm/__init__.py`
**Plans**: 1 plan

Plans:
- [ ] 10-01-PLAN.md -- Fix baseline gate, add --enable-drafts CLI flag, remove invalid --cwd (INTL-01, INTL-02, INTL-05, SWARM-01)

### Phase 11: Fix Tabular Output + Stagnation Guard
**Goal**: Fix the P0/P1 wiring gaps that break the core tabular E2E flow — tabular train.py JSON output, CLAUDE.md output format rule, and stagnation crash guard
**Depends on**: Phase 10
**Requirements**: CORE-02, CORE-03, CORE-09, INTL-04
**Gap Closure**: Closes GAP-1 (tabular JSON output), GAP-2 (protocol output format), GAP-3 (stagnation crash) from v1.0 audit
**Success Criteria** (what must be TRUE):
  1. `tabular_train.py.j2` outputs `json.dumps({"metric_value": best_value})` instead of plain text `print(f"Best value: ...")`
  2. `base_claude.md.j2` contains an output format rule instructing the agent to emit `{"metric_value": X}` as the last line of output
  3. `trigger_stagnation_branch()` gracefully handles `best_commit=None` instead of raising ValueError
  4. Standard tabular E2E flow completes without metric_value=None or stagnation crash
**Plans**: 1 plan

Plans:
- [x] 11-01-PLAN.md -- Fix tabular JSON output, CLAUDE.md output format rule, and stagnation None guard (CORE-02, CORE-03, CORE-09, INTL-04)

### Phase 12: Wire Plugin Validation + Task Type Mapping
**Goal**: Call validate_config() before scaffolding and map profiler task types to DL/FT expected types so simple mode works for all domains
**Depends on**: Phase 11
**Requirements**: FT-04, DL-03, UX-01, TABL-01, DL-01, FT-01
**Gap Closure**: Closes GAP-4 (validate_config dead code), GAP-5 (DL/FT task type mismatch) from v1.0 audit
**Success Criteria** (what must be TRUE):
  1. `validate_config()` called from scaffold.py before `plugin.scaffold()` — invalid configs raise clear errors
  2. Profiler task types (`classification`/`regression`) mapped to DL types (`image_classification`/`text_classification`) before passing to DL plugin
  3. FineTuningPlugin rejects missing `model_name` with actionable error message
  4. DL/FT simple mode renders correct model architecture for detected task type
**Plans**: 1 plan

Plans:
- [ ] 12-01-PLAN.md -- Wire validate_config() gate + task type mapping in scaffold (FT-04, DL-03, UX-01, TABL-01, DL-01, FT-01)

### Phase 13: Wire Dead Code + Rich Profile Display
**Goal**: Connect orphaned functions (tag_best, publish_result) and surface rich dataset profile data in CLI output
**Depends on**: Phase 11
**Requirements**: CORE-10, SWARM-01, SWARM-02, UX-04
**Gap Closure**: Closes GAP-6 (tag_best dead code), GAP-7 (swarm scoreboard dead code), GAP-8 (profile data discarded) from v1.0 audit
**Success Criteria** (what must be TRUE):
  1. `tag_best()` called from engine at session end when a best experiment exists
  2. `publish_result()` called from swarm agent completion path (not just protocol text)
  3. CLI displays missing_pct, numeric_features, categorical_features, and leakage_warnings from DatasetProfile
  4. Git tag `best-{run_id}` exists on the best experiment commit after a successful session
**Plans**: 1 plan

Plans:
- [ ] 13-01-PLAN.md -- Wire tag_best + publish_result + rich profile display (CORE-10, SWARM-01, SWARM-02, UX-04)

### Phase 14: Fix Swarm Agent Subprocess
**Goal**: Fix swarm agent subprocess command to include required permission flags, budget enforcement, and CLAUDE.md in worktrees so swarm mode E2E flow works
**Depends on**: Phase 13
**Requirements**: SWARM-01, SWARM-02, SWARM-03, SWARM-04
**Gap Closure**: Closes INT-03 (swarm subprocess missing flags) and Swarm E2E flow from v1.0 re-audit
**Success Criteria** (what must be TRUE):
  1. `_build_agent_command()` includes `--dangerously-skip-permissions` flag so agents can write files
  2. `--max-budget-usd` passed to child agents with budget inheritance from parent
  3. CLAUDE.md protocol file copied into each worktree before agent spawn
  4. Agents write `state.json` so scoreboard reads actual results instead of empty files
**Plans**: 1 plan

Plans:
- [x] 14-01-PLAN.md -- Fix _build_agent_command flags + setup CLAUDE.md copy + state.json template (SWARM-01, SWARM-02, SWARM-03, SWARM-04)

### Phase 15: Fix FT Simple Mode Metric Mapping
**Goal**: Add finetuning domain to task type mapping and set valid default metric so `--domain finetuning` simple mode works without ValueError
**Depends on**: Phase 12
**Requirements**: FT-04, UX-01
**Gap Closure**: Closes INT-04 (FT metric mismatch) and FT simple mode flow from v1.0 re-audit
**Success Criteria** (what must be TRUE):
  1. `_TASK_TYPE_MAP` has entry for `finetuning` domain mapping to valid FT task type
  2. Profiler sets FT-valid metric (e.g., `loss` or `perplexity`) instead of `accuracy` for finetuning domain
  3. `--domain finetuning` simple mode reaches scaffold without ValueError from `validate_config()`
**Plans**: 1 plan

Plans:
- [ ] 15-01-PLAN.md -- Add FT domain to task type map + metric/direction override + default model_name (FT-04, UX-01)

### Phase 16: Wire Template Runtime Artifacts
**Goal**: Train templates write predictions.csv and best_model.joblib so diagnostics engine and artifact export actually fire at runtime
**Depends on**: Phase 14
**Requirements**: INTL-03, UX-03
**Gap Closure**: Closes INT-01 (predictions.csv never written) and INT-02 (model file never saved) from v1.0 re-audit
**Success Criteria** (what must be TRUE):
  1. `tabular_train.py.j2` writes `predictions.csv` with test set predictions after model training
  2. `tabular_train.py.j2` saves best model via `joblib.dump()` as `best_model.joblib`
  3. CLAUDE.md templates instruct agent to preserve predictions.csv and model artifact writes
  4. `_run_diagnostics()` finds predictions.csv and produces diagnostic output at runtime
  5. `export_artifact()` finds best_model.joblib and exports with metadata
**Plans**: 1 plan

Plans:
- [ ] 16-01-PLAN.md -- Add predictions.csv + best_model.joblib writes to tabular template + CLAUDE.md artifact rule (INTL-03, UX-03)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7/8/9 (parallel) → 10 → 11 → 12/13 (parallel)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Engine + Plugin Infrastructure | 3/3 | Complete   | 2026-03-19 |
| 2. Tabular Plugin + Experiment Intelligence | 3/3 | Complete   | 2026-03-19 |
| 3. Scaffold, CLI + Run Engine | 3/3 | Complete   | 2026-03-20 |
| 4. E2E Validation + UX | 2/2 | Complete   | 2026-03-20 |
| 5. Domain Plugins + Swarm | 3/3 | Complete   | 2026-03-20 |
| 6. Fix Engine Subprocess Flags | 1/1 | Complete   | 2026-03-20 |
| 7. Wire Intelligence Subsystem | 2/2 | Complete   | 2026-03-20 |
| 8. Register Domain Plugins + Swarm CLI | 2/2 | Complete   | 2026-03-20 |
| 9. Wire Simple Mode Task Propagation | 1/1 | Complete   | 2026-03-20 |
| 10. Fix Runtime Wiring Bugs | 1/1 | Complete    | 2026-03-20 |
| 11. Fix Tabular Output + Stagnation Guard | 1/1 | Complete    | 2026-03-20 |
| 12. Wire Plugin Validation + Task Mapping | 1/1 | Complete    | 2026-03-20 |
| 13. Wire Dead Code + Rich Profile Display | 1/1 | Complete    | 2026-03-20 |
| 14. Fix Swarm Agent Subprocess | 1/1 | Complete    | 2026-03-20 |
| 15. Fix FT Simple Mode Metric Mapping | 1/1 | Complete    | 2026-03-20 |
| 16. Wire Template Runtime Artifacts | 1/1 | Complete   | 2026-03-21 |
