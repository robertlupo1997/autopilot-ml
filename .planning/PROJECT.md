# AutoLab

## What This Is

An autonomous ML research framework that brings GSD-style deterministic control to machine learning experimentation. Users point it at a dataset and a goal, and it runs structured experiments overnight — using hooks, protocol prompts, state tracking, and checkpoints to maintain guardrails while Claude Code acts as the autonomous researcher. Supports three domains: traditional tabular ML, deep learning (custom architectures), and LLM fine-tuning (LoRA/QLoRA). Installable CLI that works for both beginners ("give it a CSV and a goal") and expert ML engineers ("full config, custom protocols").

## Core Value

Leave an ML research agent running overnight with full confidence it will follow protocol, respect resource boundaries, track state, and produce meaningful results — without human intervention.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Shared core engine with plugin architecture for domain-specific ML workflows
- [ ] Hook engine (PreToolUse/PostToolUse) enforcing experiment boundaries and frozen file zones
- [ ] Protocol prompt system (CLAUDE.md templates) driving agent behavior per domain
- [ ] State tracking with checkpoints and session resume across context resets
- [ ] Experiment journal with structured knowledge accumulation across iterations
- [ ] Keep/revert experiment loop with git-based state management (autoresearch pattern)
- [ ] Multi-draft start: diverse initial solutions, pick best, iterate linearly
- [ ] Branch-on-stagnation: explore alternative approaches when stuck
- [ ] Resource guardrails: cost caps, GPU hour limits, disk usage boundaries
- [ ] Tabular ML plugin: scikit-learn, XGBoost, LightGBM pipelines with Optuna search
- [ ] Deep learning plugin: custom CNN/transformer training with PyTorch
- [ ] LLM fine-tuning plugin: LoRA/QLoRA fine-tuning of open models (Llama, Mistral, etc.)
- [ ] Diagnostics engine: error analysis telling the agent WHERE the model fails
- [ ] Installable CLI: `autolab <dataset> <goal> --mode=tabular|deeplearning|finetune`
- [ ] Simple mode for beginners (minimal config) and expert mode (full protocol control)
- [ ] Verification and phase lifecycle adapted from GSD (plan, execute, verify)
- [ ] Swarm mode: parallel agents in git worktrees with scoreboard coordination
- [ ] Walk-forward temporal validation for time-series/forecasting tasks

### Out of Scope

- Web UI or dashboard — CLI-first, terminal output and log files
- Cloud orchestration (AWS/GCP job submission) — local-first, single machine
- Real-time data ingestion — batch input (CSV, Parquet, HuggingFace datasets)
- Building a new LLM from scratch — fine-tuning existing models only
- AutoML competition platform (Kaggle integration) — research tool, not competition tool

## Context

### Origin

This project evolves from autopilot-ml (v1.0-v3.0), an autonomous ML framework for tabular data. The v1-v3 code proved the autoresearch pattern works: Claude Code as autonomous researcher, git for state, CLAUDE.md protocol prompts for behavior control, hooks for boundary enforcement. The new vision expands this to all ML domains and restructures the architecture to mirror GSD's plugin-based, hook-driven design.

### Key Inspirations

- **Karpathy's autoresearch**: Single-file constraint, "NEVER STOP" loop, results.tsv tracking, program.md domain expertise injection
- **GSD framework**: Hook engine, protocol prompts, phased lifecycle, state management, checkpoint/resume, verification agents, plugin architecture
- **GSD forks**: Community extensions showing how the plugin model adapts to different domains
- **autopilot-ml v1-v3**: Proven patterns — multi-draft start, keep/revert loop, branch-on-stagnation, swarm mode, experiment journal, diagnostics

### Name Decision

Working name: **AutoLab** — pending research to confirm the name isn't taken by a major existing project. Repo rename from autopilot-ml if clear.

## Constraints

- **Architecture**: Shared core + plugins — the GSD pattern adapted for ML domains
- **Rewrite**: Fresh codebase, not refactored from v1-v3 — old code is reference only
- **Runtime**: Must work unattended overnight — crash recovery, checkpoint/resume are mandatory
- **Claude Code**: The agent orchestrator — hooks and protocols must work in headless `claude -p` mode
- **Python**: Primary language — ML ecosystem is Python-first
- **v1 scope**: All three modes (tabular, deep learning, fine-tuning) working end-to-end

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Rewrite from scratch | v1-v3 architecture doesn't support plugin model; carrying old code constrains design | -- Pending |
| Shared core + plugins | GSD pattern — common engine with domain-specific modules | -- Pending |
| AutoLab name | Short, memorable, fits "automated research lab" vision | -- Pending (research needed) |
| Full GSD architecture | Hooks, protocols, agents, phases, state, checkpoints — the whole system adapted for ML | -- Pending |
| Research guardrail design | Let deep research determine optimal control model rather than guessing | -- Pending |

---
*Last updated: 2026-03-19 after initialization*
