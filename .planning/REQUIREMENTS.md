# Requirements: mlforge

**Defined:** 2026-03-19
**Core Value:** Leave an ML research agent running overnight with full confidence it will follow protocol, respect resource boundaries, track state, and produce meaningful results — without human intervention.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Core Engine

- [x] **CORE-01**: User can install mlforge via pip and run `mlforge <dataset> <goal>` to start an autonomous experiment session
- [x] **CORE-02**: Agent executes keep/revert experiment loop — modifies code, evaluates, commits on improvement, resets on failure
- [x] **CORE-03**: Protocol prompt system injects domain-specific CLAUDE.md templates into agent context at session start
- [x] **CORE-04**: State tracking persists experiment progress (current best, budget remaining, experiment count) across context resets
- [x] **CORE-05**: Checkpoint/resume allows crashed sessions to restart from last successful experiment
- [x] **CORE-06**: Config system (mlforge.config.toml) controls domain, budget, mutable zones, metric, and plugin settings
- [x] **CORE-07**: Hook engine (PreToolUse/PostToolUse) intercepts Claude Code tool calls to enforce frozen file zones
- [x] **CORE-08**: Experiment journal accumulates structured knowledge (hypothesis, result, diff, metric delta) that survives context resets
- [x] **CORE-09**: Deviation handling auto-recovers from crashes (retry), OOM (reduce batch), and divergence (revert)
- [x] **CORE-10**: Git-based state management: branch per run, commit per kept experiment, reset on revert, tag best model

### Experiment Intelligence

- [x] **INTL-01**: Baseline establishment runs naive + domain-specific baselines before agent starts experimenting
- [x] **INTL-02**: Dual-baseline gate requires agent to beat both naive and domain-specific baselines before keeping an experiment
- [x] **INTL-03**: Diagnostics engine analyzes WHERE the model fails (worst predictions, bias direction, feature correlations)
- [x] **INTL-04**: Branch-on-stagnation triggers after 3 consecutive reverts — branches from best-ever commit, tries different approach
- [x] **INTL-05**: Multi-draft start generates 3-5 diverse initial solutions (different model families), picks best, iterates linearly
- [x] **INTL-06**: Diff-aware experimentation shows agent what changed between experiments via git diff in journal
- [x] **INTL-07**: Experiment time/cost budget with per-experiment timeout and total session budget (wall clock, API cost, GPU hours)
- [x] **INTL-08**: Results tracking in structured experiment log with commit hash, metric value, status, description, timestamp

### Tabular ML Plugin

- [x] **TABL-01**: Tabular ML plugin handles classification and regression tasks on CSV/Parquet tabular data
- [x] **TABL-02**: Plugin supports scikit-learn, XGBoost, LightGBM model families with Optuna hyperparameter search
- [x] **TABL-03**: Leakage prevention enforces shift-first temporal features and walk-forward CV for time-series data
- [x] **TABL-04**: Plugin generates domain-specific CLAUDE.md protocol with tabular ML rules and anti-patterns
- [x] **TABL-05**: Frozen prepare.py handles data loading and train/test split; mutable train.py handles modeling

### Deep Learning Plugin

- [x] **DL-01**: Deep learning plugin handles image classification, text classification, and custom architecture training with PyTorch
- [x] **DL-02**: Plugin manages GPU utilization, memory limits, and training time budgets
- [x] **DL-03**: Plugin supports learning rate scheduling, early stopping, and gradient clipping as protocol rules
- [x] **DL-04**: Plugin generates domain-specific CLAUDE.md protocol with deep learning rules and anti-patterns
- [x] **DL-05**: Fixed time budget per training run prevents runaway GPU consumption

### LLM Fine-tuning Plugin

- [x] **FT-01**: Fine-tuning plugin handles LoRA/QLoRA fine-tuning of open models (Llama, Mistral, etc.) via PEFT/TRL
- [x] **FT-02**: Plugin manages VRAM allocation, quantization config, and LoRA rank/alpha selection
- [x] **FT-03**: Plugin supports evaluation metrics for generative tasks (perplexity, ROUGE, task-specific eval)
- [x] **FT-04**: Plugin generates domain-specific CLAUDE.md protocol with fine-tuning rules and anti-patterns
- [x] **FT-05**: Plugin handles dataset formatting (chat templates, instruction format) and train/eval splits

### Guardrails & Reliability

- [x] **GUARD-01**: Frozen file zone enforcement prevents agent from modifying infrastructure files (prepare.py, evaluate.py)
- [x] **GUARD-02**: Resource guardrails enforce cost caps, GPU hour limits, and disk usage boundaries
- [x] **GUARD-03**: Crash recovery automatically saves state before each experiment so sessions can resume
- [x] **GUARD-04**: Live progress monitoring shows current experiment, best metric so far, and budget remaining in terminal
- [x] **GUARD-05**: Cost tracking records API token usage per experiment with running total and budget cap enforcement
- [x] **GUARD-06**: Run summary generated at session end: key findings, best approach, failed hypotheses, next directions

