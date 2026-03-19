# Project Research Summary

**Project:** AutoML v4.0 (package name TBD -- "AutoLab" is taken, see Naming section)
**Domain:** Autonomous ML research framework -- multi-domain plugin architecture with overnight unattended execution
**Researched:** 2026-03-19
**Confidence:** HIGH

## Executive Summary

This project is a ground-up rebuild of autopilot-ml (v1-v3) into a multi-domain autonomous ML research framework. The core idea -- an LLM agent that runs ML experiments overnight, keeping improvements and reverting failures -- is proven from v1-v3 and validated by Karpathy's autoresearch, AIDE, and others. The recommended approach is a shared core engine (session lifecycle, git state, checkpoint/resume, experiment journal) with a plugin protocol for three ML domains: tabular (proven from v1-v3), deep learning (autoresearch-style), and LLM fine-tuning (LoRA/QLoRA). The architecture borrows GSD's best patterns (fresh subagent contexts, init-pattern context loading, protocol-first behavior control, goal-backward verification) while rejecting its Node.js toolchain and fragile markdown-as-database state management in favor of Python + Pydantic + TOML + JSON.

The stack is high-confidence: Typer CLI, Pydantic config/validation, Jinja2 protocol templates, GitPython for state, scikit-learn/XGBoost/LightGBM for tabular, PyTorch Lightning for DL, HuggingFace transformers+PEFT for fine-tuning. The plugin interface should use Python's `typing.Protocol` (structural subtyping) rather than ABC, keeping the door open for third-party plugins without inheritance requirements. Build order is strictly dependency-driven: core engine first, then plugin protocol, then tabular plugin (the proven domain), then scaffold/run engines, then E2E validation, then additional domains, then swarm mode last.

The critical risks are all related to unattended overnight execution: context window exhaustion (solved by fresh-context-per-iteration), metric gaming / data leakage (solved by frozen evaluation modules + hooks), headless session hangs (solved by session timeouts + watchdog), and spawn budget explosion in swarm mode (solved by budget inheritance + no recursive spawning). Every one of these has a known mitigation, but they must be built into the core engine from day one -- they are not features to bolt on later.

## Naming Decision Required

**"AutoLab" is not viable.** CMU's Autolab (7k+ GitHub stars, CS education) and PyPI's `autolab` (scientific instruments, v2.0.3) own this name. The project needs a new name before `pyproject.toml` is written.

Candidates to check on PyPI: `mlforge`, `autoforge`, `mlpilot`, `labrat`, `autoresearch`. Action: run `pip index versions <name>` for each before the roadmap phase.

## Key Findings

### Recommended Stack

The stack is Python-ecosystem standard with no exotic dependencies. See [STACK.md](STACK.md) for full version matrix and rationale.

**Core technologies:**
- **Python >=3.11**: Performance gains + stdlib `tomllib` for config parsing
- **Typer + Rich**: CLI framework with beautiful terminal output, built on Click
- **Pydantic v2 + pydantic-settings**: Type-safe config, env var loading, TOML file support
- **Jinja2**: Protocol template rendering (CLAUDE.md per domain) -- proven in v1-v3
- **GitPython**: Programmatic git for keep/revert loop -- proven in v1-v3
- **importlib + typing.Protocol**: Plugin system for 3 known domains, no pluggy/stevedore overhead

**Domain libraries (installed via extras):**
- `[tabular]`: scikit-learn, XGBoost, LightGBM, Optuna, pandas
- `[deeplearning]`: PyTorch, Lightning, torchvision, Optuna
- `[finetuning]`: transformers, PEFT, TRL, bitsandbytes, accelerate

**Key decision: Structured state over markdown state.** GSD uses markdown with regex parsing for machine state (STATE.md). This is fragile. AutoML v4.0 uses JSON (`state.json`) for machine state and markdown (`experiments.md`) for human-readable journal. Both are authoritative for their domain.

### Expected Features

See [FEATURES.md](FEATURES.md) for full landscape with complexity ratings.

**Must have (table stakes):**
- Keep/revert experiment cycle with git state management
- Single metric optimization with baseline gate (dual-baseline from v2.0)
- Structured experiment journal surviving context resets
- Protocol prompt injection (CLAUDE.md per domain)
- Crash recovery / checkpoint resume
- Frozen file enforcement (evaluation module, data splits)
- Installable CLI: `autolab run data.csv --goal "predict X" --mode tabular`
- Time and cost budgets with hard stops

**Should have (differentiators over autoresearch):**
- Multi-draft start (3-5 diverse initial solutions)
- Branch-on-stagnation (3 consecutive reverts trigger new approach)
- Diagnostics engine (WHERE does the model fail, not just how badly)
- Diff-aware experimentation (git diff between experiments in journal)
- Three-domain support via plugin architecture
- Simple mode (zero-config) + expert mode (full protocol control)
- Live progress monitoring in terminal

