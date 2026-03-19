# Feature Landscape

**Domain:** Autonomous ML research framework (AutoLab)
**Researched:** 2026-03-19
**Overall confidence:** HIGH

## Sources and Competitive Landscape

Research drew from direct source reading of:
- **GSD framework v1.22.4** — Full source catalog of 34 workflow files, 13 reference docs, 15+ templates, and CLI tooling
- **Karpathy's autoresearch** — program.md protocol, train.py constraint, results.tsv tracking
- **AIDE (Weco AI)** — Tree-search code optimization, MLE-Bench champion
- **SELA** — Monte Carlo Tree Search for AutoML pipelines
- **AutoKaggle** — Multi-agent framework for data science competitions
- **AI Scientist v2 (Sakana AI)** — Fully autonomous paper-writing research agent
- **ML-Agent** — RL-trained LLM agents for ML engineering
- **R&D-Agent (Microsoft)** — Two-phase research+development autonomous framework
- **OpenHands** — General-purpose coding agent platform
- **autopilot-ml v1-v3** — This project's predecessor (proven patterns)

## Table Stakes

Features users expect. Missing = the tool feels broken or incomplete compared to running autoresearch directly.

### Core Experiment Loop

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Keep/revert experiment cycle** | Autoresearch's core pattern — agent modifies code, evaluates, keeps or discards | Med | Git-based: commit on keep, reset on discard. Every competitor does this. |
| **Single metric optimization** | Every framework needs ONE number to optimize. Without it, the agent has no objective | Low | User specifies metric name + direction (minimize/maximize). Support custom eval functions. |
| **Results tracking** | Autoresearch has results.tsv. AIDE has solution tree HTML. Without history, overnight runs are useless | Low | Structured experiment journal with commit hash, metric, status, description, timestamp |
| **Experiment time budget** | Autoresearch uses fixed 5-min runs. Cost/time caps prevent runaway overnight jobs | Low | Per-experiment timeout + total session budget (wall clock, API cost, GPU hours) |
| **Git-based state management** | Autoresearch, autopilot-ml, and AIDE all use git for experiment state. Without git, no rollback | Med | Branch per run, commit per kept experiment, reset on discard |
| **Protocol prompt injection** | Autoresearch's program.md tells the agent HOW to experiment. Without it, the agent hallucinates approaches | Med | CLAUDE.md templates with domain-specific rules injected into agent context |
| **Baseline establishment** | Every framework runs a baseline first. Without it, no way to know if improvements are real | Low | Auto-run naive baseline before agent starts. Dual-baseline gate (naive + domain-specific) |
| **Crash recovery** | Overnight runs WILL crash. Without recovery, you wake up to nothing | High | Checkpoint/resume across context resets. STATE.md + experiment journal survive crashes |
| **Installable CLI** | Users expect `pip install autolab && autolab run dataset.csv --goal "predict churn"` | Med | Click-to-start for beginners. No manual CLAUDE.md authoring required for simple cases |

### Agent Behavior Control

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Frozen file zones** | Autoresearch only allows editing train.py. Without boundaries, agent breaks infrastructure | Med | Hook-based enforcement. Declare which files are mutable vs frozen per domain |
| **Mutable code scope** | Agent needs to know exactly what it can change | Low | Staged zones: v1=model only, v2=+features+hyperparams, v3=+architecture |
| **NEVER STOP loop** | Autoresearch's core directive: keep experimenting until manually stopped or budget exhausted | Low | Protocol rule in CLAUDE.md. No confirmation prompts. Fully autonomous |
| **Leakage prevention** | In tabular/forecasting ML, data leakage silently inflates metrics. Without prevention, results are fake | High | Shift-first temporal features, walk-forward CV, holdout set the agent cannot touch |
| **Resource guardrails** | Without limits, agent burns GPU hours or API credits | Med | Cost caps, GPU memory limits, disk usage boundaries, experiment count limits |

