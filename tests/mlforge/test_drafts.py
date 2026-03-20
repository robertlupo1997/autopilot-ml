"""Tests for multi-draft generation and selection."""

from __future__ import annotations

import pytest

from mlforge.intelligence.drafts import ALGORITHM_FAMILIES, DraftResult, select_best_draft


class TestAlgorithmFamilies:
    def test_has_required_keys(self):
        for key in ("linear", "random_forest", "xgboost", "lightgbm"):
            assert key in ALGORITHM_FAMILIES, f"Missing family: {key}"

    def test_entries_have_description(self):
        for name, entry in ALGORITHM_FAMILIES.items():
            assert "description" in entry, f"{name} missing description"


class TestDraftResult:
    def test_dataclass_fields(self):
        dr = DraftResult(
            name="linear",
            metric_value=0.85,
            status="draft-keep",
            commit_hash="abc1234",
            description="Linear baseline",
        )
        assert dr.name == "linear"
        assert dr.metric_value == 0.85
        assert dr.status == "draft-keep"
        assert dr.commit_hash == "abc1234"
        assert dr.description == "Linear baseline"

    def test_metric_value_none(self):
        dr = DraftResult(
            name="xgb", metric_value=None, status="draft-discard",
            commit_hash="", description="Failed",
        )
        assert dr.metric_value is None


class TestSelectBestDraft:
    def test_maximize(self):
        results = [
            DraftResult("a", 0.7, "draft-keep", "h1", "A"),
            DraftResult("b", 0.9, "draft-keep", "h2", "B"),
            DraftResult("c", 0.8, "draft-keep", "h3", "C"),
        ]
        best = select_best_draft(results, direction="maximize")
        assert best is not None
        assert best.name == "b"

    def test_minimize(self):
        results = [
            DraftResult("a", 0.7, "draft-keep", "h1", "A"),
            DraftResult("b", 0.9, "draft-keep", "h2", "B"),
            DraftResult("c", 0.3, "draft-keep", "h3", "C"),
        ]
        best = select_best_draft(results, direction="minimize")
        assert best is not None
        assert best.name == "c"

    def test_all_none_metrics(self):
        results = [
            DraftResult("a", None, "draft-discard", "", "A"),
            DraftResult("b", None, "draft-discard", "", "B"),
        ]
        assert select_best_draft(results) is None

    def test_mixed_none(self):
        results = [
            DraftResult("a", None, "draft-discard", "", "A"),
            DraftResult("b", 0.5, "draft-keep", "h1", "B"),
            DraftResult("c", None, "draft-discard", "", "C"),
        ]
        best = select_best_draft(results, direction="maximize")
        assert best is not None
        assert best.name == "b"

    def test_empty_list(self):
        assert select_best_draft([]) is None
