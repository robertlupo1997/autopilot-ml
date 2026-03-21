# LLM Fine-Tuning Domain Guide

LoRA and QLoRA fine-tuning of open-source LLMs (Llama, Mistral, and others) using [peft](https://huggingface.co/docs/peft) and [trl](https://huggingface.co/docs/trl).

## Installation

```bash
uv sync --extra ft
```

This adds: `peft`, `trl`, `bitsandbytes`, `evaluate`, `rouge-score`, `transformers`, `datasets`.

## Usage

```bash
# Chat fine-tuning with Llama
mlforge train.jsonl "fine-tune for chat" \
  --domain finetuning \
  --model-name meta-llama/Llama-3.2-1B

# QA fine-tuning with Mistral, optimizing for ROUGE-L
mlforge qa_data.csv "improve QA" \
  --domain finetuning \
  --model-name mistralai/Mistral-7B-v0.3 \
  --metric rougeL
```

The `--model-name` flag is **required** for the fine-tuning domain.

## Valid Task and Metrics

| Task | Metrics |
|------|---------|
| `sft` (Supervised Fine-Tuning) | `perplexity`, `rouge1`, `rouge2`, `rougeL`, `loss` |

## Scaffolded Files

- **prepare.py** (FROZEN) -- Dataset formatting (converts CSV/JSONL to chat format), VRAM detection, quantization config selection.
- **train.py** (MUTABLE) -- LoRA/QLoRA training loop using `SFTTrainer`.

## Protocol Rules

Enforced by the scaffolded `CLAUDE.md`:

1. **NEVER full fine-tune.** Use LoRA or QLoRA exclusively.
2. **4-bit quantization when VRAM is limited.** If `prepare.py` reports less than 16 GB VRAM, use QLoRA (4-bit NormalFloat via `bitsandbytes`).
3. **Always apply chat templates.** Call `tokenizer.apply_chat_template()` to format inputs.
4. **Save adapters only.** Call `model.save_pretrained()` to save LoRA adapter weights, not the full merged model.
5. **Use SFTTrainer from trl.** Don't write a custom training loop.
6. **Enable gradient checkpointing.** Required for 7B+ models.
7. **Required outputs.** Every run must produce `predictions.csv` and a `best_adapter/` directory.

## Multi-Draft Mode

With `--enable-drafts`, the agent creates up to 4 diverse initial solutions:

| Draft | Configuration | Rank | Notes |
|-------|--------------|------|-------|
| 1 | QLoRA r=8 | 8 | Lowest memory, fastest |
| 2 | QLoRA r=16 | 16 | Balanced |
| 3 | QLoRA r=32 | 32 | Higher capacity, more memory |
| 4 | LoRA full (16-bit) | 16 | No quantization, needs more VRAM |

## Data Format

**JSONL (recommended):**

```json
{"messages": [{"role": "user", "content": "What is MLOps?"}, {"role": "assistant", "content": "MLOps is..."}]}
```

**CSV:**

```
input,output
"What is MLOps?","MLOps is..."
```

`prepare.py` converts CSV rows into chat-formatted messages automatically.

## Output

```
artifacts/
  best_adapter/           # LoRA adapter weights (adapter_config.json + adapter_model.safetensors)
  predictions.csv         # Sample generations on the eval set
  metadata.json           # Model name, metric value, LoRA config, timestamp
```

To load the adapter for inference:

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.2-1B")
model = PeftModel.from_pretrained(base, "artifacts/best_adapter")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-1B")
```

## Memory Planning

| Model size | VRAM needed (QLoRA 4-bit) | VRAM needed (LoRA 16-bit) |
|------------|---------------------------|---------------------------|
| 1B | ~3 GB | ~5 GB |
| 3B | ~6 GB | ~12 GB |
| 7B | ~10 GB | ~20 GB |
| 13B | ~18 GB | ~35 GB |

`prepare.py` detects available VRAM and writes it to the workspace so the agent can select the right quantization strategy.
