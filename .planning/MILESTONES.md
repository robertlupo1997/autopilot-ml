# Milestones

## v1.0 Multi-Domain Autonomous ML Framework (Shipped: 2026-03-21)

**Phases completed:** 24 phases, 34 plans | 583 tests
**Timeline:** 3 days (2026-03-19 -> 2026-03-21)
**Requirements:** 48/48 satisfied | Audit: passed

**Key accomplishments:**
- Ground-up rewrite from autopilot-ml into plugin-based multi-domain framework
- Three domains: tabular (sklearn/XGBoost/LightGBM/Optuna), deep learning (PyTorch/timm/transformers), fine-tuning (peft/trl/LoRA/QLoRA)
- Core engine with experiment loop, git state, checkpoint/resume, guardrails
- Intelligence layer: diagnostics, multi-draft, branch-on-stagnation, journal
- Swarm mode: parallel agents in git worktrees with file-locked scoreboard
- Full documentation: README, CONTRIBUTING, 7 guides
- CLI with simple mode (auto-detect) and expert mode (full control)

**Archives:** [ROADMAP](milestones/v1.0-ROADMAP.md) | [REQUIREMENTS](milestones/v1.0-REQUIREMENTS.md) | [AUDIT](milestones/v1.0-MILESTONE-AUDIT.md)

---

## Prior Work (autopilot-ml, archived)

### v3.0 Intelligent Iteration (Shipped: 2026-03-15)
4 phases, 6 plans | 392 tests. Diagnostics, journal, branch-on-stagnation. Tabular-only.

### v2.0 Results-Driven Forecasting (Shipped: 2026-03-15)
4 phases, 6 plans | 330 tests. Walk-forward CV, forecasting template, dual-baseline gate. Tabular-only.

### v1.0 AutoML MVP + Swarm (Shipped: 2026-03-14)
10 phases, 22 plans | 250 tests. Foundation, core loop, CLI, swarm. Tabular-only.