### Output and Reporting

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Structured experiment log** | Users need to see what happened overnight. autoresearch has results.tsv, AIDE has tree viz | Med | Experiment journal: each entry has hypothesis, result, diff, metric delta, commit |
| **Best model artifact** | User expects to find the best model ready to use after overnight run | Low | Auto-export best checkpoint/model file with metadata |
| **Run summary** | Human-readable summary of what the agent tried and learned | Med | Generated at session end: key findings, best approach, failed hypotheses, next directions |

---

## Differentiators

Features that set AutoLab apart from running autoresearch directly or using AIDE. Not expected, but create competitive advantage.

### GSD-Style Deterministic Control (from GSD source analysis)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Hook engine (PreToolUse/PostToolUse)** | autoresearch has NO enforcement — agent follows program.md by convention only. Hooks enforce boundaries programmatically: block writes to frozen files, reject dangerous operations, validate experiment format | High | GSD's core innovation. Intercepts Claude Code tool calls BEFORE execution. Essential for trust in overnight runs |
| **Multi-agent orchestration** | autoresearch is single-agent. GSD coordinates researcher, planner, executor, verifier agents. AutoLab can parallelize experiments across approaches | High | Swarm mode: parallel agents in git worktrees with file-locked scoreboard. Already proven in autopilot-ml v1.0 |
| **Phase lifecycle (plan/execute/verify)** | autoresearch has no structure — just "try stuff". GSD's phased approach means systematic exploration: first establish baselines, then feature engineering, then model selection, then hyperparameter tuning | Med | Import GSD's discuss -> plan -> execute -> verify cycle adapted for ML experiments |
| **Goal-backward verification** | GSD verifies that phase GOALS were achieved, not just tasks completed. Apply to ML: "Did we actually beat the baseline?" not "Did we run 50 experiments?" | Med | Verification agent checks metric improvement claims against actual holdout performance |
| **Checkpoint/resume across sessions** | GSD has full STATE.md + session continuity. autoresearch loses all context on restart. AIDE's tree can be resumed but has no state management protocol | High | STATE.md tracks: current best model, experiment count, budget remaining, last hypothesis, accumulated knowledge |
| **Experiment journal with knowledge accumulation** | autoresearch's results.tsv is append-only metrics. AutoLab's journal carries WHAT WAS LEARNED forward, so the agent doesn't repeat failed approaches after context reset | High | experiments.md with structured entries that survive /clear. Agent reads past failures before proposing new experiments |

### Three-Domain Support

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Tabular ML plugin** | autoresearch only does deep learning. Most real-world ML is tabular (scikit-learn, XGBoost, LightGBM). This is where AutoLab started (autopilot-ml v1-v3) | Med | Proven in autopilot-ml: Optuna search, prepare.py for leakage-free features, forecast.py for time series |
| **Deep learning plugin** | Match autoresearch's core domain. Custom CNN/transformer training with PyTorch | High | autoresearch-style single-file constraint. Fixed time budget per experiment. GPU utilization tracking |
| **LLM fine-tuning plugin** | Emerging demand. LoRA/QLoRA fine-tuning of open models (Llama, Mistral) | High | Unique differentiator — no other autonomous framework handles fine-tuning. Needs VRAM management and eval metrics |
| **Domain-specific protocol templates** | Each ML domain has different rules. Tabular needs leakage prevention. DL needs learning rate schedules. Fine-tuning needs LoRA rank selection | Med | CLAUDE.md templates per domain with domain-specific rules, anti-patterns, and evaluation criteria |

