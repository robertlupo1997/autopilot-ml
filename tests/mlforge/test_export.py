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
