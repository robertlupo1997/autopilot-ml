# Phase 5: Domain Plugins + Swarm - Research

**Researched:** 2026-03-19
**Domain:** Deep learning (PyTorch), LLM fine-tuning (PEFT/TRL), multi-agent swarm (git worktrees)
**Confidence:** MEDIUM

## Summary

Phase 5 extends mlforge from tabular-only to three domains (tabular, deep learning, LLM fine-tuning) and adds swarm mode for parallel agent exploration. The existing plugin architecture (`DomainPlugin` Protocol with `scaffold()`, `template_context()`, `validate_config()`) is well-designed for extension -- the DL and FT plugins follow the exact same pattern as `TabularPlugin`.

The deep learning plugin centers on PyTorch with `timm` for image classification and HuggingFace `transformers` for text classification. GPU management, LR scheduling, early stopping, and time-budgeted training are standard PyTorch patterns. The fine-tuning plugin uses HuggingFace's `peft` + `trl` (SFTTrainer) with `bitsandbytes` for QLoRA 4-bit quantization. Both plugins generate domain-specific CLAUDE.md protocols and frozen/mutable files through the existing template system.

Swarm mode reuses proven patterns from the old `automl.swarm` reference code: git worktrees for isolation, `fcntl.LOCK_EX` file-locked scoreboard, subprocess-spawned `claude -p` agents. The key new requirements are budget inheritance (parent splits budget across children) and a verification agent that re-runs holdout evaluation to check metric claims.

**Primary recommendation:** Build DL plugin first (simpler GPU story), then FT plugin (adds quantization complexity), then swarm mode (orthogonal to plugins, can test with any domain). Three plans.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DL-01 | DL plugin handles image/text classification with PyTorch | PyTorch + timm (image) + transformers (text) stack; DomainPlugin Protocol scaffold pattern |
| DL-02 | GPU utilization, memory limits, training time budgets | `torch.cuda` memory management, `torch.cuda.max_memory_allocated()`, timer-based epoch cutoff |
| DL-03 | LR scheduling, early stopping, gradient clipping as protocol rules | Standard PyTorch: `ReduceLROnPlateau`, patience-based early stopping, `clip_grad_norm_` |
| DL-04 | Domain-specific CLAUDE.md protocol generation | Jinja2 template with DL-specific rules via `template_context()` |
| DL-05 | Fixed time budget per training run | Timer check between epochs; `signal.alarm()` or wall-clock cutoff |
| FT-01 | LoRA/QLoRA fine-tuning via PEFT/TRL | `peft.LoraConfig` + `trl.SFTTrainer` with `BitsAndBytesConfig` |
| FT-02 | VRAM management, quantization config, LoRA rank/alpha | `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4")`, LoRA r=16/alpha=16 defaults |
| FT-03 | Evaluation metrics: perplexity, ROUGE, task-specific | `evaluate` library for ROUGE; cross-entropy loss for perplexity; custom eval callbacks |
| FT-04 | Domain-specific CLAUDE.md protocol | Jinja2 template with FT-specific rules (no full fine-tune, check VRAM, use chat templates) |
| FT-05 | Dataset formatting (chat templates, instruction format) | `tokenizer.apply_chat_template()`, SFTTrainer dataset formatting |
| SWARM-01 | Parallel agents in git worktrees | `git worktree add` via GitPython, subprocess.Popen for claude -p per worktree |
| SWARM-02 | File-locked scoreboard coordination | TSV scoreboard with `fcntl.LOCK_EX`, lockless reads (append-only safe) |
| SWARM-03 | Budget inheritance prevents spawn explosion | Parent config.budget_usd / n_agents = child budget; no recursive spawning |
| SWARM-04 | Verification agent checks metric claims | Separate agent re-runs holdout eval on best model, compares claimed vs actual metric |
</phase_requirements>

## Standard Stack

