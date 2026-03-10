# Feature Research

**Domain:** Autonomous ML Experiment Frameworks (Traditional/Tabular ML)
**Researched:** 2026-03-09
**Confidence:** MEDIUM-HIGH (based on AIDE docs, autoresearch docs, AI Scientist, AutoKaggle, MLAgentBench; autoresearch source code not directly inspected)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Autonomous experiment loop** | Core value prop -- run without human intervention. Every framework (AIDE, autoresearch, AI Scientist) has this. | HIGH | Must handle: run code, capture output, extract metric, decide keep/revert, loop. The "NEVER STOP" pattern from autoresearch means indefinite iteration until interrupted. |
| **Configurable evaluation metric** | Users need to specify what "better" means (AUC, RMSE, F1, etc.). AIDE accepts natural-language metric specs. | MEDIUM | Support both maximize and minimize. Parse metric from stdout/stderr. Start with simple grep/regex extraction (not LLM-as-judge). |
| **Git-based state management** | Autoresearch proved this pattern: commit on keep, reset on discard. Provides audit trail, rollback, and clean diffs. | MEDIUM | Branch per run, atomic commits, `git reset --hard` on revert. Must handle dirty working tree edge cases. |
| **Experiment result logging** | Every framework tracks results. Autoresearch uses `results.tsv`. AIDE generates tree visualizations. MLAgentBench logs to `trace.json`. | LOW | `results.tsv` with columns: step, commit_hash, metric_value, status (keep/revert), description, timestamp. Append-only, human-readable. |
| **Frozen evaluation pipeline** | Prevents the agent from gaming the metric. Separates "what to measure" from "what to optimize." AIDE and autoresearch both constrain what the agent can modify. | MEDIUM | Frozen files: data loading, train/test split, evaluation function. Agent cannot touch these. Enforced by file structure, not permissions. |
| **Mutable modeling file** | The agent's sandbox. Autoresearch constrains to `train.py`. This framework constrains to `solution.py` (or similar). | LOW | Single file containing model selection, hyperparameters, ensemble logic. Agent reads/writes only this file. |
| **Output capture to log file** | Autoresearch redirects to `run.log` to avoid flooding agent context. Essential when experiments produce verbose output. | LOW | Redirect stdout/stderr to `run.log`. Agent reads log for metric extraction but doesn't get full output in context window. |
| **CLI interface** | Every framework has CLI entry point. AIDE: `aide data_dir=... goal=... eval=...`. Autoresearch: `run.py`. Users expect command-line invocation. | MEDIUM | Accept: dataset path, goal description, evaluation metric, optional config overrides. Use Python argparse or click. |
| **Data preview/validation** | Framework must understand what data it's working with before starting. AutoKaggle requires structured input files. | MEDIUM | On startup: load CSV, show shape/dtypes/nulls/sample rows, write preview to a context file the agent can reference. Validates data is usable before burning experiment cycles. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Multi-draft start** | AIDE's key insight: algorithm choice matters more than hyperparameter tuning. Generate 3-5 diverse initial solutions (XGBoost, LightGBM, RF, LogReg, etc.), evaluate all, then iterate on the best. AIDE showed tree search wins 4x more medals than linear agents. | MEDIUM | Generate N drafts in parallel (or sequentially via sub-agents), evaluate each, select best, then switch to linear keep/revert on winner. This is the simplified version of AIDE's full tree search. |
| **Domain context injection (program.md)** | Autoresearch's `program.md` lets humans inject expertise without touching code. "The data has seasonal patterns," "Feature X is a known proxy for Y." No other framework does this as cleanly. | LOW | Markdown file read by the agent at each iteration. Contains: data context, known patterns, feature hints, constraints ("don't use feature Z, it leaks"). Low implementation cost, high impact on result quality. |
| **Crash recovery / resumability** | Long-running autonomous loops will crash (API errors, OOM, power loss). Being able to resume from last good state is critical for overnight runs. | MEDIUM | On startup: check for existing branch, read `results.tsv` for last committed state, resume from there. Git makes this natural -- last commit IS the recovery point. Also need to handle: agent timeout, Python crash mid-experiment, API rate limits. |
| **Simplicity criterion** | Autoresearch's insight: improvements must justify complexity. Prevents the agent from building 50-model ensembles that gain 0.001 AUC. | LOW | Inject as instruction in agent prompt: "Prefer simpler solutions. An improvement of <threshold> is not worth added complexity." Not enforced programmatically in v1 -- prompt engineering. |
| **Report generation** | AI Scientist generates full papers. AIDE generates tree visualizations. A summary of what was tried, what worked, and the final best approach is valuable. | MEDIUM | At completion (or on interrupt): generate markdown report summarizing best metric, approach progression, key experiments. Not a paper -- a readable summary. |
| **Sub-agent spawning for drafts** | Claude Code can spawn sub-agents. Use this for parallel draft generation instead of sequential loops. | MEDIUM | Spawn 3-5 sub-agents, each writes a different `solution.py` draft, evaluate all, pick best. Leverages Claude Code's native capability. |
| **Extensible metric parsers** | Different metrics need different extraction patterns. Users may have custom evaluation scripts. | LOW | Plugin-style metric extraction: regex patterns for common metrics (accuracy, AUC, RMSE, F1, MSE), with user-definable custom patterns. |
| **Data analysis phase** | Before experimenting, analyze the dataset: distributions, correlations, class balance, outliers. Feed findings into agent context. | MEDIUM | Run automated EDA on startup, write findings to a file the agent references. Helps the agent make better initial algorithm choices. Autoresearch doesn't do this; it's a differentiator for tabular ML. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Full tree search (MCTS/UCB)** | AIDE and SELA use tree search with branching. More exploration = better results in theory. | Massive complexity increase for v1. AIDE's tree search requires maintaining multiple branches, backtracking, and UCB scoring. SELA uses MCTS which needs hundreds of rollouts. Premature optimization. | Multi-draft start + linear iteration captures 80% of the value (algorithm diversity) at 20% of the complexity. Add tree search in v2 if linear plateau is observed. |
| **Multi-agent collaboration** | AutoKaggle uses 5 specialized agents (Reader, Planner, Developer, Reviewer, Summarizer). Seems like better division of labor. | Agent coordination overhead, complex state passing, debugging nightmares. AutoKaggle's 5-agent system is optimized for competition submissions, not iterative improvement loops. | Single agent with clear instructions. Claude Code is capable enough as a single agent with good prompting. Sub-agents only for parallel draft generation. |
| **LLM-as-judge for metric extraction** | More robust than regex. Can handle any output format. | Adds LLM call per experiment (cost, latency). Creates dependency on LLM availability for evaluation. Metric extraction should be deterministic, not probabilistic. | Simple regex/grep parsing with structured output format. The evaluation script should print metrics in a parseable format (e.g., `METRIC: 0.85`). |
| **Feature engineering by agent** | Agent could create better features, improving results. AutoKaggle has ML tools library for this. | Massively expands search space. Feature engineering changes can break the frozen data pipeline. Hard to revert cleanly. | Defer to v2 as "mutable zone 2." v1 agent only touches modeling (algorithm, hyperparameters, ensembles). |
| **Web UI / dashboard** | AIDE has a web UI. Visual monitoring seems user-friendly. | Significant frontend engineering. Users running ML experiments are comfortable with CLI. Adds deployment complexity. Distracts from core loop quality. | CLI with clear output + `results.tsv` that can be opened in any spreadsheet/plotting tool. Add optional web UI in v2+ if demand exists. |
| **GPU/distributed training support** | Some users want to train on GPU clusters. | Traditional ML (sklearn, XGBoost, LightGBM) runs fast on CPU. GPU support adds CUDA dependency management, device placement logic. Single-machine constraint keeps things simple. | CPU-first. XGBoost/LightGBM have optional GPU support that "just works" if CUDA is available -- don't build infrastructure around it. |
| **Auto-install dependencies** | Agent might need libraries not in the environment. | Security risk (arbitrary pip installs). Environment reproducibility breaks. Dependency conflicts mid-run. | Pre-install a curated set (sklearn, xgboost, lightgbm, pandas, numpy). Agent works within this sandbox. Document required packages clearly. |
| **Real-time streaming of experiment output** | Users want to watch experiments run live. | Floods terminal, provides false sense of control. The whole point is autonomous operation. Output is captured in `run.log`. | Periodic status updates (every N experiments): "Step 42: best metric = 0.89 (XGBoost, step 15)". Tail `run.log` if you want details. |

