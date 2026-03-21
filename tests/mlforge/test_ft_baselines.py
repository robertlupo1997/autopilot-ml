"""Tests for fine-tuning baseline computation."""

from __future__ import annotations

import math

import pytest


class TestFTComputeBaselinesLoss:
    """FT compute_baselines returns theoretical bounds for loss."""

    def test_loss_returns_random_guess_and_untrained_model(self):
        from mlforge.finetuning.baselines import compute_baselines

        result = compute_baselines(metric="loss")
        assert "random_guess" in result
        assert "untrained_model" in result

    def test_loss_random_guess_is_log_vocab_size(self):
        from mlforge.finetuning.baselines import compute_baselines

        result = compute_baselines(metric="loss")
        expected = math.log(32000)
        assert abs(result["random_guess"]["score"] - expected) < 1e-6

    def test_loss_untrained_model_is_80_percent(self):
        from mlforge.finetuning.baselines import compute_baselines

        result = compute_baselines(metric="loss")
        expected = 0.8 * math.log(32000)
        assert abs(result["untrained_model"]["score"] - expected) < 1e-6

    def test_loss_baselines_have_score_and_std(self):
        from mlforge.finetuning.baselines import compute_baselines

        result = compute_baselines(metric="loss")
        for entry in result.values():
            assert "score" in entry
            assert "std" in entry
            assert isinstance(entry["score"], float)
            assert isinstance(entry["std"], float)


class TestFTComputeBaselinesPerplexity:
    """FT compute_baselines returns theoretical bounds for perplexity."""

    def test_perplexity_returns_random_guess_and_untrained_model(self):
        from mlforge.finetuning.baselines import compute_baselines

        result = compute_baselines(metric="perplexity")
        assert "random_guess" in result
        assert "untrained_model" in result

    def test_perplexity_random_guess_equals_vocab_size(self):
        from mlforge.finetuning.baselines import compute_baselines

        result = compute_baselines(metric="perplexity")
        assert result["random_guess"]["score"] == 32000.0

    def test_perplexity_untrained_model_is_80_percent(self):
        from mlforge.finetuning.baselines import compute_baselines

        result = compute_baselines(metric="perplexity")
        assert result["untrained_model"]["score"] == 0.8 * 32000.0


class TestFTComputeBaselinesCustomVocab:
    """FT compute_baselines respects custom vocab_size."""

    def test_custom_vocab_size_loss(self):
        from mlforge.finetuning.baselines import compute_baselines

        result = compute_baselines(metric="loss", vocab_size=50257)
        expected = math.log(50257)
        assert abs(result["random_guess"]["score"] - expected) < 1e-6

    def test_custom_vocab_size_perplexity(self):
        from mlforge.finetuning.baselines import compute_baselines

        result = compute_baselines(metric="perplexity", vocab_size=50257)
        assert result["random_guess"]["score"] == 50257.0
        assert result["untrained_model"]["score"] == 0.8 * 50257.0