### Core (Deep Learning Plugin)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| torch | >=2.4 | DL framework | Industry standard; 2.6 is current stable |
| torchvision | >=0.19 | Image transforms, datasets | Tight PyTorch integration, standard augmentation |
| timm | >=1.0 | Pretrained image models | 1000+ models, transfer learning standard |
| transformers | >=4.45 | Text classification models | HuggingFace ecosystem standard |
| datasets | >=3.0 | HuggingFace dataset loading | Standard for text/NLP data |

### Core (Fine-tuning Plugin)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| peft | >=0.14 | LoRA/QLoRA adapters | HuggingFace official PEFT library |
| trl | >=0.14 | SFTTrainer for supervised fine-tuning | Simplifies PEFT+transformers integration |
| bitsandbytes | >=0.45 | 4-bit/8-bit quantization | Required for QLoRA, reduces VRAM 4-10x |
| evaluate | >=0.4 | ROUGE, perplexity metrics | HuggingFace metrics library |
| rouge-score | >=0.1 | ROUGE computation backend | Required by evaluate for ROUGE |

### Core (Swarm)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| (stdlib) | - | fcntl, subprocess, signal, json | No external deps for coordination |
| gitpython | >=3.1 | Already in deps; worktree support | Git worktree add/remove operations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| timm | torchvision only | timm has 10x more pretrained models; worth the dep |
| trl SFTTrainer | transformers Trainer + manual PEFT | SFTTrainer handles chat templates, packing, PEFT wiring automatically |
| bitsandbytes | GPTQ/AWQ | bitsandbytes is the only option for QLoRA training (GPTQ/AWQ are inference-only) |
| fcntl file locks | SQLite/Redis | Overkill; file locks are sufficient for 3-5 agents on one machine |
| evaluate library | Manual metric computation | evaluate handles tokenization, aggregation; worth the dep |

**Installation (new deps for Phase 5):**
```bash
# DL plugin deps (optional group)
pip install torch torchvision timm

# FT plugin deps (optional group)
pip install peft trl bitsandbytes evaluate rouge-score

# Swarm has no new deps (uses stdlib + existing gitpython)
```

**Important:** DL and FT deps should be optional dependency groups in pyproject.toml, not required. The base mlforge install should remain lightweight (tabular-only). Use `mlforge[dl]` and `mlforge[ft]` extras.

## Architecture Patterns

### Recommended Project Structure
```
src/mlforge/
  plugins.py              # DomainPlugin Protocol + registry (exists)
  tabular/                # Existing tabular plugin (reference)
    __init__.py           #   TabularPlugin class
    prepare.py            #   Frozen data pipeline
  deeplearning/           # NEW: Deep learning plugin
    __init__.py           #   DeepLearningPlugin class
    prepare.py            #   Frozen data loader (image/text)
    train_template.py     #   Template for mutable train.py
  finetuning/             # NEW: Fine-tuning plugin
    __init__.py           #   FineTuningPlugin class
    prepare.py            #   Frozen dataset formatter
    train_template.py     #   Template for mutable train.py
  swarm/                  # NEW: Swarm mode
    __init__.py           #   SwarmManager class
    scoreboard.py         #   File-locked TSV scoreboard
    claims.py             #   TTL-based experiment deduplication
    verifier.py           #   Verification agent logic
  templates/
    base_claude.md.j2     # Existing base template (works for all domains)
    dl_train.py.j2        # NEW: DL train.py template
    ft_train.py.j2        # NEW: FT train.py template
    swarm_claude.md.j2    # NEW: Swarm coordination protocol
```

