# AutoML — Autonomous ML Research Framework

Give [Claude Code](https://docs.anthropic.com/en/docs/claude-code) a dataset and a metric, and it autonomously discovers the best-performing traditional ML pipeline — running experiments, keeping improvements, reverting failures, and logging everything — without human intervention.

## Quick Start

```bash
# Install
git clone https://github.com/robertlupo1997/autopilot-ml.git
cd autopilot-ml
uv sync

# Scaffold an experiment
uv run automl data.csv target_column accuracy --goal "Predict customer churn"

# Run the autonomous loop
cd experiment-churn/
claude -p "Read CLAUDE.md and begin." --allowedTools 'Bash(*)' 'Edit(*)' 'Write(*)' 'Read' 'Glob' 'Grep'
```

The agent will:
1. Generate 3-5 diverse initial models (XGBoost, LightGBM, RandomForest, etc.)
2. Evaluate each against your metric using cross-validation
3. Pick the best and iterate — keeping improvements, reverting failures
4. Log everything to `results.tsv` and git history
5. Run indefinitely until you stop it

## Features

**Single-agent mode** — one Claude Code agent iterating on `train.py`:

```bash
uv run automl data.csv target metric
```

**Multi-agent swarm** — N parallel agents in git worktrees with a shared scoreboard:

```bash
uv run automl data.csv target metric --agents 3
```

**Session resume** — checkpoint state persists across sessions:

```bash
uv run automl data.csv target metric --resume
```

## How It Works

```
data.csv + metric + goal
        |
        v
  ┌─────────────┐
  │  scaffold.py │  Generates experiment project:
  │              │  prepare.py (frozen), train.py (mutable),
  │              │  CLAUDE.md, program.md, settings.json
  └──────┬───────┘
         |
         v
  ┌─────────────┐
  │  claude -p   │  Agent reads CLAUDE.md protocol:
  │              │  Phase 1: Multi-draft (3-5 algorithms)
  │              │  Phase 2: Linear iteration (keep/revert)
  └──────┬───────┘
         |
    ┌────┴────┐
    │ keep?   │──yes──> git commit + log to results.tsv
    │         │──no───> git reset --hard HEAD
    └─────────┘
         |
         v
    (loop forever)
```

### Architecture: Staged Mutable Zones

The agent's scope is intentionally constrained:

| Version | What the agent can modify |
|---------|--------------------------|
| **v1 (current)** | Modeling only — algorithm, hyperparameters, ensembles |
| v2 (planned) | + Feature engineering and preprocessing |
| v3 (planned) | Full pipeline from raw CSV to predictions |

### Key Design Decisions

- **Frozen + mutable separation**: `prepare.py` (data loading, evaluation) is frozen; `train.py` is the only file the agent edits
- **Git for state**: branch per run, commit on keep, reset on discard — full audit trail
- **Multi-draft + linear**: generate diverse starting points (from AIDE), then iterate (from autoresearch)
- **PreToolUse hooks**: `guard-frozen.sh` denies writes to `prepare.py` at the Claude Code level
- **Stdlib-only coordination**: swarm modules use `fcntl`, `subprocess`, `pathlib` — no external dependencies

## Swarm Mode

When `--agents N` is specified (N > 1), the CLI spawns a `SwarmManager` that:

1. Creates N git worktrees under `.swarm/agent-N/`
2. Assigns algorithm families round-robin (agent-0 gets families [0, N, 2N...])
3. Spawns N `claude -p` subprocesses, each with its own worktree
4. Agents coordinate via file-locked `scoreboard.tsv` and TTL claim files
5. On completion, worktrees are cleaned up and the best `train.py` is preserved

## Project Structure

```
src/automl/
  prepare.py           # Frozen data pipeline (load, split, evaluate, preprocess)
  train_template.py    # Mutable train.py template (agent edits this)
  runner.py            # Experiment execution and metric extraction
  git_ops.py           # Git operations (branch, commit, revert, worktree)
  experiment_logger.py # results.tsv logging
  loop_helpers.py      # Keep/revert, stagnation detection, crash recovery
  drafts.py            # Algorithm families and multi-draft generation
  scaffold.py          # Project scaffolding (generates experiment directory)
  cli.py               # CLI entry point (automl command)
  checkpoint.py        # Session state persistence (checkpoint.json)
  swarm.py             # SwarmManager orchestrator
  swarm_scoreboard.py  # File-locked cross-agent scoreboard
  swarm_claims.py      # TTL-based experiment deduplication
  templates/           # CLAUDE.md, program.md, swarm_claude.md templates
```

## Testing

```bash
uv run pytest -x -q          # 250 tests, ~25s
uv run pytest -v              # Verbose output
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI (for running experiments)
- CPU only — traditional ML doesn't need GPU

## Acknowledgments

This project synthesizes ideas from several pioneering autonomous ML and research frameworks:

| Project | Author | Key Ideas Adopted |
|---------|--------|-------------------|
| [**autoresearch**](https://github.com/karpathy/autoresearch) | Andrej Karpathy | Single-file constraint, git state management, `program.md` domain context, "NEVER STOP" protocol, `results.tsv` logging, `run.log` output redirect |
| [**AIDE**](https://github.com/WecoAI/aideml) | Weco AI | Multi-draft start (diverse initial solutions), atomic improvements, separation of frozen/mutable concerns |
| [**SELA**](https://github.com/geekan/MetaGPT/tree/main/metagpt/ext/sela) | MetaGPT / Tsinghua | Stage-wise pipeline concept (informing our staged mutable zones roadmap) |
| [**AutoKaggle**](https://github.com/multimodal-art-projection/AutoKaggle) | Alibaba / MAP | Unit testing concept for ML pipelines |
| [**ML-Agent**](https://github.com/geekan/MetaGPT/tree/main/metagpt/ext/ai_ml_agent) | Shanghai AI Lab | Insight that domain-specific approaches outperform scale alone |
| [**The AI Scientist**](https://github.com/SakanaAI/AI-Scientist) | Sakana AI | Full research lifecycle vision (informing future roadmap) |

Additional inspiration from:
- [**pi-autoresearch**](https://github.com/JohnPaton/pi-autoresearch) (John Paton) — checkpoint/resume patterns
- [**autoresearch-at-home**](https://github.com/darien-schettler/autoresearch-at-home) (Darien Schettler) — multi-agent coordination patterns

## License

MIT
