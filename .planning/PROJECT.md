# AutoML — Autonomous ML Research Framework

## What This Is

An autonomous ML research framework for traditional (tabular) machine learning, inspired by Karpathy's autoresearch but adapted for scikit-learn, XGBoost, LightGBM, and similar libraries. Claude Code acts as the agentic orchestrator — iterating on ML pipelines autonomously while the user sleeps, using git for state management and a `program.md` for injecting domain expertise. The framework accepts any CSV dataset with a goal and metric, then runs hundreds of experiments autonomously.

## Core Value

Give Claude Code a dataset and a metric, and it autonomously discovers the best-performing traditional ML pipeline — running experiments, keeping improvements, reverting failures, and logging everything — without human intervention.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Generic framework accepting any CSV + goal description + evaluation metric
- [ ] Frozen data pipeline (data loading, train/test split, evaluation function) that the agent cannot modify
- [ ] Mutable modeling file where the agent iterates on algorithm selection, hyperparameters, and ensemble strategies
- [ ] Multi-draft start: generate 3-5 diverse initial solutions (different algorithms), pick the best, then iterate
- [ ] Linear keep/revert improvement loop on the winning draft (autoresearch pattern)
- [ ] Git-based state management (branch per run, commit on keep, reset on discard)
- [ ] `results.tsv` experiment tracking (commit hash, metric, status, description)
- [ ] `program.md` for human domain expertise injection (data context, known patterns, feature hints)
- [ ] Output redirected to `run.log` to avoid flooding agent context
- [ ] Simplicity criterion: improvements must justify their complexity cost
- [ ] Autonomous "NEVER STOP" operation — agent runs indefinitely until manually interrupted

### Out of Scope

- Feature engineering by the agent — deferred to v2 (mutable zone 2)
- Full pipeline modification — deferred to v3 (mutable zone 3)
- MLE-bench integration — future milestone (requires Docker harness)
- Tree search / branching — v2 enhancement (v1 uses multi-draft + linear)
- LLM-as-judge for metric extraction — v1 uses simple grep/parsing
- Multi-GPU or distributed training — single machine only
- Deep learning / neural network support — traditional ML only

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
| Claude Code as orchestrator (not AIDE/custom) | Leverages existing agentic infrastructure, sub-agents, CLAUDE.md, skills | — Pending |
| Multi-draft + linear (not pure linear or tree search) | Best tradeoff of simplicity vs. search effectiveness for v1 | — Pending |
| Staged mutable zones (not all-at-once) | Incrementally expand agent scope, prove loop before adding complexity | — Pending |
| Git for state management (not custom DB) | Proven by autoresearch, atomic commits, clean rollback, audit trail | — Pending |
| CPU-first (not GPU-required) | Traditional ML runs fast on CPU, lowers barrier to entry | — Pending |
| uv as package manager | Consistent with autoresearch ecosystem, fast, reliable | — Pending |

---
*Last updated: 2026-03-09 after initialization*
