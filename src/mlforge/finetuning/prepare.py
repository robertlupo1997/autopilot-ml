"""Frozen dataset pipeline for LLM fine-tuning.

Provides VRAM detection, dataset formatting with chat templates,
and train/eval splitting. This module is copied as-is into the
experiment directory -- the agent MUST NOT modify it.

NOTE: This file uses module-level transformers imports, but it is a
standalone file copied during scaffold -- never imported by mlforge core.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any


def get_vram_info() -> dict[str, Any]:
    """Return VRAM information for the current system.

    Detects GPU availability via torch.cuda. If no GPU is available,
    returns CPU fallback with recommend_quantization=True.

    Returns:
        Dict with keys: device, gpu_name, vram_gb, recommend_quantization.
    """
    import torch

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        props = torch.cuda.get_device_properties(0)
        vram_gb = props.total_mem / (1024**3)
        return {
            "device": "cuda",
            "gpu_name": gpu_name,
            "vram_gb": round(vram_gb, 1),
            "recommend_quantization": vram_gb < 16,
        }
    return {
        "device": "cpu",
        "gpu_name": None,
        "vram_gb": 0.0,
        "recommend_quantization": True,
    }


def create_train_eval_split(
    dataset: list,
    eval_fraction: float = 0.1,
    seed: int = 42,
) -> tuple[list, list]:
    """Split dataset into train and eval portions.

    Uses a fixed random seed for reproducibility.

    Args:
        dataset: List of data items to split.
        eval_fraction: Fraction of data for evaluation (default 0.1).
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (train_items, eval_items).
    """
    rng = random.Random(seed)
    indices = list(range(len(dataset)))
    rng.shuffle(indices)

    eval_size = int(len(dataset) * eval_fraction)
    eval_indices = set(indices[:eval_size])

    train = [dataset[i] for i in range(len(dataset)) if i not in eval_indices]
    eval_ = [dataset[i] for i in range(len(dataset)) if i in eval_indices]

    return train, eval_


def _load_data(data_path: str) -> list[dict]:
    """Load data from JSON, JSONL, or CSV file.

    Args:
        data_path: Path to the data file.

    Returns:
        List of dicts, one per row/record.
    """
    path = Path(data_path)
    suffix = path.suffix.lower()

    if suffix == ".json":
        with open(path) as f:
            return json.load(f)
    elif suffix == ".jsonl":
        records = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
    elif suffix == ".csv":
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)
    else:
        msg = f"Unsupported file format: {suffix}. Use .json, .jsonl, or .csv"
        raise ValueError(msg)


def _format_as_chat(record: dict, tokenizer: Any) -> str:
    """Format a single record as a chat message using tokenizer.apply_chat_template().

    Args:
        record: Dict with 'instruction' and 'output' keys.
        tokenizer: HuggingFace tokenizer with apply_chat_template method.

    Returns:
        Formatted chat string.
    """
    messages = [
        {"role": "user", "content": record.get("instruction", "")},
        {"role": "assistant", "content": record.get("output", "")},
    ]
    return tokenizer.apply_chat_template(messages, tokenize=False)


def format_dataset(
    data_path: str,
    tokenizer_name: str,
    max_length: int = 512,
    format: str = "instruction",
) -> dict[str, Any]:
    """Load and format dataset for fine-tuning.

    Loads JSON/JSONL/CSV data, applies tokenizer chat template formatting,
    and creates a train/eval split.

    Args:
        data_path: Path to data file (.json, .jsonl, .csv).
        tokenizer_name: HuggingFace model/tokenizer name.
        max_length: Maximum sequence length for tokenization.
        format: Dataset format ('instruction' for instruction/output pairs).

    Returns:
        Dict with 'train' (list), 'eval' (list), and 'num_samples' (int).
    """
    from transformers import AutoTokenizer

    # Load raw data
    records = _load_data(data_path)

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Format each record
    formatted = []
    for record in records:
        text = _format_as_chat(record, tokenizer)
        formatted.append({"text": text, "original": record})

    # Split into train/eval
    train, eval_ = create_train_eval_split(formatted)

    return {
        "train": train,
        "eval": eval_,
        "num_samples": len(formatted),
    }
