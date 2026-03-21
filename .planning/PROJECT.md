# mlforge

## What This Is

An autonomous ML research framework that brings GSD-style deterministic control to machine learning experimentation. Users point it at a dataset and a goal, and it runs structured experiments overnight — using hooks, protocol prompts, state tracking, and checkpoints to maintain guardrails while Claude Code acts as the autonomous researcher. Supports three domains: traditional tabular ML, deep learning (custom architectures), and LLM fine-tuning (LoRA/QLoRA). Installable CLI that works for both beginners ("give it a CSV and a goal") and expert ML engineers ("full config, custom protocols").

## Core Value

Leave an ML research agent running overnight with full confidence it will follow protocol, respect resource boundaries, track state, and produce meaningful results — without human intervention.

## Current State (2026-03-21)

- **v1.0 milestone complete**: 24 phases, 48/48 requirements, 583 tests
- **Repo**: github.com/robertlupo1997/mlforge (renamed from autopilot-ml)
- **Package**: src/mlforge/ (src/automl/ legacy code removed)
- **Docs**: README.md, CONTRIBUTING.md, docs/ (7 guides)
- **Pushed to remote** and live

## Architecture

- **Plugin system**: Shared core engine (engine.py) with domain-specific plugins via typing.Protocol
- **Three domains**: Tabular (sklearn/XGBoost/LightGBM/Optuna), DL (PyTorch/timm/transformers), FT (peft/trl/LoRA/QLoRA)
- **Git for state**: branch per run, commit on keep, hard reset on revert, tag best
- **Protocol prompts**: Jinja2 CLAUDE.md templates control agent behavior per domain
- **Multi-draft + linear**: 3-5 diverse initial solutions, pick best, iterate linearly
- **Branch-on-stagnation**: 3 consecutive reverts -> branch from best-ever commit, try different model family
- **Diagnostics**: worst predictions, bias direction, feature-error correlations
- **Swarm mode**: Parallel claude -p agents in git worktrees, file-locked scoreboard
- **Guardrails**: Cost caps, time limits, disk usage, per-experiment timeouts
- **Checkpoint/resume**: Crash recovery for unattended overnight runs
- **Experiment journal**: Hypothesis -> result -> diff tracking in JSONL + rendered markdown

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Rewrite from scratch | v1-v3 architecture doesn't support plugin model | Done |
| Shared core + plugins | typing.Protocol structural subtyping, no ABC inheritance | Done |
| mlforge name | Available on PyPI, "ML forge" metaphor | Done, repo renamed |
| JSON for machine state, markdown for journal | Rejected GSD's markdown-as-database | Done |
| Tabular first to validate architecture | Prove plugin model works before DL/FT | Done |
| Agent-driven architecture | CLAUDE.md protocol rules, not complex Python imports | Done |
| Protocol-first design | Behaviors are text rules, not code enforcement | Done |

## Constraints

- **Architecture**: Shared core + plugins — the GSD pattern adapted for ML domains
- **Runtime**: Must work unattended overnight — crash recovery, checkpoint/resume are mandatory
- **Claude Code**: The agent orchestrator — hooks and protocols must work in headless `claude -p` mode
- **Python**: Primary language — ML ecosystem is Python-first

## Out of Scope

- Web UI or dashboard — CLI-first, terminal output and log files
- Cloud orchestration (AWS/GCP job submission) — local-first, single machine
- Real-time data ingestion — batch input (CSV, Parquet, JSON, JSONL)
- Building a new LLM from scratch — fine-tuning existing models only

## Origin

This project evolved from autopilot-ml (v1.0-v3.0), an autonomous ML framework for tabular data. The v1-v3 code proved the autoresearch pattern works. mlforge is the ground-up rewrite that generalizes to all ML domains with a proper plugin architecture. The old src/automl/ code has been removed; milestones are archived in .planning/milestones/.

---
*Last updated: 2026-03-21*
