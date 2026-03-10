"""Unit tests for ExperimentLogger -- TSV logging and run.log management."""

import os

import pytest

from automl.experiment_logger import ExperimentLogger, HEADER


@pytest.fixture
def logger(tmp_path):
    """Create an ExperimentLogger pointing at a temp directory."""
    return ExperimentLogger(experiment_dir=str(tmp_path))


class TestInitResults:
    def test_init_creates_header(self, tmp_path, logger):
        logger.init_results()
        results_path = tmp_path / "results.tsv"
        assert results_path.exists()
        content = results_path.read_text()
        assert content == "commit\tmetric_value\tmemory_mb\telapsed_sec\tstatus\tdescription\n"

    def test_init_idempotent(self, tmp_path, logger):
        logger.init_results()
        logger.init_results()
        content = (tmp_path / "results.tsv").read_text()
        # Should have exactly one header line, not two
        lines = content.strip().split("\n")
        assert len(lines) == 1
        assert lines[0].startswith("commit")


class TestLogResult:
    def test_log_result_appends(self, tmp_path, logger):
        logger.init_results()
        logger.log_result("abc1234", 0.95, 128.5, 3.2, "keep", "first run")
        logger.log_result("def5678", 0.87, 256.0, 5.1, "discard", "second run")
        content = (tmp_path / "results.tsv").read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3  # header + 2 data rows

    def test_tsv_format(self, tmp_path, logger):
        logger.init_results()
        logger.log_result("abc1234", 0.95, 128.5, 3.2, "keep", "first run")
        content = (tmp_path / "results.tsv").read_text()
        data_line = content.strip().split("\n")[1]
        fields = data_line.split("\t")
        assert len(fields) == 6

    def test_append_only(self, tmp_path, logger):
        logger.init_results()
        logger.log_result("abc1234", 0.95, 128.5, 3.2, "keep", "first run")
        first_content = (tmp_path / "results.tsv").read_text()
        logger.log_result("def5678", 0.87, 256.0, 5.1, "discard", "second run")
        second_content = (tmp_path / "results.tsv").read_text()
        # Second content should start with first content (append, not overwrite)
        assert second_content.startswith(first_content)

    def test_log_fields(self, tmp_path, logger):
        logger.init_results()
        logger.log_result("abc1234", 0.954321, 128.5, 3.2, "keep", "test desc")
        content = (tmp_path / "results.tsv").read_text()
        data_line = content.strip().split("\n")[1]
        fields = data_line.split("\t")
        assert fields[0] == "abc1234"
        assert fields[1] == "0.954321"  # 6 decimal places
        assert fields[2] == "128.5"     # 1 decimal place
        assert fields[3] == "3.2"       # 1 decimal place
        assert fields[4] == "keep"
        assert fields[5] == "test desc"


class TestRunLog:
    def test_write_run_log(self, tmp_path, logger):
        logger.write_run_log("stdout output", "stderr output")
        run_log = tmp_path / "run.log"
        assert run_log.exists()
        content = run_log.read_text()
        assert "stdout output" in content
        assert "stderr output" in content

    def test_run_log_overwritten(self, tmp_path, logger):
        logger.write_run_log("first output", "")
        logger.write_run_log("second output", "")
        content = (tmp_path / "run.log").read_text()
        assert "second output" in content
        assert "first output" not in content
