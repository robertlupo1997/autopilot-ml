"""Tests for multi-draft generation and selection."""

from __future__ import annotations

from mlforge.intelligence.drafts import (
    ALGORITHM_FAMILIES,
    DraftResult,
    get_families_for_domain,
    select_best_draft,
)


class TestAlgorithmFamilies:
    """Tests for the domain-keyed ALGORITHM_FAMILIES structure."""

    def test_has_domain_keys(self):
        for domain in ("tabular", "deeplearning", "finetuning"):
            assert domain in ALGORITHM_FAMILIES, f"Missing domain: {domain}"

    def test_tabular_has_required_families(self):
        tabular = ALGORITHM_FAMILIES["tabular"]
        for key in ("linear", "random_forest", "xgboost", "lightgbm", "svm"):
            assert key in tabular, f"Missing tabular family: {key}"

    def test_tabular_entries_have_description(self):
        for name, entry in ALGORITHM_FAMILIES["tabular"].items():
            assert "description" in entry, f"{name} missing description"

    def test_dl_entries_have_description(self):
        for name, entry in ALGORITHM_FAMILIES["deeplearning"].items():
            assert "description" in entry, f"{name} missing description"

    def test_ft_entries_have_description(self):
        for name, entry in ALGORITHM_FAMILIES["finetuning"].items():
            assert "description" in entry, f"{name} missing description"


class TestGetFamiliesForDomain:
    """Tests for domain-aware family lookup."""

    def test_tabular_returns_tabular_families(self):
        families = get_families_for_domain("tabular")
        assert set(families.keys()) == {"linear", "random_forest", "xgboost", "lightgbm", "svm"}

    def test_deeplearning_returns_dl_families(self):
        families = get_families_for_domain("deeplearning")
        assert set(families.keys()) == {"resnet", "vit", "efficientnet"}

    def test_finetuning_returns_ft_families(self):
        families = get_families_for_domain("finetuning")
        assert set(families.keys()) == {"qlora_r8", "qlora_r16", "qlora_r32", "lora_full"}

    def test_unknown_domain_falls_back_to_tabular(self):
        families = get_families_for_domain("unknown_domain")
        assert set(families.keys()) == {"linear", "random_forest", "xgboost", "lightgbm", "svm"}

    def test_dl_families_have_image_classification(self):
        families = get_families_for_domain("deeplearning")
        for name, entry in families.items():
            assert "image_classification" in entry, f"DL family {name} missing image_classification"

    def test_dl_resnet_model_class(self):
        families = get_families_for_domain("deeplearning")
        assert families["resnet"]["image_classification"] == "resnet50"

    def test_dl_vit_model_class(self):
        families = get_families_for_domain("deeplearning")
        assert families["vit"]["image_classification"] == "vit_base_patch16_224"

    def test_dl_efficientnet_model_class(self):
        families = get_families_for_domain("deeplearning")
        assert families["efficientnet"]["image_classification"] == "efficientnet_b0"

    def test_ft_families_have_sft(self):
        families = get_families_for_domain("finetuning")
        for name, entry in families.items():
            assert "sft" in entry, f"FT family {name} missing sft task key"

    def test_ft_qlora_r8_config(self):
        families = get_families_for_domain("finetuning")
        assert families["qlora_r8"]["sft"] == "QLoRA r=8 alpha=8"

    def test_ft_lora_full_config(self):
        families = get_families_for_domain("finetuning")
        assert families["lora_full"]["sft"] == "LoRA r=16 alpha=16 (no quantization)"


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
