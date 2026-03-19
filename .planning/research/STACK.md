# Technology Stack

**Project:** AutoLab (working name -- see Name Availability section)
**Researched:** 2026-03-19
**Overall Confidence:** HIGH (GSD internals verified from source; ML libraries verified via PyPI/official docs)

---

## GSD Framework Deep Analysis

### Architecture Overview (Verified from Source: ~/.claude/get-shit-done/)

GSD v1.22.4 is a **markdown-driven state machine** implemented as Claude Code slash commands. It is NOT a traditional plugin system -- it is a prompt engineering framework that orchestrates Claude Code subagents via markdown templates, workflow definitions, and a Node.js CLI toolchain.

**Key architectural insight for AutoLab:** GSD does not have "hooks" in the programmatic sense (no event emitter, no callback registration). It has:

1. **Workflow definitions** (`.md` files in `workflows/`) -- markdown prompts that define multi-step processes (plan-phase, execute-phase, verify-phase, etc.)
2. **Templates** (`.md` files in `templates/`) -- scaffolds for planning documents (STATE.md, ROADMAP.md, PLAN.md, SUMMARY.md)
3. **Reference docs** (`.md` files in `references/`) -- injected context about patterns (checkpoints, verification, git integration, model profiles)
4. **A CLI toolchain** (`bin/gsd-tools.cjs` + `bin/lib/*.cjs`) -- Node.js utilities for state management, phase CRUD, roadmap parsing, frontmatter handling, commit automation
5. **Subagent orchestration** -- fresh Claude Code contexts spawned per task via `Task()`, each getting a clean 200K context window

### GSD Internal Components (from source analysis)

| Component | File(s) | What It Does |
|-----------|---------|--------------|
| **State Engine** | `lib/state.cjs` | Reads/writes STATE.md with YAML frontmatter sync. Tracks: current phase, plan, status, progress, decisions, blockers, session continuity. Every write syncs markdown body to frontmatter. |
| **Phase Manager** | `lib/phase.cjs` | CRUD for phases: add, insert (decimal), remove (with renumber), complete (with state transition). Supports letter-suffix (12A) and decimal (12.1) phases. |
| **Roadmap Parser** | `lib/roadmap.cjs` | Extracts phase sections from ROADMAP.md, analyzes plan progress, updates progress tables. |
| **Config System** | `lib/config.cjs` | `.planning/config.json` with defaults. Supports: model_profile, branching_strategy, parallelization, brave_search, workflow toggles (research, plan_checker, verifier, nyquist_validation). |
| **Model Profiles** | `lib/core.cjs` | Maps agent types to Claude models based on profile (quality/balanced/budget). Per-agent overrides via `model_overrides`. Returns "inherit" for opus-tier to avoid version conflicts. |
| **Template System** | `lib/template.cjs` | Generates pre-filled PLAN.md, SUMMARY.md, VERIFICATION.md with frontmatter from phase context. |
| **Verification** | `lib/verify.cjs` | Plan structure validation, phase completeness checks, reference resolution, commit verification, artifact verification. |
| **Frontmatter** | `lib/frontmatter.cjs` | YAML frontmatter CRUD: extract, reconstruct, validate against schemas (plan, summary, verification). |
| **Init Commands** | `lib/init.cjs` | Compound context loaders for workflows. Each `init <workflow>` call aggregates config, phase info, state, models into a single JSON payload, minimizing subagent context. |
| **Milestone Manager** | `lib/milestone.cjs` | Archives completed milestones, moves phase dirs, creates MILESTONES.md history. |

### GSD Workflow Execution Model

```
User: /gsd:execute-phase 5
  |
  v
execute-phase.md workflow:
  1. gsd-tools init execute-phase 5  --> JSON context blob
  2. gsd-tools phase-plan-index 5    --> plans grouped by wave
  3. For each wave:
     a. Describe what's being built (from plan objectives)
     b. Spawn subagent(s) via Task() with execute-plan.md
        - Each subagent gets: PLAN.md, STATE.md, config.json
        - Fresh 200K context window (no context rot)
        - Creates SUMMARY.md + git commits on completion
     c. Collect results, update state
  4. After all waves: spawn verifier subagent (verify-phase.md)
  5. gsd-tools phase complete 5       --> advance state
```

### GSD Checkpoint Types (from references/checkpoints.md)

| Type | Frequency | Purpose |
|------|-----------|---------|
| `checkpoint:human-verify` | 90% | Agent completed work, human confirms visually/functionally |
| `checkpoint:decision` | 9% | Human makes architectural choice |
| `checkpoint:human-action` | 1% | Truly manual step (email verification, etc.) |