### Intelligent Iteration (proven in autopilot-ml v3.0)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Diagnostics engine** | autoresearch has no error analysis. AutoLab tells the agent WHERE the model fails (worst periods, bias direction, feature correlations) | Med | diagnose() function: worst prediction periods, systematic bias, correlation with features, seasonal patterns |
| **Branch-on-stagnation** | When the agent is stuck (3 consecutive reverts), branch from best-ever commit and try a different model family. No other framework does this | Med | Proven in autopilot-ml v3.0: 3-revert threshold triggers git checkout -b explore-{family} |
| **Multi-draft start** | Instead of one starting point, generate 3-5 diverse initial solutions, pick best, iterate linearly. Avoids local minima | Med | Proven pattern: diverse initial drafts (different model families, feature sets) then linear iteration from best |
| **Diff-aware experimentation** | Agent sees what changed between experiments, not just metrics. Enables causal reasoning about what works | Low | Git diff between experiments shown in journal. Agent reads diffs to understand why improvements happened |

### User Experience

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Simple mode for beginners** | `autolab data.csv --goal "predict price"` — zero config. autoresearch requires understanding program.md. AIDE needs goal/eval specification | Med | Auto-detect task type, auto-select metrics, auto-generate protocol. Expert mode available for full control |
| **Expert mode with full protocol control** | ML engineers want to specify exactly which approaches to try, which are forbidden, custom eval functions | Med | Custom CLAUDE.md, custom frozen/mutable zones, custom baseline functions, plugin API |
| **Live progress monitoring** | autoresearch: check results.tsv manually. AutoLab: real-time terminal output showing current experiment, best so far, budget remaining | Low | Structured terminal output during runs. No web UI needed — CLI-first |
| **Cost tracking** | API costs for LLM calls add up overnight. Users need to know what they spent | Low | Track API token usage per experiment. Show running total. Stop at budget cap |

---

## Anti-Features

Features to explicitly NOT build. These add complexity without proportional value, or conflict with AutoLab's design philosophy.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Web UI / dashboard** | Massive complexity for marginal value. CLI users don't need a React app to check experiment results. autoresearch has no UI and it's fine | CLI output + structured log files. `autolab status` shows current progress. `autolab results` shows experiment table |
| **Cloud orchestration (AWS/GCP job submission)** | Scope explosion. Managing cloud infrastructure is a different product | Local-first, single machine. Users who need cloud can wrap AutoLab in their own infra |
| **Kaggle integration** | AutoKaggle exists for this. Competition optimization is a different use case than research | Focus on research/production ML, not competition submission formatting |
| **AutoML-style model selection (AutoGluon pattern)** | Traditional AutoML just tries every algorithm with default params. AutoLab's value is intelligent, hypothesis-driven experimentation | Agent reasons about what to try next based on diagnostics and past results. NOT exhaustive grid search |
| **Built-in data preprocessing pipeline** | Users already have data loading code. Building pandas wrappers adds fragile surface area | Provide prepare.py template with clear interface. User brings their own data loading. Agent works on modeling |
| **Paper writing (AI Scientist style)** | AI Scientist v2 does this and most papers are mediocre. AutoLab optimizes models, not manuscripts | Generate experiment reports and summaries, not LaTeX papers |
| **Real-time data ingestion** | Streaming ML is a different problem domain. Batch is AutoLab's scope | Batch input: CSV, Parquet, HuggingFace datasets |
| **Visual experiment tree (AIDE style)** | AIDE's tree visualization is nice but not essential. Terminal output + structured logs are sufficient | Flat experiment journal with parent references. Optional tree export for analysis |
| **Reinforcement learning for agent improvement** | ML-Agent uses RL to train the agent itself. Interesting research but massive complexity | Use strong foundation models (Claude) with good protocol prompts. Let model improvements flow from Anthropic |

---

## GSD Features to Replicate

Specific capabilities from the actual GSD v1.22.4 source code that AutoLab needs to replicate or adapt. Cataloged from reading all 34 workflow files, 13 reference docs, and CLI tooling.

### Tier 1: Must Replicate (Core Engine)