### Multi-Agent

- [x] **SWARM-01**: Swarm mode spawns parallel agents in git worktrees exploring different model families simultaneously
- [x] **SWARM-02**: File-locked scoreboard coordinates best result across parallel agents
- [x] **SWARM-03**: Budget inheritance prevents spawn explosion — child agents inherit parent's remaining budget
- [x] **SWARM-04**: Verification agent checks metric improvement claims against actual holdout performance

### User Experience

- [x] **UX-01**: Simple mode auto-detects task type, selects metrics, and generates protocol from minimal user input
- [x] **UX-02**: Expert mode allows custom CLAUDE.md, custom frozen/mutable zones, custom baseline functions, and plugin API access
- [x] **UX-03**: Best model artifact exported with metadata (metric, config, training history) after session completes
- [x] **UX-04**: Dataset profiling analyzes schema, feature types, target distribution, and temporal patterns before experiments start
- [x] **UX-05**: Run retrospective summarizes what approaches worked, what failed, cost analysis, and recommendations for next run

## v2 Requirements

Deferred to future release.

### Advanced Features

- **ADV-01**: AIDE-style tree search as alternative exploration strategy
- **ADV-02**: Model acceptance testing — user reviews top-3 models interactively
- **ADV-03**: Global defaults (~/.mlforge/defaults.json) for cross-project settings
- **ADV-04**: Run archival with experiment journal, best model, config, and summary

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web UI or dashboard | CLI-first; terminal output and log files are sufficient |
| Cloud orchestration (AWS/GCP) | Local-first, single machine; users wrap mlforge in their own infra |
| Kaggle competition integration | Research tool, not competition platform; AutoKaggle exists for that |
| AutoML grid search (AutoGluon pattern) | mlforge does intelligent hypothesis-driven experimentation, not exhaustive search |
| Paper writing (AI Scientist style) | Generates experiment reports, not LaTeX manuscripts |
| Real-time data ingestion | Batch input only (CSV, Parquet, HuggingFace datasets) |
| Training LLMs from scratch | Fine-tuning existing models only |
| Reinforcement learning for agent improvement | Use strong foundation models with good protocols instead |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 3 | Complete |
| CORE-02 | Phase 11 | Complete |
| CORE-03 | Phase 11 | Complete |
| CORE-04 | Phase 1 | Complete |
| CORE-05 | Phase 1 | Complete |
| CORE-06 | Phase 1 | Complete |
| CORE-07 | Phase 1 | Complete |
| CORE-08 | Phase 21 | Complete |
| CORE-09 | Phase 11 | Complete |
| CORE-10 | Phase 13 | Complete |
| INTL-01 | Phase 21 | Complete |
| INTL-02 | Phase 19 | Complete |
| INTL-03 | Phase 16 | Complete |
| INTL-04 | Phase 21 | Complete |
| INTL-05 | Phase 21 | Complete |
| INTL-06 | Phase 7 | Complete |
| INTL-07 | Phase 6 | Complete |
| INTL-08 | Phase 2 | Complete |
| TABL-01 | Phase 2 | Complete |
| TABL-02 | Phase 2 | Complete |
| TABL-03 | Phase 9 | Complete |
| TABL-04 | Phase 2 | Complete |
| TABL-05 | Phase 2 | Complete |
| DL-01 | Phase 21 | Complete |
| DL-02 | Phase 8 | Complete |
| DL-03 | Phase 12 | Complete |
| DL-04 | Phase 21 | Complete |
| DL-05 | Phase 8 | Complete |
| FT-01 | Phase 8 | Complete |
| FT-02 | Phase 8 | Complete |
| FT-03 | Phase 21 | Complete |
| FT-04 | Phase 15 | Complete |
| FT-05 | Phase 8 | Complete |
| GUARD-01 | Phase 3 | Complete |
| GUARD-02 | Phase 21 | Complete |
| GUARD-03 | Phase 6 | Complete |
| GUARD-04 | Phase 3 | Complete |
| GUARD-05 | Phase 21 | Complete |
| GUARD-06 | Phase 4 | Complete |
| SWARM-01 | Phase 14 | Complete |
| SWARM-02 | Phase 22 | Pending |
| SWARM-03 | Phase 22 | Pending |
| SWARM-04 | Phase 14 | Complete |
| UX-01 | Phase 15 | Complete |
| UX-02 | Phase 4 | Complete |
| UX-03 | Phase 16 | Complete |
| UX-04 | Phase 13 | Complete |
| UX-05 | Phase 4 | Complete |

**Coverage:**
- v1 requirements: 48 total
- Satisfied: 37
- Pending (gap closure): 11
- Mapped to phases: 48
- Unmapped: 0

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-21 after gap closure planning*