### Pattern 1: Plugin Follows Existing Protocol
**What:** Each new plugin implements the same `DomainPlugin` Protocol -- `scaffold()`, `template_context()`, `validate_config()`.
**When to use:** Always. This is the established pattern from Phase 1.
**Example:**
```python
# Source: existing TabularPlugin pattern in src/mlforge/tabular/__init__.py
class DeepLearningPlugin:
    name: str = "deeplearning"
    frozen_files: list[str] = ["prepare.py"]

    def scaffold(self, target_dir: Path, config: Config) -> None:
        # Copy frozen prepare.py (data loading + augmentation)
        # Render mutable train.py from dl_train.py.j2 template
        ...

    def template_context(self, config: Config) -> dict:
        task = config.plugin_settings.get("task", "image_classification")
        rules = [
            "Use timm pretrained models for image classification",
            "Use transformers AutoModel for text classification",
            "Do not modify prepare.py -- it is frozen infrastructure",
            "train.py is the ONLY mutable file",
            "Check GPU memory before loading model: torch.cuda.mem_get_info()",
            "Use mixed precision (torch.amp) for memory efficiency",
            "Stop training when time budget expires (check wall clock between epochs)",
            "Use early stopping with patience=5 on validation loss",
            "Apply gradient clipping: torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)",
        ]
        return {"domain_rules": rules, "extra_sections": []}

    def validate_config(self, config: Config) -> list[str]:
        errors = []
        valid_metrics = {"accuracy", "f1", "f1_weighted", "loss"}
        if config.metric not in valid_metrics:
            errors.append(f"Unknown DL metric: {config.metric}")
        return errors
```

### Pattern 2: GPU Memory Guard in Frozen prepare.py
**What:** The DL/FT frozen prepare.py includes GPU detection and memory reporting.
**When to use:** Both DL and FT plugins.
**Example:**
```python
# In deeplearning/prepare.py (frozen)
import torch

def get_device_info() -> dict:
    """Report GPU availability and memory for agent context."""
    if not torch.cuda.is_available():
        return {"device": "cpu", "gpu_name": None, "vram_gb": 0}
    return {
        "device": "cuda",
        "gpu_name": torch.cuda.get_device_name(0),
        "vram_gb": torch.cuda.get_device_properties(0).total_mem / 1e9,
    }
```

### Pattern 3: Time-Budgeted Training Loop
**What:** Training stops after wall-clock budget expires, not after fixed epochs.
**When to use:** DL-05 requirement. Critical for overnight unattended runs.
**Example:**
```python
# In dl_train.py.j2 template (rendered to mutable train.py)
import time

TIME_BUDGET_SEC = {{ time_budget }}
start = time.time()

for epoch in range(MAX_EPOCHS):
    train_one_epoch(model, train_loader, optimizer, device)
    val_loss = evaluate(model, val_loader, device)

    # Time budget check
    elapsed = time.time() - start
    if elapsed > TIME_BUDGET_SEC:
        print(f"Time budget expired after {epoch+1} epochs ({elapsed:.0f}s)")
        break

    # Early stopping check
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        patience_counter = 0
        torch.save(model.state_dict(), "best_model.pt")
    else:
        patience_counter += 1
        if patience_counter >= PATIENCE:
            print(f"Early stopping after {epoch+1} epochs")
            break
```

### Pattern 4: Swarm Budget Inheritance
**What:** Parent splits its remaining budget across N child agents.
**When to use:** SWARM-03. Prevents spawn explosion.
**Example:**
```python
# SwarmManager.setup()
child_budget_usd = self.config.budget_usd / self.n_agents
child_budget_minutes = self.config.budget_minutes / self.n_agents
child_experiments = self.config.budget_experiments // self.n_agents

# Each worktree gets its own config with reduced budget
child_config = Config(
    budget_usd=child_budget_usd,
    budget_minutes=child_budget_minutes,
    budget_experiments=child_experiments,
    # ... inherit other settings
)
```

