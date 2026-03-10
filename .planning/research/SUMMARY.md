# Project Research Summary

**Project:** AutoML -- Autonomous ML Research Framework
**Domain:** Autonomous ML Experiment Framework (Tabular ML, Claude Code as Orchestrator)
**Researched:** 2026-03-09
**Confidence:** MEDIUM-HIGH

## Executive Summary

AutoML is an autonomous ML experiment framework that applies the autoresearch pattern (pioneered by Karpathy for LLM pretraining) to traditional tabular ML. The core idea: Claude Code acts as both orchestrator and researcher, iteratively modifying a single modeling file, running experiments, extracting metrics, and deciding to keep or revert changes -- all managed through git state. The research landscape (AIDE, autoresearch, SELA, AutoKaggle, AI Scientist) consistently validates this loop-based approach but diverges on search strategy. The recommended path is a hybrid: multi-draft start for algorithm diversity (from AIDE), followed by linear keep/revert iteration (from autoresearch), with Claude Code as the native orchestrator rather than building a separate Python orchestration layer.

The stack is deliberately minimal: Python 3.11+, scikit-learn, XGBoost, LightGBM, pandas, numpy, and uv for package management. There is no experiment tracking server, no web UI, no distributed execution. Git commits ARE the experiment log. A TSV file provides the summary view. Subprocess calls to the git CLI handle state management. This simplicity is not a compromise -- it is the architecture. Every framework studied confirms that adding infrastructure (MLflow, Celery, web dashboards) creates more problems than it solves at this stage.

The primary risks are well-understood: silent failures where the model produces garbage but the metric looks reasonable, context window flooding after many iterations, the agent getting stuck in local optima, and metric gaming through overfitting to the validation split. All of these have proven mitigations: sanity-check baselines, output redirection to run.log, stagnation detection, and cross-validation as the default metric. The frozen evaluation boundary (where the agent cannot modify the metric computation or data split) is the single most important architectural decision -- it prevents the agent from cheating, and every successful framework in the landscape enforces this.

## Key Findings

### Recommended Stack

The stack follows autoresearch's minimalism, adapted for tabular ML. No experiment tracking servers, no distributed frameworks, no web UI dependencies. Git and a TSV file handle all state management.

**Core technologies:**
- **Python 3.11+** with **uv** package manager: fast, handles venvs and lockfiles, matches autoresearch pattern
- **scikit-learn + XGBoost + LightGBM**: the three pillars of tabular ML. CatBoost as optional extra. Covers linear models, random forests, and gradient boosting
- **pandas + numpy**: standard data handling. pandas for CSV loading, numpy for array operations
- **subprocess + git CLI**: git operations via shell commands, NOT GitPython. Simple, debuggable, no memory leaks
- **results.tsv + csv stdlib**: append-only experiment log. No MLflow, no W&B, no external services
- **ruff + pytest**: development tooling for linting and framework tests

**Critical version note:** All library versions are MEDIUM confidence (based on training data cutoff). Version ranges in pyproject.toml use >= lower bounds so uv lock resolves the actual latest. Manual verification needed before finalizing.

### Expected Features

**Must have (table stakes):**
- Autonomous experiment loop (run, extract metric, keep/revert, repeat)
- Configurable evaluation metric (AUC, RMSE, F1, etc. with direction)
- Git-based state management (branch per run, commit on keep, reset on revert)
- Frozen evaluation pipeline (agent cannot modify metric computation or data split)
- Mutable modeling file (single file the agent iterates on)
- Output capture to run.log (prevents context flooding)
- Result logging via results.tsv (structured, append-only, human-readable)
- CLI interface (dataset path, goal, metric, config)
- Domain context injection via program.md
- Data preview/validation on startup

**Should have (differentiators):**
- Multi-draft start (3-5 diverse initial solutions, pick best, then iterate linearly)
- Crash recovery / resumability from last good git state
- Data analysis phase (automated EDA before experiments begin)
- Report generation (markdown summary of what was tried and what worked)
- Simplicity criterion (prefer simpler solutions, penalize unnecessary complexity)

**Defer (v2+):**
- Feature engineering as a mutable zone
- Tree search / branching (full AIDE-style exploration)
- Sub-agent spawning for parallel drafts
- Full pipeline modification (agent owns everything)
- Web UI / dashboard
- Extensible metric parser plugins

### Architecture Approach

Claude Code IS the orchestrator -- there is no separate Python orchestration layer. The framework is a set of files and conventions that Claude Code operates on: a frozen prepare.py (data loading, splitting, evaluation), a mutable train.py (model code the agent edits), program.md (human domain expertise), CLAUDE.md (loop instructions), and git for state management. The architecture uses staged mutable zones: v1 restricts the agent to model selection and hyperparameters only; v2 unlocks feature engineering; v3 unlocks the full pipeline. Each stage expands scope while keeping the evaluation boundary frozen.

