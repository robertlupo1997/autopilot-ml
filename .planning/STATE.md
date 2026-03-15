---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Results-Driven Forecasting
status: planning
stopped_at: Completed 14-01-PLAN.md (E2E forecasting validation)
last_updated: "2026-03-15T01:05:52.547Z"
last_activity: 2026-03-14 — v2.0 roadmap created
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 6
  completed_plans: 6
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Give Claude Code a dataset and a metric, and it autonomously discovers the best-performing traditional ML pipeline — running experiments, keeping improvements, reverting failures, and logging everything — without human intervention.
**Current focus:** Phase 13 — Scaffold and CLI Updates (--date-column flag, scaffold forecasting mode)

## Current Position

Phase: 11 of 14 (Forecasting Infrastructure)
Plan: 0 of 2 in current phase
Status: Ready to plan
Last activity: 2026-03-14 — v2.0 roadmap created

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed (v2.0): 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

*Updated after each plan completion*
| Phase 11 P01 | 193s | 1 tasks | 4 files |
| Phase 11 P02 | 240 | 1 tasks | 3 files |
| Phase 12 P02 | 480 | 1 tasks | 2 files |
| Phase 12 P01 | 720 | 1 tasks | 3 files |
| Phase 13 P01 | 204 | 2 tasks | 5 files |
| Phase 14-e2e-validation P01 | 20 | 3 tasks | 4 files |

## Accumulated Context

### Decisions

Recent decisions affecting current work:

- [Roadmap]: forecast.py must be built before train_template_forecast.py — callable model_fn interface must be locked in Phase 11 before Phase 12 can write a correct template
- [Roadmap]: Feature engineering stays in train.py (no separate features.py) — single-mutable-file constraint preserved from v1.0
- [Roadmap]: Optuna objective must call frozen walk_forward_evaluate() — agent cannot write its own CV loop
- [Roadmap]: feature-engine vs. manual shift() decision deferred to Phase 12 template authoring
- [Roadmap]: statsmodels necessity (ETS baseline) to be resolved during Phase 11 implementation
- [Phase 11]: guard hook updated in plan 11-01 to protect forecast.py immediately after creation (not deferred to Phase 12)
- [Phase 11]: seasonal naive uses index arithmetic on full y array (no statsmodels required)
- [Phase 11]: model_fn dollar-scale contract: walk_forward_evaluate does NOT inverse-transform; model_fn must return predictions in same unit as y_true
- [Phase 11]: date_col defaults to None to preserve exact backwards compatibility with PIPE-01 through PIPE-07 callers
- [Phase 11]: temporal_split uses math.floor for deterministic split boundary (40 rows * 0.85 = 34 train, 6 holdout)
- [Phase 12]: settings.json deny list extended to include Edit(forecast.py)/Write(forecast.py) for defense-in-depth alongside guard-frozen.sh hook
- [Phase 12]: forecast.py copied byte-identical via inspect.getfile(_forecast_module) matching the established prepare.py pattern
- [Phase 12]: optuna>=4.0 added to experiment pyproject.toml so Optuna is available in all experiment virtualenvs
- [Phase 12]: engineer_features called inside model_fn (not pre-computed) — each CV fold gets fresh features from its own training data only
- [Phase 12]: Dual-baseline gate enforced in CLAUDE.md as agent protocol rule only — loop_helpers.should_keep() unchanged (assumes higher=better)
- [Phase 12]: Template uses local imports (from forecast import ...) not automl package — matches standalone experiment directory layout
- [Phase 12]: MAPE direction explicit in CLAUDE.md: keep if new_mape < best_mape, not should_keep() which assumes higher=better
- [Phase 13]: scaffold_experiment import moved to cli.py module level for testability (patch support)
- [Phase 13]: _render_forecast_program_md() built separately from render_program_md() to avoid 'higher is always better' text in forecasting program.md
- [Phase 14-e2e-validation]: Best kept MAPE sourced from results.tsv not last json_output — last json_output may reflect a reverted experiment
- [Phase 14-e2e-validation]: stop_reason=tool_use is a known limitation (same as Phase 7) — all deliverables written before max-turns wall hit, no impact on validation

### Pending Todos

None.

### Blockers/Concerns

None at roadmap stage. Key risks documented in research:
- [Phase 11]: Temporal leakage in lag/rolling features is the dominant risk — walk_forward_evaluate() must call engineer_features() inside each fold
- [Phase 12]: Optuna trial budget split between draft phase and iteration phase — clarified in claude_forecast.md.tmpl Rule 7: min(50, 2*n_rows) cap

## Session Continuity

Last session: 2026-03-15T01:03:07.782Z
Stopped at: Completed 14-01-PLAN.md (E2E forecasting validation)
Resume file: None
