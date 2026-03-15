# AutoML — Autonomous ML Research Framework

## What This Is

An autonomous ML research framework for traditional (tabular) machine learning, inspired by Karpathy's autoresearch but adapted for scikit-learn, XGBoost, LightGBM, and similar libraries. Claude Code acts as the agentic orchestrator — iterating on ML pipelines autonomously while the user sleeps, using git for state management and a `program.md` for injecting domain expertise. The framework accepts any CSV dataset with a goal and metric, then runs hundreds of experiments autonomously.

## Core Value

Give Claude Code a dataset and a metric, and it autonomously discovers the best-performing traditional ML pipeline — running experiments, keeping improvements, reverting failures, and logging everything — without human intervention.

## Current State (v3.0 shipped 2026-03-15)

**Source:** 2,803 LOC Python across 16 modules | **Tests:** 5,210 LOC, 392 tests | **Commits:** ~200
**CLI:** `uv run automl data.csv target metric` → scaffolded project → `claude -p` autonomous loop
**Forecasting:** `--date-column date` enables walk-forward CV, Optuna search, shift-first features, dual-baseline gate
**Swarm:** `--agents N` spawns parallel agents in git worktrees with scoreboard coordination
**Resume:** `--resume` + checkpoint.json for session recovery
**v3.0 Intelligence:** `diagnose()` error analysis, `experiments.md` journal with knowledge accumulation, diff-aware iteration, hypothesis-driven commits, branch-on-stagnation exploration
**E2E validated:** MAPE 0.028172 on quarterly data, agent actively reads/writes journal between iterations

## Requirements

### Validated

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
- ✓ Walk-forward temporal validation (no future data leakage) — v2.0
- ✓ Forecasting metrics (MAPE, MAE, RMSE on dollar values) — v2.0
- ✓ Agent engineers time-series features (lags, rolling stats, growth rates) — v2.0
- ✓ Optuna hyperparameter search in train.py — v2.0
- ✓ Mutable zone 2 (feature engineering + modeling) — v2.0
- ✓ CLI `--date-column` flag for forecasting scaffold — v2.0
- ✓ Dual-baseline gate (beat naive + seasonal naive) — v2.0
- ✓ E2E validation: agent beats seasonal naive on synthetic data — v2.0
- ✓ Experiment journal for structured knowledge accumulation across iterations — v3.0
- ✓ Error diagnosis telling the agent WHERE the model fails — v3.0
- ✓ Branch-on-stagnation search strategy (AIDE-inspired backtracking) — v3.0
- ✓ Diff-aware iteration protocol (agent reviews own recent changes) — v3.0
- ✓ Hypothesis-first iteration protocol in CLAUDE.md — v3.0

### Active

(No active requirements — next milestone not yet defined)

### Out of Scope

- Full pipeline modification (mutable zone 3) — deferred to v4.0, prove smart iteration first
- MLE-bench integration — future milestone (requires Docker harness)
- Deep learning / neural network support — traditional ML only
- Multi-GPU or distributed training — single machine only
- Multi-company / cross-company models — single-company forecasting focus
- Real-time data ingestion — batch CSV input only
- Full MCTS tree search (SELA/AIDE) — branch-on-stagnation captures 80% of value
- LLM-as-judge for solution novelty — real metrics are authoritative
- Multi-agent research/dev split (R&D-Agent) — single agent + protocol is simpler

## Next Milestone: TBD

Run `/gsd:new-milestone` to define the next milestone.

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

- **v1 (shipped):** Agent modifies modeling only (algorithm, hyperparameters, ensembles)
- **v2 (shipped):** Agent can also modify feature engineering + Optuna hyperparameter search
- **v3 (shipped):** Agent has intelligent iteration — journal, diagnosis, diff-aware protocol, exploration branching
- **v4:** Agent owns the full pipeline (preprocessing, feature engineering, modeling)

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

| Separate forecast program.md renderer | Avoids "higher is always better" text from v1.0 template | ✓ Good — `_render_forecast_program_md()` generates minimize-aware content |
| Optuna for hyperparameter search | Agent writes search space, optimizer explores efficiently | ✓ Good — trial budget capped at min(50, 2*n_rows) |
| Branch-on-stagnation over full MCTS | 80% of AIDE's value at 10% complexity | ✓ Good — simple threshold + branch, no tree data structure |
| experiments.md journal over multi-agent decomposition | Single agent + journal simpler than research/dev agent split | ✓ Good — agent actively used journal in E2E validation |
| diagnose() as novel differentiator | Neither AIDE nor R&D-Agent does structured error diagnosis | ✓ Good — worst periods, bias, seasonal patterns exposed |
| Protocol rules in CLAUDE.md over code enforcement | Proven pattern from v2.0 dual-baseline gate | ✓ Good — all v3.0 rules are template text, not hardcoded |
| Second walk_forward_evaluate pass for diagnose() | Keeps Optuna objective clean, collects predictions separately | ✓ Good — no side effects in training loop |

---
*Last updated: 2026-03-15 after v3.0 milestone completion*
