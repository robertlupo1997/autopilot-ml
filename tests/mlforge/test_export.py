"""Tests for mlforge.export -- artifact export after session."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mlforge.config import Config
from mlforge.state import SessionState


class TestExportArtifact:
    """export_artifact packages best model + metadata."""

    def test_returns_artifacts_dir_when_model_exists(self, tmp_path: Path) -> None:
        from mlforge.export import export_artifact

        (tmp_path / "best_model.joblib").write_bytes(b"fake-model-data")
        state = SessionState(
            best_metric=0.92, best_commit="abc1234", experiment_count=5, cost_spent_usd=1.50
        )
        config = Config(metric="accuracy", direction="maximize")

        result = export_artifact(tmp_path, state, config)
        assert result is not None
        assert result == tmp_path / "artifacts"
        assert result.is_dir()

    def test_returns_none_when_no_model(self, tmp_path: Path) -> None:
        from mlforge.export import export_artifact

        state = SessionState()
        config = Config()

        result = export_artifact(tmp_path, state, config)
        assert result is None

    def test_metadata_json_contains_required_fields(self, tmp_path: Path) -> None:
        from mlforge.export import export_artifact

        (tmp_path / "best_model.joblib").write_bytes(b"fake-model-data")
        state = SessionState(
            best_metric=0.92, best_commit="abc1234", experiment_count=5, cost_spent_usd=1.50
        )
        config = Config(metric="accuracy", direction="maximize")

        export_artifact(tmp_path, state, config)

        metadata_path = tmp_path / "artifacts" / "metadata.json"
        assert metadata_path.exists()
        metadata = json.loads(metadata_path.read_text())
        assert metadata["metric_name"] == "accuracy"
        assert metadata["metric_value"] == 0.92
        assert metadata["metric_direction"] == "maximize"
        assert metadata["best_commit"] == "abc1234"
        assert metadata["experiment_count"] == 5
        assert metadata["total_cost_usd"] == 1.50
        assert "exported_at" in metadata

    def test_model_is_copied_not_moved(self, tmp_path: Path) -> None:
        from mlforge.export import export_artifact

        model_path = tmp_path / "best_model.joblib"
        model_path.write_bytes(b"fake-model-data")
        state = SessionState(best_metric=0.9, best_commit="abc1234", experiment_count=1)
        config = Config()

        export_artifact(tmp_path, state, config)

        # Original still exists
        assert model_path.exists()
        # Copy exists in artifacts
        assert (tmp_path / "artifacts" / "best_model.joblib").exists()
        assert (tmp_path / "artifacts" / "best_model.joblib").read_bytes() == b"fake-model-data"

    def test_artifacts_dir_created_if_not_exists(self, tmp_path: Path) -> None:
        from mlforge.export import export_artifact

        (tmp_path / "best_model.joblib").write_bytes(b"fake-model-data")
        state = SessionState(best_metric=0.9, best_commit="abc1234", experiment_count=1)
        config = Config()

        assert not (tmp_path / "artifacts").exists()
        export_artifact(tmp_path, state, config)
        assert (tmp_path / "artifacts").is_dir()

    def test_export_artifact_pt_file(self, tmp_path: Path) -> None:
        """export_artifact finds best_model.pt when .joblib absent."""
        from mlforge.export import export_artifact

        (tmp_path / "best_model.pt").write_bytes(b"fake-pt-data")
        state = SessionState(best_metric=0.85, best_commit="def5678", experiment_count=3)
        config = Config(metric="accuracy", direction="maximize")

        result = export_artifact(tmp_path, state, config)
        assert result is not None
        assert (result / "best_model.pt").exists()
        assert (result / "best_model.pt").read_bytes() == b"fake-pt-data"

    def test_export_artifact_adapter_dir(self, tmp_path: Path) -> None:
        """export_artifact copies best_adapter/ directory when .joblib and .pt absent."""
        from mlforge.export import export_artifact

        adapter_dir = tmp_path / "best_adapter"
        adapter_dir.mkdir()
        (adapter_dir / "adapter_model.bin").write_bytes(b"adapter-data")
        (adapter_dir / "adapter_config.json").write_text('{"r": 16}')

        state = SessionState(best_metric=0.88, best_commit="ghi9012", experiment_count=2)
        config = Config(metric="f1", direction="maximize")

        result = export_artifact(tmp_path, state, config)
        assert result is not None
        exported_adapter = result / "best_adapter"
        assert exported_adapter.is_dir()
        assert (exported_adapter / "adapter_model.bin").read_bytes() == b"adapter-data"
        assert (exported_adapter / "adapter_config.json").read_text() == '{"r": 16}'

    def test_export_artifact_priority_order(self, tmp_path: Path) -> None:
        """When both .joblib and .pt exist, .joblib wins (first match)."""
        from mlforge.export import export_artifact

        (tmp_path / "best_model.joblib").write_bytes(b"joblib-data")
        (tmp_path / "best_model.pt").write_bytes(b"pt-data")

        state = SessionState(best_metric=0.9, best_commit="abc1234", experiment_count=1)
        config = Config()

        result = export_artifact(tmp_path, state, config)
        assert result is not None
        assert (result / "best_model.joblib").exists()
        # .pt should NOT be exported (first match wins)
        assert not (result / "best_model.pt").exists()
