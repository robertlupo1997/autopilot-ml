# AutoML — Autonomous ML Research Framework

## What This Is

An autonomous ML research framework for traditional (tabular) machine learning, inspired by Karpathy's autoresearch but adapted for scikit-learn, XGBoost, LightGBM, and similar libraries. Claude Code acts as the agentic orchestrator — iterating on ML pipelines autonomously while the user sleeps, using git for state management and a `program.md` for injecting domain expertise. The framework accepts any CSV dataset with a goal and metric, then runs hundreds of experiments autonomously.

## Core Value

Give Claude Code a dataset and a metric, and it autonomously discovers the best-performing traditional ML pipeline — running experiments, keeping improvements, reverting failures, and logging everything — without human intervention.

## Current State (v1.0 shipped 2026-03-14)

**Source:** 1,977 LOC Python across 14 modules | **Tests:** 3,496 LOC, 250 tests | **Commits:** 124
**CLI:** `uv run automl data.csv target metric` → scaffolded project → `claude -p` autonomous loop
**Swarm:** `--agents N` spawns parallel agents in git worktrees with scoreboard coordination
**Resume:** `--resume` + checkpoint.json for session recovery

## Requirements

### Validated (v1.0)

- ✓ Generic framework accepting any CSV + goal description + evaluation metric — v1.0
- ✓ Frozen data pipeline (data loading, train/test split, evaluation function) — v1.0
- ✓ Mutable modeling file (algorithm selection, hyperparameters, ensembles) — v1.0
- ✓ Multi-draft start: 3-5 diverse initial solutions, pick best, iterate — v1.0
- ✓ Linear keep/revert improvement loop (autoresearch pattern) — v1.0
- ✓ Git-based state management (branch per run, commit/reset) — v1.0
- ✓ results.tsv experiment tracking — v1.0
- ✓ program.md for domain expertise injection — v1.0
- ✓ Output redirected to run.log — v1.0
- ✓ Autonomous "NEVER STOP" operation — v1.0
- ✓ PreToolUse hooks for frozen file enforcement — v1.0
- ✓ Checkpoint persistence and session resume — v1.0
- ✓ Multi-agent swarm with scoreboard coordination — v1.0

### Active

- ✓ Walk-forward temporal validation replaces random CV splits — no future data leakage — Phase 11
- ✓ Forecasting-appropriate metrics (MAPE, MAE, RMSE on dollar values) replace classification accuracy — Phase 11
- ✓ Agent engineers time-series features (lags, rolling stats, growth rates, seasonality) from raw historicals — Phase 12
- ✓ Optuna replaces manual hyperparameter guessing inside train.py — agent writes search space, optimizer runs trials — Phase 12
- ✓ Agent can modify both feature engineering and modeling (mutable zone 2) — Phase 12
- [ ] System produces better forecasts than a basic regression script on real financial data

## Current Milestone: v2.0 Results-Driven Forecasting

**Goal:** Refactor the autonomous loop so the agent engineers features, uses efficient hyperparameter search (optuna), respects time ordering, and produces forecasts that beat traditional approaches on real corporate financial data.

**Target use case:** Single-company quarterly revenue forecasting from historical financials.

### Out of Scope

- Full pipeline modification (mutable zone 3) — v3
- MLE-bench integration — future milestone (requires Docker harness)
- Deep learning / neural network support — traditional ML only
- Multi-GPU or distributed training — single machine only
- Multi-company / cross-company models — v2 focuses on single-company forecasting
- Real-time data ingestion — batch CSV input only

## Context

### Research Landscape (March 2026)

This project synthesizes patterns from 6 major autonomous ML frameworks:

| Project | Key Pattern Adopted | Key Pattern Deferred |
|---------|-------------------|---------------------|
| **Autoresearch** (Karpathy) | Single-file constraint, git state, program.md, "NEVER STOP", results.tsv, run.log redirect | LLM training specifics |
| **AIDE** (Weco AI) | Multi-draft start (5 diverse solutions), atomic improvements, separation of concerns | Full tree search, LLM-as-judge, two-model architecture |
| **SELA** (MetaGPT/Tsinghua) | Stage-wise pipeline concept (for v2+) | MCTS, UCB exploration |
| **AutoKaggle** (Alibaba) | Unit testing concept (for v2+) | Multi-agent collaboration |
| **ML-Agent** (Shanghai) | Insight that domain-specific beats scale | RL training approach |
| **AI Scientist** (Sakana) | — | Full research lifecycle (too ambitious for v1) |