**Defer to v2+:**
- Deep learning plugin (build after tabular proves the plugin interface)
- LLM fine-tuning plugin (requires GPU/VRAM management complexity)
- Swarm mode (requires all core features working first)
- Web UI / dashboard (anti-feature -- CLI-first)
- Cloud orchestration (anti-feature -- local-first)
- Kaggle integration (anti-feature -- different use case)
- Tree-search exploration (SELA/AIDE style -- interesting but massive complexity)

### Architecture Approach

The architecture is a shared core engine with a plugin protocol. The core handles session lifecycle, git state, checkpoint/resume, experiment journal, cost tracking, and protocol injection. Plugins handle domain-specific logic: data preparation, model creation, evaluation, diagnostics, and resource limits. See [ARCHITECTURE.md](ARCHITECTURE.md) for component diagram and data flow.

**Major components:**
1. **CLI** (Typer) -- parse user command, route to scaffold or run engine
2. **ScaffoldEngine** -- create experiment directory from dataset + config + plugin
3. **RunEngine** -- orchestrate the experiment loop (fresh-context-per-iteration)
4. **DomainPlugin** (Protocol) -- domain-specific logic behind a structural typing interface
5. **ProtocolGen** -- compose CLAUDE.md from base + domain + section templates via Jinja2
6. **StateManager** -- experiment state CRUD (`state.json`) + journal (`experiments.md`)
7. **GitOps** -- branch/commit/revert operations (proven from v1-v3)
8. **GuardrailEngine** -- frozen file enforcement, cost caps, leakage detection, metric validation

**Key patterns to follow:**
- **Protocol-first behavior control**: Rules in CLAUDE.md, code enforcement only for integrity
- **Plugin interface via typing.Protocol**: Structural subtyping, no inheritance
- **Init-pattern context loading**: One call gathers all context, not N file reads
- **Markdown + JSON dual state**: Human journal + machine checkpoint, both authoritative
- **Thin core, fat plugins**: Core handles shared concerns only; domain logic lives in plugins

### Critical Pitfalls

See [PITFALLS.md](PITFALLS.md) for all 15 pitfalls with prevention strategies.