**Major components:**
1. **prepare.py (frozen)** -- loads CSV, splits data, computes evaluation metric. Agent imports from it but cannot modify it.
2. **train.py (mutable)** -- the agent's workspace. Model selection, hyperparameters, ensembles. Single-file constraint caps complexity.
3. **program.md** -- human-written domain expertise and strategy hints. Agent reads at each iteration.
4. **CLAUDE.md** -- meta-orchestrator instructions telling Claude Code how to run the experiment loop.
5. **Git state layer** -- branch per run, atomic commits, reset on revert. Git IS the undo mechanism.
6. **results.tsv** -- append-only experiment log with rich schema (commit hash, metric, status, description, strategy category, duration).
7. **Template system** -- Jinja templates to scaffold new experiment projects from a CSV + config.

### Critical Pitfalls

1. **Silent failures (garbage predictions)** -- The model runs without errors but produces meaningless output (constant predictions, random guessing). Mitigate by computing sanity-check baselines before the loop starts and adding prediction distribution checks to the frozen evaluation module.

2. **Data leakage** -- The agent introduces leakage that inflates metrics, especially in v2+ when feature engineering is unlocked. Mitigate by providing pre-split arrays in v1, reserving a hidden holdout set the agent never sees, and using cross-validation as the default metric.

3. **Context window flooding** -- After 50+ experiments, accumulated context degrades agent reasoning. Mitigate by redirecting all output to run.log, keeping results.tsv compact, and implementing periodic context resets via fresh sub-agents.

4. **Agent stuck in local optima** -- The agent makes tiny hyperparameter adjustments indefinitely instead of exploring different strategies. Mitigate with stagnation detection (trigger after N consecutive reverts), exploration prompts, and multi-draft restarts.

5. **Metric gaming / overfitting** -- Hundreds of experiments on a fixed split will overfit by chance. Mitigate with cross-validation as the loop metric, a hidden holdout for validation, and a simplicity/complexity penalty.

6. **Git state corruption** -- Failed experiments or crashes leave the repo in an inconsistent state. Mitigate by wrapping all git operations in helper functions with safety checks, pre-experiment status verification, and branch-per-run isolation.

## Implications for Roadmap

Based on research, the build order follows the architecture's layer dependencies and the feature dependency graph. Six phases are suggested.

### Phase 1: Frozen Pipeline and Project Scaffolding
**Rationale:** Everything depends on the frozen evaluation boundary. It must exist before any experiment can run. This is also the lowest-risk phase -- pure Python with no agent involvement.
**Delivers:** prepare.py template (data loading, train/test split, CV evaluation, metric computation, sanity baselines, hidden holdout), train.py baseline template, pyproject.toml, .gitignore, project scaffolding CLI that takes a CSV and generates a ready-to-run project.
**Addresses:** Frozen evaluation pipeline, mutable modeling file, data preview/validation, configurable metric.
**Avoids:** Data leakage (structurally impossible in v1 via pre-split arrays), silent failures (sanity baselines computed at setup), metric gaming (CV as default).

### Phase 2: Git Operations and Experiment Logging
**Rationale:** The experiment loop needs git state management and result logging before it can run. These are infrastructure components that the loop depends on.
**Delivers:** git_ops helper module (commit, reset, branch, status check, recovery from dirty state), results.tsv schema and append logic, run.log capture setup.
**Addresses:** Git-based state management, result logging, output capture.
**Avoids:** Git state corruption (helper functions with safety checks), inadequate logging (rich schema from day one).

### Phase 3: Core Experiment Loop
**Rationale:** With the frozen pipeline and git infrastructure in place, the core loop can be built. This is the highest-complexity phase and the core value proposition.
**Delivers:** CLAUDE.md template with full loop instructions, program.md template, the keep/revert decision logic, metric extraction (regex parsing from run.log), timeout enforcement, stagnation detection, error handling and crash recovery within the loop.
**Addresses:** Autonomous experiment loop, domain context injection (program.md), crash recovery, simplicity criterion.
**Avoids:** Context flooding (run.log redirect + selective reading), agent stuck in loops (stagnation detection), over-complexity (code length limits, simplicity criterion in prompts), Claude Code orchestrator failures (pre-authorized operations, error handling).

### Phase 4: Multi-Draft Start
**Rationale:** Multi-draft requires a working experiment loop (Phase 3). It is the highest-value differentiator -- AIDE's research showed algorithm choice matters more than hyperparameter tuning.
**Delivers:** Draft generation logic (3-5 diverse train.py variants across algorithm families), draft evaluation and selection, draft-to-linear transition, runner-up draft preservation.
**Addresses:** Multi-draft start, sub-agent spawning (optional enhancement).
**Avoids:** Multi-draft selection bias (use CV for draft selection, ensure true algorithm diversity, keep runner-ups).

### Phase 5: CLI Interface and End-to-End Integration
**Rationale:** With all core components built, wrap them in a user-facing CLI and ensure the full pipeline works end-to-end. This is the integration and polish phase.
**Delivers:** CLI entry point (accept dataset, goal, metric, config), end-to-end test on a real dataset, data analysis phase (automated EDA), report generation (markdown summary of experiment history).
**Addresses:** CLI interface, data analysis phase, report generation.
**Avoids:** Fragmented components that work in isolation but fail when integrated.