Auto-mode bypasses verify/decision checkpoints. Human-action always stops.

### GSD State Machine

```
Ready to plan --> Planning --> Ready to execute --> Executing --> Phase complete
     ^                                                              |
     |______________ verify ________ advance state _________________|
```

State stored in STATE.md (markdown body + YAML frontmatter). Frontmatter auto-synced on every write for machine-readable access.

### What AutoLab Should Borrow from GSD

| GSD Pattern | AutoLab Adaptation |
|-------------|-------------------|
| Fresh subagent contexts | Each experiment iteration gets a fresh Claude context with clean CLAUDE.md protocol |
| STATE.md as living memory | experiment journal (experiments.md) + run state file |
| Workflow markdown templates | Protocol templates per domain (tabular, DL, fine-tuning) |
| gsd-tools CLI | Python CLI (`autolab`) wrapping experiment orchestration |
| Phase lifecycle (plan/execute/verify) | Experiment lifecycle (draft/iterate/diagnose/branch) |
| config.json | TOML/YAML config per run with domain defaults |
| Model profiles | Resource profiles (CPU-only, single-GPU, multi-GPU) |
| Checkpoint system | Human approval gates (cost cap warnings, quality thresholds) |
| Verification subagent | Diagnostic engine analyzing model failures |

### What AutoLab Should NOT Borrow from GSD

| GSD Pattern | Why Not |
|-------------|---------|
| Node.js CLI toolchain | ML ecosystem is Python-first; no reason to add a JS dependency |
| Markdown-driven state (STATE.md regex parsing) | Fragile; use structured config (TOML/Pydantic) for machine state, markdown for human-readable journals |
| YAML frontmatter in markdown | Unnecessary complexity; separate state files from documentation |
| Decimal phase numbering (12.1, 12.2) | Experiments use sequential numbering or hashes |
| Wave-based parallelization | Experiment parallelism is better handled by swarm mode (worktrees) |

### GSD Forks and Extensions (from web search)

| Fork | What It Does | Relevance |
|------|-------------|-----------|
| **GSD-2** (gsd-build/gsd-2) | Standalone CLI on Pi SDK. Direct TypeScript agent harness access. Supports Claude Code, OpenCode, Gemini CLI. | Shows evolution toward standalone CLI -- AutoLab should also be a standalone Python CLI, not a Claude Code extension |
| **gsd-opencode** (rokicool) | Port to OpenCode runtime | Shows multi-runtime is desirable but AutoLab is Claude Code-only (at least v1) |
| **GSD Cost Saver** (itsjwill) | Multi-model intelligence, adaptive context loading, rollback/recovery | Confirms cost management and rollback are valued features |

**Confidence: HIGH** -- GSD internals verified by reading actual source code at ~/.claude/get-shit-done/.

---

## Name Availability: "AutoLab"

### Findings

| Usage | Project | Risk Level |
|-------|---------|------------|
| **PyPI: `autolab`** | Scientific instrument control (autolab-project/autolab). Active, v2.0.3. | **BLOCKING** -- name is taken on PyPI |
| **PyPI: `autolab-core`** | Berkeley Automation Lab utilities | Name family is occupied |
| **GitHub: autolab/Autolab** | CMU course management/autograding platform. Ruby on Rails. 7k+ stars. Very well known in CS education. | **HIGH** -- major name collision in tech/ML space |
| **GitHub: autolab-project/autolab** | The scientific instruments package | Additional collision |

### Recommendation: Rename

**"AutoLab" is not viable.** Two major projects own this name: CMU's autograding platform (well-known in CS) and a PyPI package for lab instrument control. Using "AutoLab" would cause confusion and block PyPI distribution.

**Alternative names to consider:**

| Name | PyPI Available | Meaning | Check |
|------|---------------|---------|-------|
| `autolab-ml` | Likely available | AutoLab for ML | Distinguishes from existing autolab |
| `mlpilot` | Needs check | ML autopilot | Clean, descriptive |
| `labrat` | Needs check | Lab researcher agent | Memorable, playful |
| `autoforge` | Needs check | Auto-forging ML models | Strong, unique |
| `mlforge` | Needs check | ML model forge | Clean |
| `autoresearch` | Needs check | Direct Karpathy reference | Descriptive |

**Action needed:** Check PyPI availability for alternatives before committing. Use `pip index versions <name>` or check pypi.org/<name>.