### Architecture Decision: Staged Mutable Zones

The framework uses a "staged zones" approach to incrementally expand the agent's scope:

- **v1 (this milestone):** Agent modifies modeling only (algorithm, hyperparameters, ensembles)
- **v2:** Agent can also modify feature engineering and preprocessing
- **v3:** Agent owns the full pipeline

This mirrors autoresearch's key insight: constrain the agent to a small, comprehensible scope where changes are attributable and reversible.

### Architecture Decision: Multi-Draft + Linear

Instead of pure linear iteration (autoresearch) or full tree search (AIDE), v1 uses a hybrid:
1. Generate 3-5 diverse drafts (XGBoost, LightGBM, RandomForest, LogisticRegression, etc.)
2. Evaluate all drafts
3. Linear keep/revert iteration on the best performer

This captures AIDE's most impactful insight (algorithm choice matters) with minimal added complexity.

### Key Differences from Autoresearch

| Dimension | Autoresearch | AutoML Framework |
|-----------|-------------|-----------------|
| Target domain | LLM pretraining | Traditional tabular ML |
| Time per experiment | 5 minutes (GPU training) | ~30 seconds (sklearn/XGBoost) |
| Experiments overnight | ~100 | ~1,000+ |
| Metric | val_bpb (bits per byte) | Configurable (AUC, RMSE, F1, etc.) |
| Search strategy | Linear keep/revert | Multi-draft + linear |
| Dependencies | PyTorch, CUDA, H100 | scikit-learn, XGBoost, LightGBM |
| Hardware required | NVIDIA GPU | CPU only (GPU optional for XGBoost) |

### Prior Research Document

Full landscape analysis available at: `Autonomous_ML_Agents_Research_Report.docx`

## Constraints

- **Orchestrator**: Claude Code (agent framework, sub-agent spawning, git integration)
- **Languages**: Python 3.11+
- **ML Libraries**: scikit-learn, XGBoost, LightGBM, pandas, numpy
- **State Management**: Git (branches, commits, resets)
- **Hardware**: Single machine, CPU-first (GPU optional)
- **Package Manager**: uv (following autoresearch pattern)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Claude Code as orchestrator (not AIDE/custom) | Leverages existing agentic infrastructure, sub-agents, CLAUDE.md, skills | ✓ Good — agent drives entire loop autonomously |
| Multi-draft + linear (not pure linear or tree search) | Best tradeoff of simplicity vs. search effectiveness for v1 | ✓ Good — diverse starting points, then focused iteration |
| Staged mutable zones (not all-at-once) | Incrementally expand agent scope, prove loop before adding complexity | ✓ Good — v1 modeling-only proven, ready for v2 expansion |
| Git for state management (not custom DB) | Proven by autoresearch, atomic commits, clean rollback, audit trail | ✓ Good — worktrees enable swarm isolation too |
| CPU-first (not GPU-required) | Traditional ML runs fast on CPU, lowers barrier to entry | ✓ Good — experiments complete in ~30s |
| uv as package manager | Consistent with autoresearch ecosystem, fast, reliable | ✓ Good |
| Agent-driven architecture | Library modules provide utilities; agent follows CLAUDE.md protocol | ✓ Good — simpler than wiring complex import chains |
| Broad Edit(*)/Write(*) + deny list | Narrow path patterns silently ignored in headless mode | ✓ Good — defense-in-depth with hook system |
| File-locked scoreboard + TTL claims | Cross-agent coordination via filesystem, no external deps | ✓ Good — stdlib-only, no race conditions in tests |
| Shift-first rolling features | Prevents temporal leakage in lag/rolling features — `.shift(1)` before any `.rolling()` | ✓ Good — enforced in template and CLAUDE.md protocol |
| Dual-baseline gate | Agent must beat both naive and seasonal-naive to keep a result | ✓ Good — protocol rule in CLAUDE.md, not hardcoded in loop_helpers |
| Local imports in experiment templates | `from forecast import ...` not `from automl.forecast import ...` | ✓ Good — matches standalone experiment directory layout |

---
*Last updated: 2026-03-14 after Phase 12*
