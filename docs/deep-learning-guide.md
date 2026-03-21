# Deep Learning Domain Guide

PyTorch-based training for image classification and text classification. Uses [timm](https://github.com/huggingface/pytorch-image-models) for vision models and [transformers](https://huggingface.co/docs/transformers) for NLP.

## Installation

```bash
uv sync --extra dl
```

This adds: `torch`, `torchvision`, `timm`, `transformers`, `datasets`.

## Usage

```bash
# Image classification
mlforge images/ "classify dog breeds" --domain deeplearning

# Text classification with a specific metric
mlforge text_data.csv "sentiment analysis" --domain deeplearning --metric f1
```

## Valid Tasks and Metrics

| Tasks                  | Metrics                          |
|------------------------|----------------------------------|
| `image_classification` | `accuracy`, `f1`, `f1_weighted`  |
| `text_classification`  | `accuracy`, `f1`, `f1_weighted`  |
| `custom`               | `loss`                           |

## Scaffolded Files

- **prepare.py** (FROZEN) -- GPU detection, data loading, VRAM reporting.
- **train.py** (MUTABLE) -- PyTorch training loop template. The Claude Code agent iterates on this file.

## Protocol Rules

Enforced by the scaffolded `CLAUDE.md`:

1. **Use timm for image models, transformers for text.** Don't hand-roll architectures when a pretrained backbone exists.
2. **Check GPU memory before loading a model.** `prepare.py` writes VRAM info; the agent must choose a model that fits.
3. **Mixed precision is required.** Use `torch.amp` (autocast + GradScaler) for all training runs.
4. **Early stopping with patience=5.** Track validation loss each epoch and stop when it hasn't improved for 5 consecutive epochs.
5. **Gradient clipping.** Call `torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)` every training step.
6. **Required outputs.** Every run must produce `predictions.csv` and `best_model.pt`.

## Multi-Draft Mode

With `--enable-drafts`, the agent creates 3 diverse initial solutions:

| Draft | Family        | Typical first model        |
|-------|---------------|----------------------------|
| 1     | ResNet        | `resnet50`                 |
| 2     | ViT           | `vit_small_patch16_224`    |
| 3     | EfficientNet  | `efficientnet_b0`          |

## Output

```
artifacts/
  best_model.pt      # PyTorch state dict
  metadata.json       # Model name, metric value, training config, timestamp
  predictions.csv     # Test-set predictions
```

## Example: End-to-End Image Classification

```bash
# 1. Organize images by class:
#    images/golden_retriever/001.jpg
#    images/labrador/001.jpg

# 2. Run mlforge
mlforge images/ "classify dog breeds" --domain deeplearning --metric accuracy

# 3. Inspect results
cat artifacts/metadata.json
```

The agent selects a pretrained backbone from timm, fine-tunes it on your data, applies early stopping, and exports the best checkpoint.
