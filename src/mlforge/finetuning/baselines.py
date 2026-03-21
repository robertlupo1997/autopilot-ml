"""Baseline computation for fine-tuning domains.

Computes theoretical loss and perplexity baselines using vocabulary size.
No torch or transformers imports -- uses only math.
"""

from __future__ import annotations

import math


def compute_baselines(
    metric: str = "loss",
    vocab_size: int = 32000,
) -> dict[str, dict[str, float]]:
    """Compute theoretical baselines for fine-tuning tasks.

    For loss: random_guess = log(vocab_size), untrained_model = 0.8 * log(vocab_size).
    For perplexity: random_guess = vocab_size, untrained_model = 0.8 * vocab_size.

    Args:
        metric: Metric name ('loss', 'perplexity').
        vocab_size: Vocabulary size (default 32000).

    Returns:
        Dict mapping strategy name to dict with 'score' and 'std'.
    """
    if metric == "perplexity":
        random_guess = float(vocab_size)
        untrained = 0.8 * float(vocab_size)
    else:
        # Default to loss (cross-entropy)
        random_guess = math.log(vocab_size)
        untrained = 0.8 * math.log(vocab_size)

    return {
        "random_guess": {"score": random_guess, "std": 0.0},
        "untrained_model": {"score": untrained, "std": 0.0},
    }