**Confidence: HIGH** -- verified via PyPI and GitHub search.

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Python** | >=3.11 | Runtime | ML ecosystem standard. 3.11+ for performance (10-25% faster CPython). 3.10 is scikit-learn minimum but 3.11 gives tomllib stdlib. | HIGH |
| **Typer** | >=0.12 | CLI framework | Built on Click, type-hint native, auto-generated help, less boilerplate. Click is the power underneath if needed. Industry standard for modern Python CLIs. | HIGH |
| **Rich** | >=13.0 | Terminal output | Beautiful tables, progress bars, panels, markdown rendering. Used by Typer for help formatting. Essential for experiment status display. | HIGH |
| **Pydantic** | >=2.7 | Data validation & settings | Type-safe config, environment variable loading, schema validation. pydantic-settings for layered config (defaults < file < env < CLI). 5x faster than v1. | HIGH |
| **pydantic-settings** | >=2.13 | Configuration management | TOML/YAML/JSON config file support, env var override, SecretStr for API keys. Python 3.10-3.14 support. | HIGH |

### ML Libraries: Tabular Domain

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **scikit-learn** | >=1.8.0 | ML algorithms, preprocessing, pipelines | Standard. Ridge, RandomForest, SVR, etc. Pipeline API for reproducible transforms. | HIGH |
| **XGBoost** | >=3.2.0 | Gradient boosting | Best-in-class for tabular. scikit-learn API compatible. | HIGH |
| **LightGBM** | >=4.6.0 | Gradient boosting | Faster training than XGBoost on large datasets, handles categoricals natively. | HIGH |
| **CatBoost** | >=1.2 | Gradient boosting | Best with high-cardinality categoricals, no encoding needed. | MEDIUM |
| **Optuna** | >=4.8.0 | Hyperparameter optimization | Define-by-run API, pruning, multi-objective support. GP-based Bayesian optimization from v4.4+. | HIGH |
| **pandas** | >=2.2 | Data manipulation | Standard for tabular data. Required by all ML libraries. | HIGH |
| **numpy** | >=1.26 | Numerical computing | Foundation dependency. | HIGH |

### ML Libraries: Deep Learning Domain

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **PyTorch** | >=2.5 | Deep learning framework | Industry standard for research. Dynamic computation graph. | HIGH |
| **PyTorch Lightning** | >=2.6.0 | Training loop abstraction | Eliminates boilerplate (checkpointing, logging, distributed training). 20+ hooks for customization. Requires Python >=3.10. | HIGH |
| **torchvision** | >=0.20 | Computer vision datasets/transforms | Standard companion to PyTorch. | HIGH |
| **Optuna** | >=4.8.0 | Hyperparameter search | Same as tabular -- unified search across all domains. | HIGH |

### ML Libraries: LLM Fine-Tuning Domain

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **transformers** | >=4.49 | Model loading, tokenization | HuggingFace standard. Access to all open models. | HIGH |
| **peft** | >=0.14 | LoRA/QLoRA adapters | Parameter-efficient fine-tuning. 10-20x memory reduction. | HIGH |
| **trl** | >=0.15 | SFTTrainer | Supervised fine-tuning made simple. Handles data collation, mixed precision. | HIGH |
| **bitsandbytes** | >=0.45 | 4-bit/8-bit quantization | Required for QLoRA. Enables 7B model fine-tuning on consumer GPU (RTX 4090). | HIGH |
| **accelerate** | >=1.4 | Distributed training | Multi-GPU, mixed precision, DeepSpeed integration. | HIGH |
| **datasets** | >=3.3 | Dataset loading | HuggingFace datasets for standard benchmarks + custom data. | HIGH |

### Infrastructure & Utilities

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **GitPython** | >=3.1 | Git operations | Programmatic branch/commit/reset for keep/revert loop. Already proven in autopilot-ml. | HIGH |
| **tomli** / **tomllib** | stdlib (3.11+) | Config parsing | TOML is the Python config standard (pyproject.toml). stdlib in 3.11+. | HIGH |
| **Jinja2** | >=3.1 | Protocol templates | CLAUDE.md template rendering with domain-specific variables. Already proven in autopilot-ml (.tmpl files). | HIGH |
| **filelock** | >=3.12 | Process coordination | File-based locking for swarm mode scoreboard. Already proven in autopilot-ml. | HIGH |
| **pytest** | >=8.0 | Testing | Standard Python testing. Already have 392 tests in v1-v3. | HIGH |
| **pytest-cov** | >=5.0 | Coverage | Coverage reporting for CI. | HIGH |
| **ruff** | >=0.8 | Linting + formatting | Replaces flake8 + black + isort. 10-100x faster. Industry standard 2025+. | HIGH |
| **mypy** | >=1.10 | Type checking | Static type analysis. Pydantic models give runtime + static safety. | MEDIUM |

