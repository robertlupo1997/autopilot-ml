# Milestones

## mlforge v1.0 — Multi-Domain Autonomous ML Framework (Shipped: 2026-03-21)

**Phases completed:** 24 phases, 34 plans | 583 tests
**Timeline:** 3 days (2026-03-19 -> 2026-03-21)
**Requirements:** 48/48 satisfied | Audit: passed

**Key accomplishments:**
- Ground-up rewrite from autopilot-ml into plugin-based multi-domain framework
- Three domains: tabular (sklearn/XGBoost/LightGBM/Optuna), deep learning (PyTorch/timm/transformers), fine-tuning (peft/trl/LoRA/QLoRA)
- Core engine with experiment loop, git state management, checkpoint/resume, guardrails
- Intelligence layer: diagnostics, multi-draft start, branch-on-stagnation, experiment journal
- Swarm mode: parallel agents in git worktrees with file-locked scoreboard
- Protocol-first design: CLAUDE.md Jinja2 templates control all agent behavior
- Full documentation: README, CONTRIBUTING, 7 domain/config guides
- CLI: `mlforge <dataset> <goal>` with simple mode (auto-detect) and expert mode (full control)
- Legacy src/automl/ code removed, repo renamed to mlforge on GitHub

---

## Prior Work (autopilot-ml, archived in .planning/milestones/)

### v3.0 Intelligent Iteration (Shipped: 2026-03-15)

**Phases:** 4 | **Plans:** 6 | 392 tests
Diagnostics, experiment journal, branch-on-stagnation, protocol-first design.
Tabular-only, in the old src/automl/ codebase (now deleted).

### v2.0 Results-Driven Forecasting (Shipped: 2026-03-15)

**Phases:** 4 | **Plans:** 6 | 330 tests
Walk-forward CV, shift-first features, forecasting template, dual-baseline gate.
Tabular-only, in the old src/automl/ codebase (now deleted).

### v1.0 AutoML MVP + Swarm (Shipped: 2026-03-14)

**Phases:** 10 | **Plans:** 22 | 250 tests
Foundation, core loop, CLI, multi-agent swarm. Tabular-only.
The original autopilot-ml codebase (now deleted).
