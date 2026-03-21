# mlforge

An autonomous ML research framework. Point it at a dataset and a goal, and it runs structured experiments overnight using **Claude Code** as the autonomous researcher.

Supports **tabular ML**, **deep learning** (PyTorch), and **LLM fine-tuning** (LoRA/QLoRA).

Inspired by Karpathy's [autoresearch](https://github.com/karpathy/autoresearch).

---

## Quick Start

```bash
# Install
git clone https://github.com/robertlupo1997/autopilot-ml.git
cd autopilot-ml
uv sync

# Tabular ML -- just point and shoot
mlforge sales.csv "predict customer churn"

# Deep learning -- image classification with PyTorch + timm
uv sync --extra dl
mlforge images/ "classify plant diseases" --domain deeplearning

# Fine-tuning -- LoRA on a HuggingFace model
uv sync --extra ft
mlforge dataset.jsonl "summarize medical notes" \
  --domain finetuning \
  --model-name meta-llama/Llama-3-8B

# Swarm mode -- 5 parallel agents racing on the same problem
mlforge data.csv "predict revenue" --swarm --n-agents 5
```

**Requirements**: Python 3.11+, [uv](https://docs.astral.sh/uv/), [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated. CPU-only for tabular; GPU optional for deep learning and fine-tuning.

---

## How It Works

```
mlforge data.csv "predict churn"
        |
        v
+------------------+
|  1. Auto-Profile  |  Detect task type, choose metric, generate prepare.py
+--------+---------+
         v
+------------------+
|  2. Scaffold      |  Frozen data pipeline + mutable train.py + CLAUDE.md protocol
+--------+---------+
         v
+------------------+
|  3. Git Branch    |  mlforge/run-{id}
+--------+---------+
         v
+--------------------------------------+
|  4. Experiment Loop                   |
|                                       |
|   Spawn claude -p with protocol       |
|        |                              |
|        v                              |
|   Agent edits train.py, runs it,      |
|   reports metric via structured JSON  |
|        |                              |
|        v                              |
|   Improved? -- yes --> git commit     |
|        |                              |
|        no ----------> git reset       |
|        |                              |
|        v                              |
|   Diagnostics: analyze WHERE it       |
|   fails, inject into next prompt      |
|        |                              |
|        v                              |
|   Repeat until budget exhausted       |
+------------------+-------------------+
                   v
+--------------------------------------+
|  5. Export best model + retrospective |
+--------------------------------------+
```

Every experiment is a git commit. Crash? `--resume` picks up where you left off.

---

## Three Domains

### Tabular ML

scikit-learn, XGBoost, LightGBM with Optuna hyperparameter search. Auto-detects classification vs. regression and selects the appropriate metric.

```bash
mlforge customers.csv "predict churn" --metric f1 --budget-usd 3.0
```

Metrics: accuracy, f1, rmse, mae, r2, and more.

### Deep Learning

PyTorch with timm (images) and transformers (text). Generates GPU-aware training templates.

```bash
uv sync --extra dl
mlforge images/ "classify defects" --domain deeplearning --budget-experiments 20
```

Metrics: accuracy, f1, loss.

### Fine-Tuning

LoRA/QLoRA via peft and trl. Point it at a HuggingFace model and a dataset.

```bash
uv sync --extra ft
mlforge data.jsonl "answer questions about legal documents" \
  --domain finetuning \
  --model-name mistralai/Mistral-7B-v0.1 \
  --budget-experiments 10
```

Metrics: perplexity, rouge1, rougeL, loss.

---

## Key Features

| Feature | Description |
|---|---|
| **Auto-profiling** | Detects task type, picks metric, generates data pipeline |
| **Plugin system** | Shared core engine with domain-specific plugins |
| **Protocol prompts** | Jinja2 CLAUDE.md templates control agent behavior |
| **Git for state** | Branch per run, commit on keep, hard reset on revert |
| **Multi-draft start** | 3-5 diverse initial solutions, pick best, iterate linearly |
| **Branch-on-stagnation** | 3 consecutive reverts -> branch from best-ever, try different model family |
| **Diagnostics** | Tells the agent *where* the model fails (worst slices, bias, correlation) |
| **Swarm mode** | Parallel agents in git worktrees with file-locked scoreboard |
| **Guardrails** | Cost caps, time limits, disk usage, per-experiment timeouts |
| **Checkpoint/resume** | Crash recovery for unattended overnight runs |
| **Experiment journal** | Hypothesis -> result -> diff tracking in experiments.md |
| **Retrospective** | Post-run summary: what worked, what didn't, metric trajectory |

---

## Architecture

```
+------------------------------------------------------+
|                    CLI (cli.py)                        |
+------------------------------------------------------+
|                 Core Engine (engine.py)                |
|                                                       |
|  scaffold --- git_ops --- checkpoint --- guardrails   |
|  profiler --- results --- export --- retrospective    |
|  hooks ------ progress -- journal --- state           |
|                                                       |
|              Intelligence Layer                        |
|  diagnostics ---- drafts ---- stagnation              |
+----------+---------------+---------------+-----------+
| Tabular  | Deep Learning |  Fine-Tuning  |  Swarm    |
| Plugin   | Plugin        |  Plugin       |  Mode     |
|          |               |               |           |
| sklearn  | PyTorch/timm  |  peft/trl     | worktrees |
| XGBoost  | transformers  |  LoRA/QLoRA   | scoreboard|
| LightGBM |               |               | claims    |
| Optuna   |               |               |           |
+----------+---------------+---------------+-----------+
|              Templates (Jinja2)                        |
|  CLAUDE.md --- train.py --- experiments.md             |
+------------------------------------------------------+
```

---

## CLI Reference

```
mlforge <dataset> <goal> [options]
```

| Argument | Default | Description |
|---|---|---|
| `dataset` | *(required)* | Path to dataset (CSV or Parquet) |
| `goal` | *(required)* | What to predict or optimize |
| `--domain` | `tabular` | Plugin domain: `tabular`, `deeplearning`, `finetuning` |
| `--metric` | auto-detected | Metric to optimize |
| `--direction` | auto | Override metric direction: `minimize` or `maximize` |
| `--budget-minutes` | `60` | Time budget in minutes |
| `--budget-usd` | `5.0` | USD cost cap |
| `--budget-experiments` | `50` | Maximum experiment count |
| `--output-dir` | auto | Experiment output directory |
| `--resume` | -- | Resume a previous run |
| `--model` | -- | Claude model to use |
| `--custom-claude-md` | -- | Path to custom CLAUDE.md template |
| `--custom-frozen` | -- | Additional frozen files |
| `--custom-mutable` | -- | Additional mutable files |
| `--swarm` | `false` | Enable parallel swarm mode |
| `--n-agents` | `3` | Number of swarm agents |
| `--enable-drafts` | `false` | Multi-draft initial exploration |
| `--model-name` | -- | HuggingFace model name (fine-tuning) |

---

## Project Structure

```
src/mlforge/
  cli.py                 # CLI entry point
  config.py              # TOML-based configuration
  engine.py              # Core experiment loop
  scaffold.py            # Experiment directory scaffolding
  plugins.py             # Plugin protocol + registry
  state.py               # Session state tracking
  checkpoint.py          # Crash recovery / session resume
  git_ops.py             # Git operations (branch, commit, revert)
  guardrails.py          # Cost / time / disk safety limits
  profiler.py            # Dataset auto-profiling
  export.py              # Best model artifact export
  results.py             # JSONL experiment tracking
  journal.py             # Experiment journal
  retrospective.py       # Post-session summary report
  progress.py            # Live terminal progress display
  hooks.py               # Git hooks for frozen file protection
  intelligence/
    diagnostics.py       # Where does the model fail?
    drafts.py            # Multi-draft exploration
    stagnation.py        # Detect + branch on plateau
  tabular/               # Tabular ML plugin
  deeplearning/          # Deep learning plugin
  finetuning/            # Fine-tuning plugin
  swarm/                 # Multi-agent parallel mode
  templates/             # Jinja2 templates (CLAUDE.md, train.py, experiments.md)
```

---

## Documentation

- **[Getting Started](docs/getting-started.md)** -- Installation, first experiment, simple vs expert mode
- **[Tabular ML Guide](docs/tabular-guide.md)** -- Baselines, diagnostics, stagnation, model families
- **[Deep Learning Guide](docs/deep-learning-guide.md)** -- Image/text classification, GPU config
- **[Fine-Tuning Guide](docs/fine-tuning-guide.md)** -- LoRA/QLoRA, data format, memory planning
- **[Swarm Guide](docs/swarm-guide.md)** -- Parallel agents, scoreboard, budget splitting
- **[Configuration Reference](docs/configuration.md)** -- All CLI flags, config file, metrics

---

## Testing

```bash
uv run pytest -x -q          # 617+ tests
uv run pytest -v              # Verbose output
```

---

## Acknowledgments

This project builds on ideas from the **AI-for-science / autonomous-research** community:

| Project | Key Idea Borrowed |
|---|---|
| [autoresearch](https://github.com/karpathy/autoresearch) | "Point AI at a problem, let it research overnight" -- the founding inspiration |
| [AIDE](https://github.com/WecoAI/aideml) (WecoAI) | Multi-draft start, atomic improvements, frozen/mutable separation |
| [SELA](https://github.com/geekan/MetaGPT/tree/main/metagpt/ext/sela) (MetaGPT) | Stage-wise pipeline concept informing staged mutable zones |
| [AutoKaggle](https://github.com/multimodal-art-projection/AutoKaggle) (Alibaba) | Unit testing concept for ML pipelines |
| [ML-Agent](https://github.com/geekan/MetaGPT/tree/main/metagpt/ext/ai_ml_agent) (Shanghai AI Lab) | Domain-specific approaches outperform scale alone |
| [The AI Scientist](https://github.com/SakanaAI/AI-Scientist) (Sakana AI) | Full research lifecycle vision |
| [pi-autoresearch](https://github.com/JohnPaton/pi-autoresearch) (John Paton) | Checkpoint/resume patterns |
| [autoresearch-at-home](https://github.com/darien-schettler/autoresearch-at-home) (Darien Schettler) | Multi-agent coordination patterns |

---

## License

MIT