### Plugin Architecture

Use **importlib + entry_points** (stdlib), NOT pluggy or stevedore.

**Rationale:** AutoLab has exactly 3 domain plugins (tabular, deeplearning, finetuning). This is not a public plugin ecosystem where third parties write extensions. The plugin system needs:
- Domain registration (name, supported task types, default config)
- Protocol template selection (which CLAUDE.md template to use)
- Library dependency declaration (which ML packages needed)
- Hook points (prepare_data, create_model, evaluate, diagnose)

This is achievable with a base class + `importlib.import_module()` + an `entry_points` group in pyproject.toml for future extensibility. No need for pluggy's hookspec/hookimpl complexity or stevedore's namespace management.

```python
# src/autolab/plugins/base.py
class DomainPlugin(ABC):
    name: str
    task_types: list[str]

    @abstractmethod
    def prepare_data(self, config: RunConfig) -> PreparedData: ...

    @abstractmethod
    def create_model(self, config: RunConfig, trial: optuna.Trial) -> Any: ...

    @abstractmethod
    def evaluate(self, model, data: PreparedData) -> Metrics: ...

    @abstractmethod
    def diagnose(self, model, data: PreparedData, metrics: Metrics) -> Diagnosis: ...
```

**Confidence: HIGH** -- importlib + ABC is the simplest correct solution for a known, small plugin set.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| CLI | Typer | Click | Typer wraps Click with less boilerplate. Can always drop to Click internals. |
| CLI | Typer | argparse | Too verbose, no auto-completion, no rich help formatting. |
| Config | Pydantic + TOML | YAML | TOML is Python's standard (pyproject.toml). YAML has footgun indentation. |
| Config | Pydantic | dataclasses | Pydantic gives validation, env vars, settings management. dataclasses are just containers. |
| Plugin | importlib + ABC | pluggy | Pluggy is for public plugin ecosystems (pytest). Overkill for 3 known plugins. |
| Plugin | importlib + ABC | stevedore | OpenStack-era complexity. Entry points are available directly via importlib.metadata. |
| Deep Learning | Lightning | Raw PyTorch | Lightning eliminates training loop boilerplate and handles checkpointing, logging. |
| Fine-tuning | HF transformers + PEFT | Axolotl | Axolotl is a wrapper around the same stack. Direct usage gives more control. |
| Fine-tuning | HF transformers + PEFT | LitGPT | Less ecosystem support, fewer models. |
| Linting | ruff | flake8 + black | ruff replaces both, 100x faster, single tool. |
| Git | GitPython | subprocess git | GitPython gives proper Python API, error handling, branch management. Proven in v1-v3. |
| Testing | pytest | unittest | pytest is the standard. Already using it with 392 tests. |
| State format | Structured TOML + markdown journal | GSD-style STATE.md | Regex-parsing markdown for machine state is fragile. Separate machine state (TOML/JSON) from human journal (markdown). |

---

## Project Layout

```
autolab/                          # or whatever the final name is
  pyproject.toml                  # Build config, dependencies, entry_points
  src/
    autolab/
      __init__.py
      cli.py                      # Typer CLI: autolab <dataset> <goal> --mode=tabular
      config.py                   # Pydantic models for run configuration
      engine/
        __init__.py
        runner.py                 # Main experiment orchestration loop
        loop.py                   # Keep/revert iteration logic
        drafts.py                 # Multi-draft initial solutions
        stagnation.py             # Branch-on-stagnation detection
        swarm.py                  # Parallel agents in worktrees
      state/
        __init__.py
        journal.py                # Experiment journal (experiments.md)
        git_ops.py                # Git operations (branch, commit, reset)
        checkpoint.py             # Session save/resume
        scoreboard.py             # Swarm coordination
      plugins/
        __init__.py
        base.py                   # DomainPlugin ABC
        tabular/
          __init__.py
          plugin.py               # TabularPlugin implementation
          prepare.py              # Data preparation
          models.py               # Model creation
          diagnose.py             # Error analysis
        deeplearning/
          __init__.py
          plugin.py               # DeepLearningPlugin implementation
          trainer.py              # Lightning training
          diagnose.py
        finetuning/
          __init__.py
          plugin.py               # FineTuningPlugin implementation
          trainer.py              # PEFT/TRL training
          diagnose.py
      templates/
        claude_tabular.md.tmpl    # CLAUDE.md protocol for tabular
        claude_dl.md.tmpl         # CLAUDE.md protocol for deep learning
        claude_ft.md.tmpl         # CLAUDE.md protocol for fine-tuning
        program.md.tmpl           # Domain expertise injection (a la Karpathy)
      guardrails/
        __init__.py
        cost.py                   # Cost tracking and caps
        resources.py              # GPU hours, disk usage
        frozen.py                 # Frozen file enforcement
  tests/
    test_cli.py
    test_config.py
    test_engine/
    test_plugins/
    test_state/
    test_guardrails/
```