## Feature Dependencies

```
[CLI Interface]
    +-- accepts --> [Dataset Path + Goal + Metric]
                       +-- triggers --> [Data Preview/Validation]
                                            +-- feeds --> [Data Analysis Phase]
                                            +-- feeds --> [Domain Context (program.md)]
                                                              |
[Frozen Evaluation Pipeline]                                  |
    +-- used by --> [Metric Extraction]                       |
                       +-- used by --> [Experiment Loop]  <---+
                                            |
                                            +-- uses --> [Mutable Modeling File]
                                            +-- uses --> [Git State Management]
                                            +-- uses --> [Output Capture (run.log)]
                                            +-- writes --> [Result Logging (results.tsv)]
                                            |
                                            +-- enhanced by --> [Multi-Draft Start]
                                            |                       +-- optionally uses --> [Sub-Agent Spawning]
                                            |
                                            +-- enhanced by --> [Crash Recovery]
                                            +-- enhanced by --> [Simplicity Criterion]
                                            |
                                            +-- on completion --> [Report Generation]
```

### Dependency Notes

- **Experiment Loop requires Frozen Pipeline + Metric Extraction:** Cannot iterate without knowing what to measure and how to measure it.
- **Multi-Draft Start requires Experiment Loop:** Drafts are evaluated using the same loop mechanics. Must build the core loop first.
- **Crash Recovery requires Git State Management:** Recovery works by reading git history and `results.tsv` to find last good state.
- **Data Analysis enhances Multi-Draft Start:** EDA findings help the agent choose better initial algorithms for drafts.
- **Report Generation requires Result Logging:** Summarizes what's in `results.tsv` plus git diffs.
- **Sub-Agent Spawning enhances Multi-Draft Start:** Optional parallelism for draft generation. Not required -- drafts can be generated sequentially.
- **Domain Context (program.md) enhances Experiment Loop:** Agent reads `program.md` at each iteration for human-injected guidance.