### Phase 6: Expanded Mutable Zones (v2+)
**Rationale:** Only after v1 is proven stable should the agent's scope expand. Feature engineering introduces leakage risk that requires the loop to be battle-tested first.
**Delivers:** v2 templates (model + feature engineering), v2 contract (agent receives raw dataframes), leakage detection mechanisms, v3 templates (full pipeline), benchmark harness.
**Addresses:** Feature engineering zone, full pipeline modification, tree search / branching.
**Avoids:** Premature scope expansion before the core loop is reliable.

### Phase Ordering Rationale

- **Phases 1-2 before Phase 3:** The experiment loop cannot function without a frozen pipeline to evaluate against and git infrastructure to manage state. Building these first also establishes the safety guarantees (no leakage, no metric gaming) before any autonomous operation begins.
- **Phase 3 before Phase 4:** Multi-draft is an enhancement to the core loop. The loop must work in linear mode before adding draft-based initialization. This also allows testing the loop in the simplest configuration first.
- **Phase 5 after Phases 3-4:** CLI and integration are the packaging layer. Building them too early means reworking them as the core components evolve.
- **Phase 6 is explicitly deferred:** The research unanimously supports starting with the most constrained scope (model-only) and expanding later. AIDE, autoresearch, and SELA all validate that model selection alone delivers significant value.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Core Experiment Loop):** The CLAUDE.md prompt engineering is critical and non-obvious. The exact instructions that make Claude Code operate as a reliable autonomous loop need careful iteration. How to handle context resets, how to phrase the stagnation detection prompt, how to enforce atomic changes -- all need experimentation.
- **Phase 4 (Multi-Draft Start):** How to ensure true algorithm diversity in drafts, how many iterations to run before selecting, whether to use sub-agents or sequential generation -- these have design decisions that benefit from prototyping.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Frozen Pipeline):** Well-understood scikit-learn patterns. Train/test split, CV, metric computation are standard.
- **Phase 2 (Git Operations):** Subprocess + git CLI is straightforward. The helper functions are simple wrappers with error checking.
- **Phase 5 (CLI):** Standard Python CLI patterns with argparse or click. No novel decisions.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Core libraries (sklearn, XGBoost, LightGBM) are well-established. Exact version numbers need verification against current PyPI. The anti-recommendations (no MLflow, no GitPython) are HIGH confidence. |
| Features | HIGH | Feature landscape is well-mapped from 6+ reference frameworks. Table stakes vs. differentiators distinction is clear. MVP scope is well-defined. |
| Architecture | HIGH | Architecture directly follows proven autoresearch + AIDE patterns. The staged mutable zones design is novel but well-supported by evidence from all studied frameworks. |
| Pitfalls | HIGH | Pitfalls are grounded in published evaluations (AI Scientist failure rates, MLE-bench overfitting findings, ML-Agent repetition patterns). Mitigations are concrete and actionable. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Library version verification:** All version numbers are from training data (cutoff ~May 2025). Must run `pip index versions <package>` before writing the final pyproject.toml. Low risk -- version ranges accommodate minor version drift.
- **CLAUDE.md prompt engineering:** The exact instructions for the autonomous loop are critical but cannot be fully designed in research. They require iterative testing with Claude Code. Plan for significant iteration in Phase 3.
- **Context reset strategy:** How exactly to implement periodic context resets (fresh sub-agent every N experiments) within Claude Code is an open question. The concept is proven (autoresearch does it), but the Claude Code-specific mechanism needs prototyping.
- **Cross-validation performance:** CV as the default metric means each experiment runs 5x. For large datasets, this could make experiments too slow. May need a "fast mode" (single split) vs. "reliable mode" (CV) toggle.
- **Stagnation detection thresholds:** What constitutes "stagnation" (how many consecutive reverts, what improvement epsilon) needs empirical tuning during Phase 3.

## Sources

### Primary (HIGH confidence)
- Autoresearch source code (Karpathy) -- experiment loop, program.md, results.tsv, git state patterns
- Autonomous ML Agents Research Report (project file) -- comprehensive landscape analysis of 7 frameworks
- PROJECT.md -- project constraints, decisions, prior research synthesis

### Secondary (MEDIUM confidence)
- AIDE (Weco AI, arXiv:2502.13138) -- tree search, multi-draft, atomic improvements, journal architecture
- AI Scientist (Sakana AI, arXiv:2504.08066) -- 42% failure rate, inability to self-assess, complexity patterns
- MLE-bench (OpenAI, arXiv:2410.07095) -- validation overfitting, pipeline error patterns
- SELA (MetaGPT/Tsinghua, arXiv:2410.17238) -- stage-wise MCTS, pipeline decomposition
- ML-Agent (arXiv:2505.23723) -- narrow action repetition as core limitation
- AutoKaggle (arXiv:2410.20424) -- 85% valid submission rate, unit testing emphasis

### Tertiary (LOW confidence)
- Exact library version numbers (scikit-learn, XGBoost, LightGBM, pandas, numpy) -- need PyPI verification
- CatBoost version and compatibility -- lower priority, optional dependency

---
*Research completed: 2026-03-09*
*Ready for roadmap: yes*
