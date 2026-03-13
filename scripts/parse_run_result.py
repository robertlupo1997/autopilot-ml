#!/usr/bin/env python3
"""Parse the outer claude -p --output-format json result file.

Usage: python3 scripts/parse_run_result.py <path-to-output.json>

Extracts stop_reason, num_turns, total_cost_usd, is_error from the JSON
output produced by `claude -p --output-format json`.
"""
import json
import sys


def parse_run_result(path: str) -> dict:
    """Parse claude -p JSON output file and return key fields.

    Returns dict with keys: stop_reason, num_turns, total_cost_usd, is_error.
    Missing fields default to None.
    """
    with open(path) as f:
        data = json.load(f)
    return {
        "stop_reason": data.get("stop_reason"),
        "num_turns": data.get("num_turns"),
        "total_cost_usd": data.get("total_cost_usd"),
        "is_error": data.get("is_error"),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/parse_run_result.py <path-to-output.json>", file=sys.stderr)
        sys.exit(1)
    result = parse_run_result(sys.argv[1])
    for k, v in result.items():
        print(f"{k}: {v}")
