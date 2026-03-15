# Milestones

## v2.0 Results-Driven Forecasting (Shipped: 2026-03-15)

**Phases completed:** 4 phases, 6 plans, 9 tasks | 2,562 LOC source, 4,417 LOC tests (330 tests)
**Timeline:** 2 days (2026-03-14 → 2026-03-15) | 50 commits
**Requirements:** 22/22 satisfied | Nyquist: 4/4 compliant

**Key accomplishments:**
- Frozen `forecast.py` with walk-forward CV, MAPE/MAE/RMSE metrics, and naive/seasonal-naive baselines
- Leakage-free `train_template_forecast.py` with shift-first feature engineering and Optuna hyperparameter search
- 10-rule agent protocol (`claude_forecast.md.tmpl`) enforcing feature cap, trial budget, dual-baseline gate
- `--date-column` CLI flag wiring forecasting scaffold end-to-end with baselines pre-computed in `program.md`
- E2E validation: Ridge achieves MAPE 0.029 vs seasonal naive 0.061 (52% improvement), 7 experiments, $1.90 cost

---

## v1.0 AutoML MVP + Swarm (Shipped: 2026-03-14)

**Phases completed:** 10 phases, 22 plans | 1,977 LOC source, 3,496 LOC tests (250 tests)
**Timeline:** 6 days (2026-03-09 → 2026-03-14) | 124 commits
**Requirements:** 69/69 satisfied | Nyquist: 10/10 compliant

**Key accomplishments:**
- Frozen pipeline + mutable modeling architecture for autonomous ML experimentation
- Autonomous experiment loop with multi-draft start, stagnation detection, crash recovery
- CLI scaffolding: `uv run automl data.csv target metric` generates complete project
- PreToolUse hooks and permissions for mutable zone enforcement
- Checkpoint persistence and `--resume` flag for session recovery
- Multi-agent swarm: parallel claude -p agents in git worktrees with file-locked scoreboard
- Full E2E validation: 10 experiments, 0 permission denials, autonomous operation confirmed

---