## MVP Definition

### Launch With (v1)

Minimum viable product -- what's needed to validate the concept.

- [ ] **Frozen evaluation pipeline** -- data loading, train/test split, evaluation function that agent cannot modify
- [ ] **Mutable modeling file** -- single file where agent iterates on algorithm/hyperparameters/ensembles
- [ ] **Core experiment loop** -- run code, capture output, extract metric, decide keep/revert, repeat
- [ ] **Git state management** -- branch per run, commit on keep, reset on discard
- [ ] **Result logging (results.tsv)** -- append-only experiment tracking
- [ ] **Output capture (run.log)** -- redirect experiment output to file
- [ ] **Configurable metric** -- user specifies metric name and direction (maximize/minimize)
- [ ] **CLI interface** -- accept dataset path, goal, metric from command line
- [ ] **Domain context (program.md)** -- human expertise injection file
- [ ] **Data preview on startup** -- show dataset shape, types, sample rows before starting

### Add After Validation (v1.x)

Features to add once core loop is working and validated.

- [ ] **Multi-draft start** -- generate 3-5 diverse initial solutions, pick best, then iterate linearly (add once core loop proves stable)
- [ ] **Crash recovery** -- resume from last good git state on restart (add once people run overnight)
- [ ] **Data analysis phase** -- automated EDA before experimentation begins (add once basic loop works)
- [ ] **Report generation** -- markdown summary of experiment progression and best result (add once there are results worth summarizing)
- [ ] **Simplicity criterion enforcement** -- prompt-level instruction to prefer simpler solutions

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Feature engineering zone (mutable zone 2)** -- expand agent scope to preprocessing/features
- [ ] **Tree search / branching** -- explore multiple improvement paths, not just linear
- [ ] **Sub-agent spawning for drafts** -- parallel draft generation via Claude Code sub-agents
- [ ] **Full pipeline modification (mutable zone 3)** -- agent owns everything
- [ ] **Extensible metric parser plugins** -- user-defined metric extraction patterns
- [ ] **Web UI / dashboard** -- visual experiment monitoring
- [ ] **MLE-bench integration** -- standardized benchmark evaluation

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Frozen evaluation pipeline | HIGH | MEDIUM | P1 |
| Mutable modeling file | HIGH | LOW | P1 |
| Core experiment loop | HIGH | HIGH | P1 |
| Git state management | HIGH | MEDIUM | P1 |
| Result logging (results.tsv) | HIGH | LOW | P1 |
| Output capture (run.log) | MEDIUM | LOW | P1 |
| Configurable metric | HIGH | MEDIUM | P1 |
| CLI interface | HIGH | MEDIUM | P1 |
| Domain context (program.md) | MEDIUM | LOW | P1 |
| Data preview on startup | MEDIUM | LOW | P1 |
| Multi-draft start | HIGH | MEDIUM | P2 |
| Crash recovery | HIGH | MEDIUM | P2 |
| Data analysis phase | MEDIUM | MEDIUM | P2 |
| Report generation | MEDIUM | MEDIUM | P2 |
| Simplicity criterion | MEDIUM | LOW | P2 |
| Feature engineering zone | HIGH | HIGH | P3 |
| Tree search / branching | MEDIUM | HIGH | P3 |
| Sub-agent spawning | MEDIUM | MEDIUM | P3 |
| Full pipeline modification | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Autoresearch | AIDE | SELA | AutoKaggle | AI Scientist | Our Approach |
|---------|-------------|------|------|------------|--------------|--------------|
| Experiment loop | Linear keep/revert, 5-min fixed time | Tree search, configurable steps (default 20) | MCTS-guided | Multi-agent phases | Hypothesis-driven | Linear keep/revert with multi-draft start |
| Search strategy | Linear only | Full tree search (4x vs linear) | MCTS + UCB | Sequential pipeline | Iterative refinement | Multi-draft + linear (hybrid) |
| Metric handling | Single metric (val_bpb) | Natural-language metric spec | Configurable | Competition-defined | Domain-specific templates | Configurable metric name + direction |
| State management | Git (commits/resets) | Workspace directories | Not documented | Output directory hierarchy | LaTeX templates | Git (autoresearch pattern) |
| Domain injection | program.md | Goal description only | Not documented | overview.txt | prompt.json + seed_ideas.json | program.md (autoresearch pattern) |
| Result tracking | results.tsv | Tree visualization (HTML) | Not documented | Structured output dirs | LaTeX paper | results.tsv + markdown report |
| Crash recovery | Not documented | Docker workspaces | Not documented | Not documented | Retry logic | Git-based resume from last commit |
| Multi-draft | No (linear only) | Yes (5 drafts default) | Yes (MCTS nodes) | No | No | Yes (3-5 drafts, best then linear) |
| Report generation | No | Tree plot HTML | No | Workflow documentation | Full academic paper | Markdown summary |
| Data analysis | No | Not documented | Not documented | Yes (Reader agent) | No | Automated EDA on startup |
| Target domain | LLM pretraining | General ML/Kaggle | General ML | Kaggle competitions | Scientific research | Traditional tabular ML |
| Orchestrator | Claude Code | Custom Python + LLM API | MetaGPT framework | Custom multi-agent | Custom Python + LLM API | Claude Code |

## Sources

- AIDE (WecoAI/aideml) GitHub repository -- features, tree search, CLI, multi-draft mechanics
- Autoresearch (karpathy/autoresearch) GitHub repository -- experiment loop, program.md, results.tsv patterns
- SELA (MetaGPT examples) GitHub -- MCTS approach, pipeline concept
- AutoKaggle GitHub repository -- multi-agent architecture, unit testing, data analysis
- AI Scientist (SakanaAI) GitHub repository -- report generation, template extensibility
- MLAgentBench (snap-stanford) GitHub repository -- logging, sandboxing, CLI patterns
- PROJECT.md -- architecture decisions, staged mutable zones, prior research synthesis

---
*Feature research for: Autonomous ML Experiment Frameworks*
*Researched: 2026-03-09*
