"""Tests for Jinja2 template rendering."""

from __future__ import annotations

import pytest

from mlforge.config import Config
from mlforge.templates import get_template_env, render_claude_md, render_experiments_md


# Re-use the mock plugin from test_plugins
from tests.mlforge.test_plugins import MockTabularPlugin


class TestTemplateEnv:
    """Verify Jinja2 environment setup."""

    def test_template_env_loads(self):
        env = get_template_env()
        template = env.get_template("base_claude.md.j2")
        assert template is not None

    def test_template_env_loads_experiments(self):
        env = get_template_env()
        template = env.get_template("base_experiments.md.j2")
        assert template is not None


class TestRenderClaudeMd:
    """Verify CLAUDE.md rendering with plugin context."""

    @pytest.fixture()
    def plugin(self):
        return MockTabularPlugin()

    @pytest.fixture()
    def config(self):
        return Config(
            domain="tabular",
            metric="accuracy",
            direction="maximize",
            frozen_files=["prepare.py"],
            mutable_files=["train.py"],
        )

    def test_render_claude_md_contains_domain(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "tabular" in output

    def test_render_claude_md_contains_metric(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "accuracy" in output
        assert "maximize" in output

    def test_render_claude_md_contains_frozen_files(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "prepare.py" in output

    def test_render_claude_md_contains_mutable_files(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "train.py" in output

    def test_render_claude_md_contains_domain_rules(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "Use scikit-learn for modeling" in output
        assert "Do not modify prepare.py" in output

    def test_render_claude_md_has_header(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "# CLAUDE.md" in output


class TestTabularTrainJsonOutput:
    """Verify tabular_train.py.j2 renders JSON metric output."""

    def test_tabular_train_renders_json_output(self):
        env = get_template_env()
        template = env.get_template("tabular_train.py.j2")
        output = template.render(
            csv_path="data.csv",
            target_column="target",
            metric="accuracy",
            time_budget=5,
            task="classification",
            date_column=None,
        )
        assert "json.dumps" in output
        assert "metric_value" in output
        assert 'print(f"Best value:' not in output

    def test_tabular_train_imports_json(self):
        env = get_template_env()
        template = env.get_template("tabular_train.py.j2")
        output = template.render(
            csv_path="data.csv",
            target_column="target",
            metric="accuracy",
            time_budget=5,
            task="classification",
            date_column=None,
        )
        assert "import json" in output


class TestClaudeMdOutputFormat:
    """Verify CLAUDE.md contains output format section."""

    @pytest.fixture()
    def plugin(self):
        return MockTabularPlugin()

    @pytest.fixture()
    def config(self):
        return Config(
            domain="tabular",
            metric="accuracy",
            direction="maximize",
            frozen_files=["prepare.py"],
            mutable_files=["train.py"],
        )

    def test_claude_md_contains_output_format(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "Output Format" in output
        assert "metric_value" in output

    def test_claude_md_contains_revert_warning(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "revert" in output.lower()


class TestTabularTrainArtifacts:
    """Verify tabular_train.py.j2 renders predictions.csv and best_model.joblib writes."""

    def _render(self, task: str = "classification") -> str:
        env = get_template_env()
        template = env.get_template("tabular_train.py.j2")
        return template.render(
            csv_path="data.csv",
            target_column="target",
            metric="accuracy" if task == "classification" else "r2",
            time_budget=5,
            task=task,
            date_column=None,
        )

    def test_classification_imports_joblib(self):
        output = self._render("classification")
        assert "import joblib" in output

    def test_classification_predictions_csv_with_columns(self):
        output = self._render("classification")
        assert "predictions.csv" in output
        assert '"y_true"' in output
        assert '"y_pred"' in output

    def test_classification_saves_model(self):
        output = self._render("classification")
        assert "joblib.dump" in output
        assert "best_model.joblib" in output

    def test_regression_predictions_csv_with_columns(self):
        output = self._render("regression")
        assert "predictions.csv" in output
        assert '"y_true"' in output
        assert '"y_pred"' in output

    def test_regression_saves_model(self):
        output = self._render("regression")
        assert "joblib.dump" in output
        assert "best_model.joblib" in output

    def test_json_output_after_artifact_writes(self):
        """JSON output must be the last line -- after predictions and model save."""
        output = self._render("classification")
        predictions_pos = output.index("predictions.csv")
        joblib_pos = output.index("joblib.dump")
        json_pos = output.index("json.dumps")
        assert json_pos > predictions_pos
        assert json_pos > joblib_pos

    def test_regression_json_output_after_artifact_writes(self):
        output = self._render("regression")
        predictions_pos = output.index("predictions.csv")
        joblib_pos = output.index("joblib.dump")
        json_pos = output.index("json.dumps")
        assert json_pos > predictions_pos
        assert json_pos > joblib_pos


class TestClaudeMdArtifactRule:
    """Verify CLAUDE.md contains artifact preservation rule."""

    @pytest.fixture()
    def plugin(self):
        from mlforge.tabular import TabularPlugin
        return TabularPlugin()

    @pytest.fixture()
    def config(self):
        return Config(
            domain="tabular",
            metric="accuracy",
            direction="maximize",
            frozen_files=["prepare.py"],
            mutable_files=["train.py"],
        )

    def test_claude_md_mentions_predictions_csv(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "predictions.csv" in output

    def test_claude_md_mentions_best_model_joblib(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "best_model.joblib" in output

    def test_claude_md_mentions_diagnostics_or_export(self, plugin, config):
        output = render_claude_md(plugin, config)
        assert "diagnostics" in output.lower() or "export" in output.lower()


class TestDLTrainArtifacts:
    """Verify dl_train.py.j2 renders predictions.csv write."""

    def _render(self, task: str = "image_classification") -> str:
        env = get_template_env()
        template = env.get_template("dl_train.py.j2")
        return template.render(
            task=task,
            data_dir="data",
            data_path="data.csv",
            metric="accuracy",
            time_budget=300,
            img_size=224,
            batch_size=32,
            model_name="resnet50",
        )

    def test_dl_template_writes_predictions(self):
        output = self._render()
        assert "predictions.csv" in output

    def test_dl_template_cpu_numpy(self):
        output = self._render()
        assert ".cpu().numpy()" in output

    def test_dl_template_text_writes_predictions(self):
        output = self._render("text_classification")
        assert "predictions.csv" in output

    def test_dl_template_json_after_predictions(self):
        output = self._render()
        predictions_pos = output.index("predictions.csv")
        json_pos = output.index("json.dumps(result)")
        assert json_pos > predictions_pos


class TestFTTrainArtifacts:
    """Verify ft_train.py.j2 renders predictions.csv write."""

    def _render(self) -> str:
        env = get_template_env()
        template = env.get_template("ft_train.py.j2")
        return template.render(
            model_name="meta-llama/Llama-3.2-1B",
            lora_r=16,
            lora_alpha=16,
            metric="perplexity",
            max_length=512,
            batch_size=4,
            learning_rate=2e-4,
            num_epochs=3,
            dataset_format="instruction",
        )

    def test_ft_template_writes_predictions(self):
        output = self._render()
        assert "predictions.csv" in output

    def test_ft_template_predictions_guarded(self):
        output = self._render()
        assert 'METRIC in ("perplexity", "loss")' in output

    def test_ft_template_json_after_predictions(self):
        output = self._render()
        predictions_pos = output.index("predictions.csv")
        json_pos = output.index("json.dumps(result)")
        assert json_pos > predictions_pos


class TestDLTemplateContextArtifactRule:
    """Verify DL plugin template_context includes artifact preservation rule."""

    def test_dl_template_context_artifact_rule(self):
        from mlforge.deeplearning import DeepLearningPlugin
        plugin = DeepLearningPlugin()
        config = Config(domain="deeplearning", metric="accuracy", direction="maximize")
        ctx = plugin.template_context(config)
        rules_text = " ".join(ctx["domain_rules"])
        assert "predictions.csv" in rules_text
        assert "best_model.pt" in rules_text


class TestFTTemplateContextArtifactRule:
    """Verify FT plugin template_context includes artifact preservation rule."""

    def test_ft_template_context_artifact_rule(self):
        from mlforge.finetuning import FineTuningPlugin
        plugin = FineTuningPlugin()
        config = Config(
            domain="finetuning", metric="perplexity", direction="minimize",
            plugin_settings={"model_name": "test-model"},
        )
        ctx = plugin.template_context(config)
        rules_text = " ".join(ctx["domain_rules"])
        assert "predictions.csv" in rules_text
        assert "best_adapter" in rules_text


class TestRenderExperimentsMd:
    """Verify experiments.md rendering."""

    def test_render_experiments_md_contains_header(self):
        config = Config(
            domain="tabular",
            metric="accuracy",
            direction="maximize",
            budget_experiments=50,
            budget_minutes=60,
        )
        output = render_experiments_md(config, run_id="run-001")
        assert "run-001" in output
        assert "accuracy" in output
        assert "maximize" in output

    def test_render_experiments_md_contains_table_header(self):
        config = Config()
        output = render_experiments_md(config, run_id="run-002")
        assert "| # |" in output
        assert "Status" in output
