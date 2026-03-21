# Getting Started with mlforge

mlforge is an autonomous ML research framework. Point it at a dataset and a goal, and Claude Code runs experiments overnight while you sleep. It profiles your data, picks the right approach, iterates on hypotheses, and delivers a trained model with a full research journal.

Three domains are supported: **tabular ML**, **deep learning**, and **LLM fine-tuning**.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Required for all functionality |
| uv | Latest | Fast Python package manager. [Install uv](https://docs.astral.sh/uv/) |
| Claude Code CLI | Latest | The agent runtime. [Install Claude Code](https://docs.anthropic.com/en/docs/claude-code) |
| Git | 2.30+ | Used for experiment state management |

Verify your setup:

```bash
python3 --version   # 3.11 or higher
uv --version
claude --version
git --version
```

---

## Installation

```bash
git clone https://github.com/robertlupo1997/autopilot-ml.git
cd autopilot-ml
uv sync                    # Core + tabular
```

For additional domains, install the relevant extras:

```bash
uv sync --extra dl         # + deep learning (PyTorch, timm, transformers)
uv sync --extra ft         # + fine-tuning (peft, trl, bitsandbytes)
```

You can combine extras: `uv sync --extra dl --extra ft`

---

## Your First Experiment

Run mlforge against the classic Iris dataset:

```bash
mlforge iris.csv "classify species"
```

That single command kicks off the full pipeline:

1. **Profiles your data** -- detects column types, missing values, class balance, and data shape.
2. **Detects the task** -- recognizes this as multi-class classification and selects accuracy as the default metric.
3. **Scaffolds a project** -- generates all the files the agent needs to begin research.
4. **Runs experiments autonomously** -- the agent forms hypotheses, trains models, evaluates results, keeps improvements, and reverts failures.

### Generated Project Structure

After scaffolding, your working directory looks like this:

```
mlforge-iris/
  CLAUDE.md               # Protocol rules the agent follows
  prepare.py              # Data loading and preprocessing (frozen)
  train.py                # Training template (agent modifies this)
  experiments.md          # Research journal
  mlforge.config.toml     # Run configuration and budget settings
```

The agent works inside this directory, committing each successful experiment to a Git branch (`mlforge/run-{id}`).

### Expected Output

When the run finishes, you will find:

```
mlforge-iris/
  artifacts/
    best_model.joblib     # Trained model, ready to load
    metadata.json         # Metric scores, config, training history
  experiments.md          # Full journal of every experiment attempted
  RETROSPECTIVE.md        # Post-session summary with recommendations
```

---

## Simple vs Expert Mode

### Simple Mode

Just provide your data and a goal in plain language:

```bash
mlforge data.csv "classify species"
mlforge sales.csv "predict monthly revenue"
mlforge reviews.csv "classify sentiment as positive or negative"
```

mlforge auto-detects the task type, metric, and optimization direction.

### Expert Mode

Take full control with flags:

```bash
mlforge data.csv "goal" \
  --metric f1_weighted \
  --direction maximize \
  --budget-usd 10 \
  --budget-experiments 100 \
  --enable-drafts \
  --custom-claude-md my_protocol.md
```

| Flag | Purpose |
|---|---|
| `--metric` | Override the auto-detected evaluation metric |
| `--direction` | `maximize` or `minimize` |
| `--budget-usd` | Maximum API spend for the session |
| `--budget-experiments` | Maximum number of experiments to attempt |
| `--enable-drafts` | Start with 3-5 diverse initial solutions, pick the best, then iterate |
| `--custom-claude-md` | Inject your own protocol rules into the agent's instructions |

---

## Resuming a Run

If a run gets interrupted, or you want to give the agent more budget to keep improving:

```bash
mlforge data.csv "goal" --resume --output-dir mlforge-my-data
```

The agent picks up from the last committed experiment and continues iterating.

---

## Understanding the Output

### experiments.md

The research journal. Every experiment is logged with a hypothesis, code changes, metric results, and the keep/revert decision. This is the single best way to understand what the agent tried and why.

### RETROSPECTIVE.md

A post-session summary. Contains key findings, what worked, what did not, and recommendations for follow-up runs.

### artifacts/

Contains the best model (`best_model.joblib`) and a `metadata.json` file with final metric scores, hyperparameters, and reproducibility information.

### Git History

Every kept experiment is a commit on the `mlforge/run-{id}` branch. You can inspect, diff, or cherry-pick any experiment the agent performed:

```bash
git log --oneline mlforge/run-{id}
```

---

## Budget Controls

mlforge enforces three budget limits. The run stops when any limit is reached.

| Flag | Default | Description |
|---|---|---|
| `--budget-minutes` | 60 | Maximum wall-clock time for the session |
| `--budget-usd` | 5.00 | Maximum Claude API spend |
| `--budget-experiments` | 50 | Maximum number of experiments to attempt |

Each individual experiment has a 5-minute timeout. If a single training run exceeds this, it is killed and counted as a failed experiment.

Example with custom budget:

```bash
mlforge large-dataset.csv "minimize RMSE" \
  --budget-minutes 120 \
  --budget-usd 15 \
  --budget-experiments 200
```

---

## Next Steps

Dive deeper with the domain-specific guides:

- **[Tabular ML Guide](tabular-guide.md)** -- Baselines, diagnostics, model families, stagnation handling
- **[Deep Learning Guide](deep-learning-guide.md)** -- Image/text classification, GPU configuration
- **[Fine-Tuning Guide](fine-tuning-guide.md)** -- LoRA, QLoRA, dataset formatting, memory planning
- **[Swarm Guide](swarm-guide.md)** -- Parallel multi-agent runs with scoreboard coordination
- **[Configuration Reference](configuration.md)** -- All CLI flags, config file format, metrics