1. **Metric gaming (Goodhart's Law)** -- Frozen evaluation module enforced by hooks, holdout test set agent never sees, secondary metrics as sanity checks
2. **Context window exhaustion** -- Fresh `claude -p` session per iteration, state persisted to filesystem, minimal context injection (last N results, not full history)
3. **Headless session hangs** -- Session timeout wrapper, pre-approved permissions in `.claude/settings.json`, watchdog process monitoring stdout
4. **Data leakage** -- Frozen data split logic, leakage detection tests, temporal validation enforcement, protocol rules reinforced by code checks
5. **Spawn budget explosion (swarm)** -- Budget inheritance (split, not duplicate), no recursive spawning (hard rule), per-agent cost caps

**Overnight-specific P0 requirements:** Session hang prevention, fresh-context pattern, heartbeat/watchdog, and hard cost caps must all ship in the core engine phase. Without these, no overnight run is trustworthy.

## Implications for Roadmap

Based on combined research, the dependency chain and domain complexity suggest 8 phases. The tabular domain is proven from v1-v3 and should be the first plugin; additional domains come after the plugin interface is validated.

### Phase 1: Core Foundation
**Rationale:** Everything depends on state management, git operations, and the plugin protocol definition. This is the skeleton.
**Delivers:** StateManager, GitOps, Checkpoint, Evaluator, DomainPlugin Protocol definition, Pydantic config models
**Addresses:** Config system, git state management, checkpoint/resume foundation
**Avoids:** Implicit state (Pitfall anti-pattern #4 from ARCHITECTURE.md)

### Phase 2: Plugin Infrastructure + Protocol Templates
**Rationale:** The plugin registry and template system must exist before any domain plugin can be built.
**Delivers:** Plugin registry, Jinja2 template loader/renderer, base protocol template, shared template sections (journal, diagnostics, stagnation)
**Addresses:** Protocol prompt injection, domain-specific CLAUDE.md generation
**Avoids:** Monolithic plugin anti-pattern

### Phase 3: Tabular Plugin
**Rationale:** Tabular is the proven domain from v1-v3. Building it first validates the plugin interface with known-good patterns before attempting DL or fine-tuning.
**Delivers:** Full TabularPlugin: prepare.py generator, train template, baselines (naive + seasonal-naive), diagnostics, Optuna search space, tabular protocol template
**Addresses:** Tabular ML support, leakage prevention, dual-baseline gate
**Avoids:** Data leakage (Pitfall #4), abstraction leaks (Pitfall #9 -- by proving interface with real domain)

### Phase 4: Scaffold Engine + CLI
**Rationale:** Users need an entry point. Scaffold creates the experiment directory structure from dataset + config.
**Delivers:** `autolab scaffold` and `autolab run` CLI commands, ScaffoldEngine (creates experiment dir, runs plugin scaffold methods, generates CLAUDE.md)
**Addresses:** Installable CLI, simple mode (zero-config), expert mode
**Avoids:** N/A -- straightforward CLI plumbing

### Phase 5: Run Engine + Guardrails
**Rationale:** The core experiment loop. This is the heart of the system -- fresh-context-per-iteration orchestration with full guardrails.
**Delivers:** RunEngine (session lifecycle, iteration loop, fresh claude -p spawning), GuardrailEngine (frozen files, cost caps, time budgets, leakage detection), Journal (experiments.md read/write), heartbeat/watchdog
**Addresses:** Keep/revert cycle, overnight reliability, crash recovery, experiment journal, cost tracking, live progress
**Avoids:** Context exhaustion (Pitfall #2), session hangs (Pitfall #6), silent failures (Pitfall #5), metric gaming (Pitfall #1)

### Phase 6: E2E Validation (Tabular)
**Rationale:** Validate the full stack end-to-end on a real dataset before building more domains. Same pattern as v1.0 Phase 7 and v2.0 Phase 14.
**Delivers:** Proof that scaffold -> run -> iterate -> checkpoint/resume works on a real tabular dataset, overnight run validation
**Addresses:** Full integration testing, overnight reliability confirmation
**Avoids:** Shipping untested integration

### Phase 7: Additional Domain Plugins
**Rationale:** Plugin interface is now validated with tabular. Build DL and fine-tuning plugins against the proven interface.
**Delivers:** DeepLearningPlugin (PyTorch Lightning training, GPU management, DL diagnostics), FineTunePlugin (LoRA/QLoRA, template canonicalization, base model comparison)
**Addresses:** Three-domain support differentiator
**Avoids:** GPU memory leaks (Pitfall #12 -- subprocess isolation), LoRA silent failures (Pitfall #11 -- sanity checks)

### Phase 8: Swarm Mode + Multi-Draft
**Rationale:** Requires all core features working. Parallel agents in worktrees with budget inheritance.
**Delivers:** SwarmEngine, scoreboard, claims system, multi-draft start, budget inheritance
**Addresses:** Multi-agent exploration, strategy diversity
**Avoids:** Spawn explosion (Pitfall #3 -- budget inheritance, no recursive spawning)

### Phase Ordering Rationale

- **Phases 1-2 before 3:** Plugin protocol must be defined before any plugin is built
- **Phase 3 before 7:** Tabular validates the plugin interface with a known domain; DL/fine-tuning build against a proven interface, not a theoretical one
- **Phase 4 before 5:** CLI and scaffold create the experiment structure that the run engine operates on
- **Phase 5 is the critical phase:** All overnight reliability pitfalls (context exhaustion, hangs, silent failures) must be solved here
- **Phase 6 before 7:** Prove the stack works before adding domain complexity
- **Phase 8 is last:** Swarm depends on everything else and is an enhancement, not a core requirement

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 5 (Run Engine):** Fresh-context-per-iteration session lifecycle is the most novel component. Needs research on claude -p session management, permission pre-approval, watchdog patterns, and heartbeat design.
- **Phase 7 (DL + Fine-tuning plugins):** GPU memory management, subprocess isolation for training, LoRA configuration space, and evaluation metrics for fine-tuning are domain-specific and less explored in autopilot-ml context.
- **Phase 8 (Swarm Mode):** Budget inheritance across agents is a new pattern (v1-v3 swarm had no token budget enforcement).

Phases with standard patterns (skip research-phase):
- **Phase 1 (Core Foundation):** Pydantic models, git operations, state management -- well-understood patterns, direct port from v1-v3.
- **Phase 2 (Plugin Infrastructure):** typing.Protocol + Jinja2 template rendering -- standard Python patterns.
- **Phase 3 (Tabular Plugin):** Direct extraction from autopilot-ml v1-v3 code. Patterns are proven.
- **Phase 4 (Scaffold + CLI):** Typer CLI + directory creation -- straightforward.
- **Phase 6 (E2E Validation):** Test execution, not novel engineering.

## GSD Patterns: Adopt vs Adapt

| GSD Pattern | Decision | Rationale |
|------------|----------|-----------|
| Fresh subagent contexts per task | **ADOPT** | Solves context exhaustion. Each experiment = one `claude -p` session. |
| Init-pattern (compound context load) | **ADOPT** | Single-call context bootstrapping prevents partial-state bugs. |
| Protocol-first behavior control (CLAUDE.md) | **ADOPT** | Proven in v1-v3. Text rules are more flexible than code enforcement. |
| Goal-backward verification | **ADOPT** | "Did metric actually improve?" not "Did we run experiments?" |
| STATE.md with regex parsing | **REJECT** | Use JSON for machine state, markdown for human journal. |
| YAML frontmatter in markdown | **REJECT** | Unnecessary coupling. Separate state from documentation. |
| Node.js CLI toolchain | **REJECT** | Python ecosystem. Use Typer. |
| Wave-based parallelism | **ADAPT** | Swarm mode uses worktree isolation, not wave-based plan scheduling. |
| Checkpoint types (human-verify/decision/action) | **ADAPT** | Simplify to: auto-continue (default), cost-warning (pause at budget %), human-review (end of run). |

## What NOT to Build

These are explicit anti-features. Building any of them is scope creep:

1. **Web UI / dashboard** -- CLI output + `autolab status` + `autolab results` commands
2. **Cloud orchestration** -- Local-first, single machine. Users wrap in their own infra.
3. **Tree-search exploration (AIDE/SELA style)** -- Interesting research, massive complexity. Linear iteration + branch-on-stagnation is sufficient.
4. **Paper writing (AI Scientist style)** -- Generate experiment reports, not LaTeX papers.
5. **AutoML-style exhaustive search** -- Agent reasons about what to try, not grid search.
6. **Kaggle integration** -- Different use case, AutoKaggle exists.
7. **Real-time data ingestion** -- Batch input only (CSV, Parquet, HuggingFace datasets).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified via PyPI/official docs. GSD internals verified from source. |
| Features | HIGH | Competitive landscape well-mapped (autoresearch, AIDE, SELA, AutoKaggle, AI Scientist v2). v1-v3 experience validates core patterns. |
| Architecture | HIGH | Component boundaries mapped from GSD source + v1-v3 experience. Plugin protocol pattern is standard Python. |
| Pitfalls | HIGH | Critical pitfalls confirmed by multiple sources (Ralph Loop, autoresearch docs, PyTorch forums, Claude Code issues). |

**Overall confidence:** HIGH

### Gaps to Address

- **Package name:** Must check PyPI availability for candidates (`mlforge`, `autoforge`, `mlpilot`, etc.) before writing `pyproject.toml`. This blocks Phase 1.
- **Claude -p session lifecycle:** Fresh-context-per-iteration pattern is well-reasoned but not yet validated with actual Claude Code headless sessions. Need to prototype in Phase 5 planning.
- **Fine-tuning evaluation metrics:** Which metrics to use for LoRA fine-tuning quality assessment (perplexity? task-specific? human eval?) needs domain research in Phase 7.
- **Budget inheritance mechanism:** How to enforce per-agent token/cost caps in swarm mode. v1-v3 swarm had process isolation but no budget tracking. Needs design in Phase 8.
- **Hook engine integration:** Whether to use Claude Code's PreToolUse/PostToolUse hooks or rely on protocol-only enforcement. Protocol-first is the recommendation, but hooks provide a safety net for frozen file protection. Decision can be deferred to Phase 5.

## Sources

### Primary (HIGH confidence -- direct source reading)
- GSD v1.22.4 source: `~/.claude/get-shit-done/` (34 workflows, 13 references, CLI toolchain)
- autopilot-ml v1-v3 codebase: `/home/tlupo/AutoML/src/automl/` (16 modules, 392 tests)
- [Karpathy autoresearch](https://github.com/karpathy/autoresearch) -- program.md protocol, train.py constraint
- [AIDE ML (Weco AI)](https://github.com/WecoAI/aideml) -- tree-search code optimization

### Secondary (MEDIUM confidence -- documentation + community)
- [AI Scientist v2 (Sakana AI)](https://github.com/SakanaAI/AI-Scientist-v2)
- [SELA paper](https://arxiv.org/abs/2410.17238) -- MCTS for AutoML pipelines
- [Ralph Loop architecture](https://blakecrosley.com/blog/ralph-agent-architecture) -- overnight agent patterns
- [Claude Code headless docs](https://code.claude.com/docs/en/headless)
- Claude Code issues [#8011](https://github.com/anthropics/claude-code/issues/8011), [#27172](https://github.com/anthropics/claude-code/issues/27172)
- [PyTorch GPU memory management](https://pytorch.org/blog/understanding-gpu-memory-2/)

### Tertiary (LOW confidence -- needs validation)
- LoRA/QLoRA autonomous fine-tuning patterns (no existing framework does this)
- Budget inheritance for multi-agent LLM spawning (novel pattern from Ralph Loop, unvalidated at scale)

---
*Research completed: 2026-03-19*
*Ready for roadmap: yes*
