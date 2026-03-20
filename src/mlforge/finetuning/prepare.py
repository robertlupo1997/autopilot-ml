"""Frozen dataset pipeline for LLM fine-tuning.

Provides VRAM detection, dataset formatting with chat templates,
and train/eval splitting. This module is copied as-is into the
experiment directory -- the agent MUST NOT modify it.
"""

from __future__ import annotations


def format_dataset(
    data_path,
    tokenizer_name,
    max_length=512,
    format="instruction",
):
    """Load and format dataset for fine-tuning.

    Placeholder -- full implementation in Task 2.
    """
    raise NotImplementedError("Full implementation in Task 2")


def get_vram_info():
    """Return VRAM information for the current system.

    Placeholder -- full implementation in Task 2.
    """
    raise NotImplementedError("Full implementation in Task 2")


def create_train_eval_split(dataset, eval_fraction=0.1):
    """Split dataset into train and eval portions.

    Placeholder -- full implementation in Task 2.
    """
    raise NotImplementedError("Full implementation in Task 2")