### Pattern 5: Verification Agent
**What:** After swarm completes, a verification agent re-runs evaluation on the best model.
**When to use:** SWARM-04. Catches overfitting or metric calculation bugs.
**Example:**
```python
# verifier.py
def verify_best_result(
    experiment_dir: Path,
    scoreboard: SwarmScoreboard,
    config: Config,
) -> dict:
    """Re-run holdout evaluation on the claimed best model."""
    best_score, best_agent = scoreboard.read_best()
    # Checkout best agent's commit
    # Run evaluation script (read-only, no training)
    # Compare claimed vs actual metric
    return {
        "claimed_metric": best_score,
        "verified_metric": actual_score,
        "match": abs(best_score - actual_score) < tolerance,
    }
```

### Anti-Patterns to Avoid
- **Requiring GPU for tests:** All DL/FT unit tests must work on CPU. Use `torch.device("cpu")` in test fixtures, mock `torch.cuda.is_available()` where needed.
- **Importing heavy deps at module level:** Use lazy imports for torch, transformers, peft. The base mlforge should import without these installed.
- **Nested agent spawning in swarm:** Children must NEVER spawn their own swarm. Budget inheritance config has `swarm_enabled=False` for child configs.
- **Hardcoding model names:** Plugin settings should parameterize model names (e.g., `timm_model: "resnet50"`, `hf_model: "meta-llama/Llama-3.1-8B"`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image augmentation pipeline | Custom transforms | torchvision.transforms / timm augmentation | Edge cases (dtype, normalization, resize modes) |
| LR scheduling | Manual LR decay | torch.optim.lr_scheduler | CosineAnnealing, ReduceLROnPlateau, OneCycleLR all battle-tested |
| LoRA injection | Manual weight freezing + low-rank layers | peft.LoraConfig + get_peft_model() | Handles target module selection, merging, saving |
| 4-bit quantization | Manual quantization code | bitsandbytes.BitsAndBytesConfig | NF4 quantization, double quantization, paged optimizers |
| Chat template formatting | String concatenation | tokenizer.apply_chat_template() | Handles model-specific special tokens, BOS/EOS |
| ROUGE computation | Regex-based n-gram matching | evaluate.load("rouge") | Handles tokenization, stemming, bootstrapping |
| File locking | Custom lock implementation | fcntl.flock(fd, LOCK_EX) | OS-level atomicity, well-tested on Linux |
| Git worktree management | Subprocess git commands | GitPython repo.git.worktree() | Already a dependency, handles cleanup |

**Key insight:** The DL and FT plugins are largely about correctly composing existing libraries (PyTorch, HuggingFace) rather than building novel functionality. The value is in the CLAUDE.md protocol rules and the frozen/mutable zone design.

## Common Pitfalls

### Pitfall 1: CUDA OOM During Model Loading
**What goes wrong:** Agent loads a model that exceeds GPU VRAM, Python process crashes.
**Why it happens:** No upfront check of model size vs available VRAM.
**How to avoid:** In frozen prepare.py, report `torch.cuda.mem_get_info()`. In CLAUDE.md protocol, include rule: "Check available VRAM before loading model. If model needs >80% of VRAM, use a smaller model or enable quantization."
**Warning signs:** `RuntimeError: CUDA out of memory` in train.py output.

### Pitfall 2: Lazy Import Failures
**What goes wrong:** `import torch` at module level in DL plugin causes ImportError when user only has tabular deps installed.
**Why it happens:** DL/FT deps are optional groups.
**How to avoid:** Import torch/transformers/peft inside methods, not at module level. Test with `mlforge[tabular]` only to verify no import chain pulls in heavy deps.
**Warning signs:** `ImportError: No module named 'torch'` when running `mlforge dataset.csv "predict price"`.

### Pitfall 3: Worktree Cleanup on Crash
**What goes wrong:** Crashed swarm agent leaves orphaned git worktree, subsequent runs fail with "worktree already exists".
**Why it happens:** No cleanup in finally block; agent subprocess killed without teardown.
**How to avoid:** SwarmManager.teardown() always runs in finally block. Uses `git worktree prune` as last resort. Register signal handlers for SIGINT/SIGTERM.
**Warning signs:** `fatal: '/path/.swarm/agent-0' is already a linked working tree`.

### Pitfall 4: Scoreboard Race Condition
**What goes wrong:** Two agents read scoreboard simultaneously, both think they have global best, both overwrite best_train.py.
**Why it happens:** Read-then-write without holding lock.
**How to avoid:** Hold `LOCK_EX` for the entire read-check-write-copy sequence in `publish_result()`. Lockless reads are fine for display purposes only.
**Warning signs:** best_train.py contents don't match the agent that claims global best.

### Pitfall 5: Fine-tuning Chat Template Mismatch
**What goes wrong:** Model produces garbage because training used wrong chat template.
**Why it happens:** Each model family (Llama, Mistral, Qwen) has different special tokens and template format.
**How to avoid:** Always use `tokenizer.apply_chat_template()` in the frozen prepare.py. Never hand-construct prompt strings. Include model-specific template in CLAUDE.md protocol.
**Warning signs:** High perplexity on evaluation set, model outputs special token text.

### Pitfall 6: fcntl Not Available on Windows
**What goes wrong:** `import fcntl` raises ImportError on Windows.
**Why it happens:** fcntl is Unix-only.
**How to avoid:** Use `msvcrt` on Windows or use a cross-platform lock library. However, given this project's Linux focus (WSL2 environment), fcntl is acceptable. Add a clear error message if someone tries on Windows.
**Warning signs:** `ModuleNotFoundError: No module named 'fcntl'` on Windows.

## Code Examples

### DL Plugin: Image Classification prepare.py Pattern
```python
# Source: Standard PyTorch/timm pattern
import torch
from pathlib import Path
from torchvision import datasets, transforms

def load_image_data(data_dir: str, img_size: int = 224, batch_size: int = 32):
    """Load image classification data with standard augmentation."""
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(img_size),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    val_transform = transforms.Compose([
        transforms.Resize(int(img_size * 1.14)),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    train_ds = datasets.ImageFolder(Path(data_dir) / "train", train_transform)
    val_ds = datasets.ImageFolder(Path(data_dir) / "val", val_transform)
    train_loader = torch.utils.data.DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = torch.utils.data.DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=2)
    return train_loader, val_loader, len(train_ds.classes)
```

### FT Plugin: QLoRA Config Pattern
```python
# Source: HuggingFace PEFT + bitsandbytes official docs
from peft import LoraConfig, get_peft_model, TaskType
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch

def load_model_for_finetuning(model_name: str, lora_r: int = 16, lora_alpha: int = 16):
    """Load a model with QLoRA 4-bit quantization and LoRA adapters."""
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules="all-linear",
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model
```

### Swarm: Budget Inheritance Pattern
```python
# Source: Project-specific design based on SWARM-03 requirement
from mlforge.config import Config

def create_child_configs(parent_config: Config, n_agents: int) -> list[Config]:
    """Split parent budget across N child agents."""
    return [
        Config(
            domain=parent_config.domain,
            metric=parent_config.metric,
            direction=parent_config.direction,
            budget_minutes=parent_config.budget_minutes // n_agents,
            budget_experiments=parent_config.budget_experiments // n_agents,
            budget_usd=parent_config.budget_usd / n_agents,
            per_experiment_timeout_sec=parent_config.per_experiment_timeout_sec,
            per_experiment_budget_usd=parent_config.per_experiment_budget_usd,
            max_turns_per_experiment=parent_config.max_turns_per_experiment,
            model=parent_config.model,
            frozen_files=parent_config.frozen_files,
            mutable_files=parent_config.mutable_files,
            plugin_settings=parent_config.plugin_settings,
        )
        for _ in range(n_agents)
    ]
```

### Scoreboard: File-Locked Write Pattern
```python
# Source: Adapted from old automl.swarm_scoreboard (reference)
import fcntl
from pathlib import Path

HEADER = "agent\tcommit\tmetric_value\telapsed_sec\tstatus\tdescription\ttimestamp\n"

def publish_result(scoreboard_path: Path, lock_path: Path, row: str) -> bool:
    """Atomic publish with LOCK_EX for the full read-check-write cycle."""
    with open(lock_path, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            if not scoreboard_path.exists():
                scoreboard_path.write_text(HEADER)
            current_best = _read_best(scoreboard_path)  # read while holding lock
            with open(scoreboard_path, "a") as f:
                f.write(row + "\n")
            new_score = float(row.split("\t")[2])
            return current_best is None or new_score > current_best
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual LoRA weight freezing | `peft.get_peft_model()` auto-injection | PEFT 0.6+ (2024) | No manual layer surgery |
| `Trainer` + manual PEFT setup | `SFTTrainer` (TRL) handles everything | TRL 0.7+ (2024) | 50% less boilerplate for fine-tuning |
| Full 16-bit fine-tuning | QLoRA 4-bit via bitsandbytes | 2023-present | 4-10x VRAM reduction |
| `torchvision.models` only | timm ecosystem (1000+ models) | timm 1.0 (2024) | Much broader model selection |
| torch.nn.DataParallel | torch.nn.parallel.DistributedDataParallel | Deprecated since PyTorch 1.x | DataParallel is single-process, slow |
| Custom training loops | PyTorch 2.0 `torch.compile()` | PyTorch 2.0+ (2023) | 10-30% speedup on supported models |

**Deprecated/outdated:**
- `torch.nn.DataParallel`: Use DDP or FSDP instead (but single-GPU is fine for mlforge's scope)
- `transformers.Trainer` for fine-tuning with PEFT: Use `trl.SFTTrainer` instead (handles PEFT natively)
- Manual 8-bit quantization: Use `bitsandbytes.BitsAndBytesConfig` with 4-bit NF4

## Open Questions

1. **Dataset format detection for DL plugin**
   - What we know: Image classification uses folder structure (train/val/class_name/), text classification uses CSV/JSON with text+label columns
   - What's unclear: Should the CLI auto-detect image vs text task, or require `--task image_classification`?
   - Recommendation: Require explicit `--domain deeplearning --task image_classification` in v1; auto-detection is a v2 feature

2. **GPU availability as hard requirement vs graceful fallback**
   - What we know: DL and FT are impractical without GPU for real experiments
   - What's unclear: Should plugins refuse to run on CPU, or allow it with a warning?
   - Recommendation: Allow CPU with warning. Tests must work on CPU. Real experiments will be slow but functional.

3. **Model download caching**
   - What we know: timm and HuggingFace cache models in ~/.cache/. First run downloads can be GBs.
   - What's unclear: Should mlforge manage cache, or leave it to the libraries?
   - Recommendation: Leave to libraries. Add CLAUDE.md rule: "Models are cached in ~/.cache/huggingface/. First run may be slow due to downloads."

4. **Swarm agent count default**
   - What we know: Old automl capped at len(ALGORITHM_FAMILIES). The current mlforge has 5 tabular families.
   - What's unclear: Optimal default for DL/FT where "families" are less clear-cut.
   - Recommendation: Default n_agents=3, cap at number of available families for domain. User can override via `--swarm-agents N`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `python -m pytest tests/mlforge/ -x -q` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DL-01 | DL plugin scaffolds image/text classification | unit | `pytest tests/mlforge/test_deeplearning.py -x` | No - Wave 0 |
| DL-02 | GPU info reported, memory limits respected | unit | `pytest tests/mlforge/test_deeplearning.py::test_gpu_management -x` | No - Wave 0 |
| DL-03 | LR scheduling + early stopping in template | unit | `pytest tests/mlforge/test_deeplearning.py::test_training_features -x` | No - Wave 0 |
| DL-04 | DL CLAUDE.md protocol generated | unit | `pytest tests/mlforge/test_deeplearning.py::test_template_context -x` | No - Wave 0 |
| DL-05 | Time budget enforced | unit | `pytest tests/mlforge/test_deeplearning.py::test_time_budget -x` | No - Wave 0 |
| FT-01 | FT plugin scaffolds LoRA/QLoRA | unit | `pytest tests/mlforge/test_finetuning.py -x` | No - Wave 0 |
| FT-02 | VRAM management, quantization config | unit | `pytest tests/mlforge/test_finetuning.py::test_quantization_config -x` | No - Wave 0 |
| FT-03 | Perplexity + ROUGE evaluation | unit | `pytest tests/mlforge/test_finetuning.py::test_eval_metrics -x` | No - Wave 0 |
| FT-04 | FT CLAUDE.md protocol generated | unit | `pytest tests/mlforge/test_finetuning.py::test_template_context -x` | No - Wave 0 |
| FT-05 | Dataset formatting with chat templates | unit | `pytest tests/mlforge/test_finetuning.py::test_dataset_formatting -x` | No - Wave 0 |
| SWARM-01 | Worktree creation + agent spawning | unit | `pytest tests/mlforge/test_swarm.py::test_worktree_setup -x` | No - Wave 0 |
| SWARM-02 | Scoreboard file-locked writes | unit | `pytest tests/mlforge/test_scoreboard.py -x` | No - Wave 0 |
| SWARM-03 | Budget inheritance math | unit | `pytest tests/mlforge/test_swarm.py::test_budget_inheritance -x` | No - Wave 0 |
| SWARM-04 | Verification agent checks claims | unit | `pytest tests/mlforge/test_swarm.py::test_verifier -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/mlforge/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/mlforge/test_deeplearning.py` -- covers DL-01 through DL-05
- [ ] `tests/mlforge/test_finetuning.py` -- covers FT-01 through FT-05
- [ ] `tests/mlforge/test_swarm.py` -- covers SWARM-01, SWARM-03, SWARM-04
- [ ] `tests/mlforge/test_scoreboard.py` -- covers SWARM-02

## Sources

### Primary (HIGH confidence)
- Existing mlforge codebase: `src/mlforge/plugins.py`, `src/mlforge/tabular/__init__.py` (plugin Protocol and reference implementation)
- Existing old automl codebase: `src/automl/swarm.py`, `src/automl/swarm_scoreboard.py`, `src/automl/swarm_claims.py` (proven swarm patterns)

### Secondary (MEDIUM confidence)
- [HuggingFace PEFT docs](https://huggingface.co/docs/peft) - LoRA/QLoRA configuration and API
- [TRL SFTTrainer docs](https://huggingface.co/docs/trl/index) - Supervised fine-tuning trainer
- [How to fine-tune open LLMs in 2025](https://www.philschmid.de/fine-tune-llms-in-2025) - Current stack recommendations
- [PyTorch 2.6 Release](https://pytorch.org/blog/pytorch2-6/) - Latest PyTorch features
- [timm on HuggingFace](https://huggingface.co/timm) - PyTorch Image Models ecosystem
- [bitsandbytes GitHub](https://github.com/bitsandbytes-foundation/bitsandbytes) - 4-bit quantization
- [HuggingFace evaluate](https://huggingface.co/spaces/evaluate-metric/rouge) - ROUGE metrics

### Tertiary (LOW confidence)
- WebSearch results for git worktree agent patterns - community practices, not official docs
- WebSearch results for GPU memory management patterns - multiple sources, not one authoritative

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - Library versions verified via PyPI/GitHub releases; API patterns verified via official docs and blog posts
- Architecture: HIGH - Plugin pattern is proven in existing codebase; swarm pattern is proven in old automl code
- Pitfalls: MEDIUM - Based on known PyTorch/HuggingFace gotchas and project experience; some may be stale

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (30 days - libraries are stable; HuggingFace releases frequently but APIs are stable)
