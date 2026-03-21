# Configuration Reference

All configuration surfaces in mlforge: CLI flags, the generated config file, supported metrics, and custom template overrides.

## CLI Flags

```bash
mlforge <dataset> <goal> [OPTIONS]
```

### Positional Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `dataset` | path | Path to the dataset file (CSV or Parquet). Required. |
| `goal` | string | What to predict or optimize, in plain English. Required. |

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--domain` | string | `tabular` | Plugin domain: `tabular`, `deeplearning`, `finetuning` |
| `--metric` | string | auto | Primary metric to optimize. See [Metrics by Domain](#metrics-by-domain). |
| `--direction` | choice | auto | `minimize` or `maximize`. Auto-detected from metric when omitted. |
| `--budget-minutes` | int | `60` | Wall-clock time budget in minutes. |
| `--budget-usd` | float | `5.0` | Maximum USD to spend on Claude API calls. |
| `--budget-experiments` | int | `50` | Maximum number of experiments to run. |
| `--output-dir` | string | auto | Directory for experiment artifacts. |
| `--resume` | flag | `false` | Resume a previous run from checkpoint. |
| `--model` | string | None | Override the Claude model (e.g., `claude-sonnet-4-20250514`). |
| `--custom-claude-md` | path | None | Path to a custom CLAUDE.md Jinja2 template. |
| `--custom-frozen` | list | None | Additional frozen files. May be specified multiple times. |
| `--custom-mutable` | list | None | Additional mutable files. May be specified multiple times. |
| `--swarm` | flag | `false` | Enable swarm mode with parallel agents in git worktrees. |
| `--n-agents` | int | `3` | Number of parallel agents in swarm mode. |
| `--enable-drafts` | flag | `false` | Multi-draft exploration (3-5 diverse initial solutions). |
| `--model-name` | string | None | HuggingFace model identifier for fine-tuning domain. |

## Config File

When mlforge scaffolds an experiment, it generates `mlforge.config.toml`. This records the resolved configuration and can be manually edited before using `--resume`.

```toml
[mlforge]
domain = "tabular"
metric = "f1"
direction = "maximize"
budget_minutes = 60
budget_usd = 5.0
budget_experiments = 50
per_experiment_timeout_sec = 300
per_experiment_budget_usd = 1.0
max_turns_per_experiment = 30
stagnation_threshold = 3
enable_drafts = false
frozen_files = ["prepare.py"]
mutable_files = ["train.py"]

[mlforge.plugin_settings]
dataset_path = "data.csv"
target_column = "price"
task = "regression"
```

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `per_experiment_timeout_sec` | 300 | Max seconds per experiment subprocess |
| `per_experiment_budget_usd` | 1.0 | Max USD cost per single experiment |
| `max_turns_per_experiment` | 30 | Max Claude turns within one experiment |
| `stagnation_threshold` | 3 | Consecutive reverts before branching to new model family |
| `frozen_files` | `["prepare.py"]` | Files the agent cannot modify |
| `mutable_files` | `["train.py"]` | Files the agent can edit |

## Metrics by Domain

### Tabular

| Metric | Direction | Task |
|--------|-----------|------|
| `accuracy` | maximize | classification |
| `auc` | maximize | binary classification |
| `roc_auc` | maximize | binary classification |
| `f1` | maximize | classification |
| `f1_weighted` | maximize | multiclass classification |
| `precision` | maximize | classification |
| `recall` | maximize | classification |
| `log_loss` | minimize | classification |
| `rmse` | minimize | regression |
| `mae` | minimize | regression |
| `mse` | minimize | regression |
| `r2` | maximize | regression |

### Deep Learning

| Metric | Direction |
|--------|-----------|
| `accuracy` | maximize |
| `f1` | maximize |
| `f1_weighted` | maximize |
| `loss` | minimize |

### Fine-Tuning

| Metric | Direction |
|--------|-----------|
| `perplexity` | minimize |
| `rouge1` | maximize |
| `rouge2` | maximize |
| `rougeL` | maximize |
| `loss` | minimize |

## Direction Auto-Detection

When `--direction` is omitted, mlforge infers it from the metric:

- **Maximize**: accuracy, auc, roc_auc, f1, f1_weighted, precision, recall, r2, rouge1, rouge2, rougeL
- **Minimize**: rmse, mae, mse, log_loss, loss, perplexity

If you use a custom metric name that mlforge doesn't recognize, specify `--direction` explicitly.

## Custom CLAUDE.md Templates

Use `--custom-claude-md` to override the built-in protocol template. Templates are rendered with Jinja2 and have access to:

| Variable | Type | Description |
|----------|------|-------------|
| `domain` | string | Active domain name |
| `metric_name` | string | Primary metric |
| `metric_direction` | string | `minimize` or `maximize` |
| `frozen_files` | list[string] | Files the agent must not modify |
| `mutable_files` | list[string] | Files the agent may edit |

Example:

```markdown
# Experiment Protocol

You are optimizing **{{ metric_name }}** ({{ metric_direction }}).

You may edit: {{ mutable_files | join(", ") }}
Do NOT edit: {{ frozen_files | join(", ") }}
```

```bash
mlforge data.csv "predict churn" --custom-claude-md ./my_protocol.md.j2
```
