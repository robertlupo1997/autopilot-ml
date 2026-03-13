"""Tests for scripts/parse_run_result.py -- extracts fields from claude -p JSON output.

STRUCT-02: Automated extraction of stop_reason, num_turns, total_cost_usd, is_error
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "parse_run_result.py"


def load_parse_run_result():
    """Import parse_run_result function from scripts/parse_run_result.py using importlib."""
    spec = importlib.util.spec_from_file_location("parse_run_result", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.parse_run_result


class TestParseRunResult:
    """Unit tests for parse_run_result function."""

    def test_parse_full_result(self, tmp_path):
        """Given JSON with all fields, returns dict with correct values."""
        data = {
            "stop_reason": "end_turn",
            "num_turns": 15,
            "total_cost_usd": 0.25,
            "is_error": False,
        }
        json_file = tmp_path / "output.json"
        json_file.write_text(json.dumps(data))

        parse_run_result = load_parse_run_result()
        result = parse_run_result(str(json_file))

        assert result["stop_reason"] == "end_turn"
        assert result["num_turns"] == 15
        assert result["total_cost_usd"] == 0.25
        assert result["is_error"] is False

    def test_parse_missing_fields(self, tmp_path):
        """Given JSON missing some fields, returns None for missing keys (no KeyError)."""
        data = {"stop_reason": "max_turns"}
        json_file = tmp_path / "partial.json"
        json_file.write_text(json.dumps(data))

        parse_run_result = load_parse_run_result()
        result = parse_run_result(str(json_file))

        assert result["stop_reason"] == "max_turns"
        assert result["num_turns"] is None
        assert result["total_cost_usd"] is None
        assert result["is_error"] is None

    def test_parse_empty_object(self, tmp_path):
        """Given '{}', returns dict with all keys set to None."""
        json_file = tmp_path / "empty.json"
        json_file.write_text("{}")

        parse_run_result = load_parse_run_result()
        result = parse_run_result(str(json_file))

        assert result["stop_reason"] is None
        assert result["num_turns"] is None
        assert result["total_cost_usd"] is None
        assert result["is_error"] is None

    def test_parse_real_structure(self, tmp_path):
        """Given realistic claude -p output with nested data, extracts correct top-level fields."""
        data = {
            "stop_reason": "end_turn",
            "num_turns": 30,
            "total_cost_usd": 0.45,
            "is_error": False,
            "result": "Experiment complete. Best model: RandomForest accuracy=0.94",
            "session_id": "abc123",
            "messages": [
                {"role": "user", "content": "Run experiment"},
                {"role": "assistant", "content": "Done."},
            ],
        }
        json_file = tmp_path / "realistic.json"
        json_file.write_text(json.dumps(data))

        parse_run_result = load_parse_run_result()
        result = parse_run_result(str(json_file))

        assert result["stop_reason"] == "end_turn"
        assert result["num_turns"] == 30
        assert result["total_cost_usd"] == 0.45
        assert result["is_error"] is False

    def test_cli_stdout(self, tmp_path):
        """Running script via CLI prints key: value lines to stdout."""
        data = {
            "stop_reason": "end_turn",
            "num_turns": 10,
            "total_cost_usd": 0.10,
            "is_error": False,
        }
        json_file = tmp_path / "cli_test.json"
        json_file.write_text(json.dumps(data))

        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), str(json_file)],
            capture_output=True,
            text=True,
        )

        assert proc.returncode == 0
        assert "stop_reason:" in proc.stdout
        assert "num_turns:" in proc.stdout
        assert "total_cost_usd:" in proc.stdout
        assert "is_error:" in proc.stdout