| GSD Feature | What It Does | AutoLab Adaptation | Complexity |
|-------------|-------------|-------------------|------------|
| **Hook engine** | PreToolUse/PostToolUse hooks intercept Claude Code tool calls before execution | Enforce frozen file zones, validate experiment format, block dangerous operations (rm -rf, pip install) | High |
| **Protocol prompts (CLAUDE.md)** | Text rules injected into agent context controlling behavior | Domain-specific experiment protocols: tabular rules, DL rules, fine-tuning rules | Med |
| **State tracking (STATE.md)** | Persistent state file surviving context resets: position, decisions, blockers, session continuity | Experiment state: current best metric, budget remaining, experiment count, accumulated knowledge, last hypothesis | Med |
| **Checkpoint/resume** | .continue-here files, agent-history.json, interrupted agent detection | Resume from last successful experiment after crash. Rebuild state from git log + experiment journal | High |
| **Git integration** | Commit per task, branch per phase, reset on failure, tag on milestone | Commit per kept experiment, branch per run, reset on revert, tag best model | Med |
| **Config system** | .planning/config.json with mode, granularity, parallelization, model profile, workflow toggles | autolab.config.json with domain, budget, mutable zones, metric, model profile, plugin settings | Low |
| **CLI tooling (gsd-tools.cjs)** | Node.js CLI for state management, roadmap updates, commit helpers, progress tracking | Python CLI for experiment management, state updates, result tracking, budget monitoring | Med |

### Tier 2: Should Replicate (Quality of Life)

| GSD Feature | What It Does | AutoLab Adaptation | Complexity |
|-------------|-------------|-------------------|------------|
| **Deviation rules** | 4-tier system: Bug (auto-fix), Missing Critical (auto-fix), Blocking (auto-fix), Architectural (ask user) | Experiment deviation handling: crash (auto-retry), OOM (reduce batch size), divergence (revert), architecture change (if budget allows, try it) | Med |
| **Verification agent** | Post-execution verification: goal-backward analysis, artifact checking, wiring verification | Post-experiment verification: actual metric improvement on holdout, no data leakage detected, model artifact saved correctly | Med |
| **Multi-agent coordination** | Wave-based parallel execution, dependency tracking, scoreboard | Swarm mode: parallel agents exploring different model families simultaneously, file-locked scoreboard for best result | High |
| **Session continuity** | STATE.md records where session stopped, what to resume, accumulated context | Experiment session: last experiment number, current best, budget consumed, knowledge accumulated | Low |
| **Auto-advance pipeline** | discuss -> plan -> execute -> verify chains automatically | baseline -> explore -> iterate -> verify chains automatically per domain | Med |
| **Codebase mapping** | 7-document analysis of existing code (STACK, ARCHITECTURE, STRUCTURE, CONVENTIONS, TESTING, INTEGRATIONS, CONCERNS) | Dataset profiling: schema analysis, feature types, target distribution, temporal patterns, class balance | Med |

### Tier 3: Nice to Have (Polish)

| GSD Feature | What It Does | AutoLab Adaptation | Complexity |
|-------------|-------------|-------------------|------------|
| **UAT (User Acceptance Testing)** | Conversational testing with persistent state, one test at a time | Model acceptance testing: user reviews top-3 models, checks predictions on edge cases, confirms production readiness | Med |
| **Retrospective** | Living document of what worked/didn't across milestones | Run retrospective: what approaches worked, what failed, cost analysis, recommendations for next run | Low |
| **Debug diagnosis** | Parallel debug agents investigate root causes of failures | Experiment failure analysis: why did this model family fail? OOM? Divergence? Bad features? | Med |
| **Progress visualization** | Progress bar, phase completion tracking | Experiment progress: X/budget experiments complete, current best, improvement trajectory | Low |
| **Global defaults** | ~/.gsd/defaults.json for cross-project settings | ~/.autolab/defaults.json for preferred LLM, default budget, preferred model families | Low |
| **Milestone archival** | Archive completed milestones with stats, retrospective, git tag | Archive completed runs with experiment journal, best model, config, and summary | Low |