---

## Installation

### Core (tabular only -- no GPU required)
```bash
pip install autolab[tabular]
# Installs: scikit-learn, xgboost, lightgbm, optuna, pandas, numpy, gitpython, typer, rich, pydantic, pydantic-settings, jinja2, filelock
```

### Deep Learning
```bash
pip install autolab[deeplearning]
# Adds: torch, pytorch-lightning, torchvision
```

### LLM Fine-Tuning
```bash
pip install autolab[finetuning]
# Adds: transformers, peft, trl, bitsandbytes, accelerate, datasets
```

### All Domains
```bash
pip install autolab[all]
```

### Development
```bash
pip install -e ".[dev]"
# Adds: pytest, pytest-cov, ruff, mypy
```

---

## Version Pinning Strategy

Pin **minimum versions** in pyproject.toml (>=X.Y), not exact versions. ML libraries release frequently and users need flexibility. Use a lockfile (uv.lock or pip-compile) for reproducible CI.

Exception: Pin **maximum major versions** for libraries with known breaking changes between majors (e.g., pydantic>=2.7,<3).

---

## Sources

### GSD Internals (PRIMARY -- direct source analysis)
- `~/.claude/get-shit-done/bin/gsd-tools.cjs` -- CLI router, 592 lines
- `~/.claude/get-shit-done/bin/lib/core.cjs` -- Config, model profiles, phase utilities
- `~/.claude/get-shit-done/bin/lib/state.cjs` -- State engine with frontmatter sync
- `~/.claude/get-shit-done/bin/lib/phase.cjs` -- Phase CRUD and lifecycle
- `~/.claude/get-shit-done/bin/lib/config.cjs` -- Config management
- `~/.claude/get-shit-done/bin/lib/init.cjs` -- Workflow initialization
- `~/.claude/get-shit-done/workflows/execute-phase.md` -- Wave-based execution
- `~/.claude/get-shit-done/workflows/execute-plan.md` -- Plan execution with checkpoint routing
- `~/.claude/get-shit-done/references/checkpoints.md` -- Checkpoint types and automation
- `~/.claude/get-shit-done/references/verification-patterns.md` -- Verification system
- `~/.claude/get-shit-done/references/model-profiles.md` -- Agent model allocation

### Name Availability
- [autolab on PyPI](https://pypi.org/project/autolab/) -- Scientific instruments package, v2.0.3
- [CMU Autolab](https://github.com/autolab/Autolab) -- Course management platform, 7k+ stars
- [autolab-project](https://github.com/autolab-project/autolab) -- Lab instruments, active development

### ML Libraries (verified via PyPI/official docs)
- [scikit-learn 1.8.0](https://pypi.org/project/scikit-learn/) -- Dec 2025
- [XGBoost 3.2.0](https://pypi.org/project/xgboost/) -- Feb 2026
- [LightGBM 4.6.0](https://pypi.org/project/lightgbm/) -- Feb 2025
- [Optuna 4.8.0](https://optuna.readthedocs.io/) -- Mar 2026
- [PyTorch Lightning 2.6.1](https://pypi.org/project/lightning/) -- Jan 2026
- [PEFT 0.14.0](https://github.com/huggingface/peft) -- 2025
- [TRL 0.15.2](https://pypi.org/project/trl/) -- 2025

### CLI & Infrastructure
- [Typer](https://typer.tiangolo.com/alternatives/) -- Click comparison, >=0.12
- [Pydantic Settings 2.13.1](https://pypi.org/project/pydantic-settings/) -- Feb 2026
- [ruff](https://docs.astral.sh/ruff/) -- Linting standard

### GSD Ecosystem
- [GSD Framework](https://github.com/gsd-build/get-shit-done) -- 31k+ stars
- [GSD-2](https://github.com/gsd-build/gsd-2) -- Standalone CLI evolution
- [GSD OpenCode fork](https://github.com/rokicool/gsd-opencode) -- Multi-runtime port