---

## Feature Dependencies

```
CLI Entry Point
  |
  v
Config System --> Protocol Templates (domain-specific CLAUDE.md)
  |
  v
Hook Engine --> Frozen File Enforcement
  |
  v
Baseline Establishment --> Dual-Baseline Gate
  |
  v
Keep/Revert Loop --> Git State Management --> Experiment Journal
  |                                              |
  v                                              v
Diagnostics Engine -----------------> Knowledge Accumulation
  |
  v
Branch-on-Stagnation (requires: experiment journal + git branching)
  |
  v
Multi-Draft Start (requires: keep/revert loop + baseline)
  |
  v
Checkpoint/Resume (requires: state tracking + experiment journal)
  |
  v
Swarm Mode (requires: git worktrees + scoreboard + all above)
```

### Critical Path
1. Config + CLI (everything depends on this)
2. Git state management + keep/revert loop (core experiment pattern)
3. Protocol templates + hook engine (behavior control)
4. Experiment journal + state tracking (crash recovery)
5. Baseline + diagnostics (intelligent iteration)
6. Domain plugins (tabular first, then DL, then fine-tuning)
7. Multi-draft + branch-on-stagnation (advanced iteration)
8. Swarm mode (parallel exploration)

---

## MVP Recommendation

Prioritize for first milestone:

1. **CLI entry point** with config system — `autolab run data.csv --goal "predict X"`
2. **Keep/revert experiment loop** with git state management — the core pattern
3. **Protocol prompt system** with tabular ML template — CLAUDE.md injection
4. **Hook engine** for frozen file enforcement — trust in overnight runs
5. **Experiment journal** with structured entries — crash recovery + knowledge accumulation
6. **Baseline establishment** with dual-baseline gate — agent must beat baselines
7. **Checkpoint/resume** — overnight runs MUST survive crashes

Defer to later milestones:
- **Deep learning plugin** — requires GPU management complexity
- **LLM fine-tuning plugin** — requires VRAM management, LoRA integration
- **Swarm mode** — requires all core features working first
- **Multi-draft start** — enhancement to core loop, not essential for v1
- **Branch-on-stagnation** — enhancement to core loop
- **UAT / verification agent** — polish feature

---

## Sources

### Primary (HIGH confidence)
- GSD v1.22.4 source: `~/.claude/get-shit-done/workflows/` (34 files read directly)
- GSD references: `~/.claude/get-shit-done/references/` (13 files read directly)
- autopilot-ml v1-v3 experience: `.planning/PROJECT.md`, project memory
- [Karpathy autoresearch program.md](https://github.com/karpathy/autoresearch/blob/master/program.md)
- [AIDE ML GitHub](https://github.com/WecoAI/aideml)

### Secondary (MEDIUM confidence)
- [AI Scientist v2 (Sakana AI)](https://github.com/SakanaAI/AI-Scientist-v2)
- [AutoKaggle](https://github.com/multimodal-art-projection/AutoKaggle)
- [ML-Agent](https://github.com/MASWorks/ML-Agent)
- [R&D-Agent (Microsoft)](https://github.com/microsoft/RD-Agent)
- [SELA paper](https://arxiv.org/abs/2410.17238)
- [OpenHands](https://github.com/OpenHands/OpenHands)

### Market Context (MEDIUM confidence)
- [Karpathy autoresearch overview (VentureBeat)](https://venturebeat.com/technology/andrej-karpathys-new-open-source-autoresearch-lets-you-run-hundreds-of-ai)
- [AIDE MLE-Bench results (MarkTechPost)](https://www.marktechpost.com/2025/02/23/this-ai-paper-from-weco-ai-introduces-aide-a-tree-search-based-ai-agent-for-automating-machine-learning-engineering/)
- [AI Scientist evaluation (arXiv)](https://arxiv.org/abs/2502.14297)
