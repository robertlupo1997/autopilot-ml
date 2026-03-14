#!/usr/bin/env bash
# =============================================================================
# run-swarm-test.sh
# Phase 10: Multi-Agent Swarm -- Smoke test for 2-agent swarm mode
#
# IMPORTANT: Must be run from a terminal OUTSIDE of Claude Code.
# Claude Code cannot launch 'claude -p' inside another Claude Code session.
# If you are currently in a Claude Code terminal session, open a NEW terminal
# and run this script from there.
#
# Usage:
#   cd /home/tlupo/AutoML
#   ./scripts/run-swarm-test.sh
#
# What it does:
#   1. Pre-flight checks (noisy.csv, uv, claude CLI)
#   2. Scaffolds experiment from noisy.csv
#   3. Runs a 2-agent swarm (each agent explores different algorithm families)
#   4. Checks .swarm/scoreboard.tsv for results
#   5. Cleans up temporary directories
#
# Expected runtime: several minutes per agent (50 turns max each).
# Requires: ANTHROPIC_API_KEY set in environment and API credits available.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_DIR=$(mktemp -d)
FIXTURE="$PROJECT_ROOT/tests/fixtures/noisy.csv"
EXPERIMENT_NAME="experiment-swarm-smoke"
EXPERIMENT_DIR="$TEST_DIR/$EXPERIMENT_NAME"

echo "============================================================"
echo "  AutoML Phase 10: Multi-Agent Swarm Smoke Test"
echo "  Project root : $PROJECT_ROOT"
echo "  Test dir     : $TEST_DIR"
echo "  Dataset      : noisy.csv (300 rows, 10 features, 10% label noise)"
echo "  Agents       : 2"
echo "  Max turns/agent: 50"
echo "============================================================"
echo ""
echo "NOTE: This script must be run OUTSIDE of a Claude Code session."
echo "      'claude -p' cannot be launched inside another CC session."
echo "      If you see an error about nested sessions, open a new terminal."
echo ""

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
echo "[1/4] Pre-flight checks..."

if [ ! -f "$FIXTURE" ]; then
    echo "ERROR: noisy.csv not found at $FIXTURE"
    echo "       Run from AutoML project root to generate it:"
    echo "         uv run python3 -c \"from sklearn.datasets import make_classification; import pandas as pd; X, y = make_classification(n_samples=300, n_features=10, n_informative=5, n_redundant=3, flip_y=0.10, random_state=42); df = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(10)]); df['target'] = y; df.to_csv('tests/fixtures/noisy.csv', index=False)\""
    rm -rf "$TEST_DIR"
    exit 1
fi
echo "  OK: noisy.csv found at $FIXTURE"

if command -v uv &> /dev/null; then
    echo "  OK: uv is available ($(uv --version))"
else
    echo "ERROR: 'uv' is not installed or not in PATH"
    rm -rf "$TEST_DIR"
    exit 1
fi

if command -v claude &> /dev/null; then
    echo "  OK: claude is available ($(claude --version 2>&1 | head -1))"
else
    echo "ERROR: 'claude' CLI is not installed or not in PATH"
    rm -rf "$TEST_DIR"
    exit 1
fi

# Check we are NOT inside a Claude Code session
if [ -n "${CLAUDECODE:-}" ]; then
    echo ""
    echo "ERROR: You are running this script inside a Claude Code session."
    echo "       'claude -p' cannot be launched inside another CC session."
    echo "       Please open a NEW terminal outside of Claude Code and run:"
    echo "         cd $PROJECT_ROOT && ./scripts/run-swarm-test.sh"
    rm -rf "$TEST_DIR"
    exit 1
fi

echo "  OK: Not inside Claude Code session"

# ---------------------------------------------------------------------------
# Run 2-agent swarm (scaffold + swarm in one CLI call)
# ---------------------------------------------------------------------------
echo ""
echo "[2/4] Running 2-agent swarm (scaffold + spawn agents)..."
echo "      This will scaffold the experiment then spawn 2 parallel claude -p agents."
echo "      Each agent explores different algorithm families."
echo "      Press Ctrl+C to stop early."
echo ""

cd "$PROJECT_ROOT"
uv run automl "$FIXTURE" target accuracy \
    --goal "Swarm smoke test: binary classification on noisy synthetic dataset" \
    --output-dir "$EXPERIMENT_DIR" \
    --time-budget 60 \
    --agents 2 || true

# ---------------------------------------------------------------------------
# Check results
# ---------------------------------------------------------------------------
echo ""
echo "[3/4] Checking results..."

SWARM_DIR="$EXPERIMENT_DIR/.swarm"
if [ -d "$SWARM_DIR" ]; then
    echo "  OK: .swarm directory exists at $SWARM_DIR"

    if [ -f "$SWARM_DIR/scoreboard.tsv" ]; then
        ROWS=$(tail -n +2 "$SWARM_DIR/scoreboard.tsv" | wc -l)
        echo "  OK: scoreboard.tsv found with $ROWS experiment row(s)"
        echo ""
        echo "--- scoreboard.tsv contents ---"
        cat "$SWARM_DIR/scoreboard.tsv"
        echo "-------------------------------"
    else
        echo "  WARN: scoreboard.tsv not found (agents may not have completed any experiments)"
        echo "        This can happen if agents ran out of turns before completing an experiment."
    fi

    if [ -f "$SWARM_DIR/config.json" ]; then
        echo "  OK: config.json found"
        cat "$SWARM_DIR/config.json"
    fi
else
    echo "  WARN: .swarm directory not found at $SWARM_DIR"
    echo "        Swarm may have failed to initialize. Check output above for errors."
fi

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
echo ""
echo "[4/4] Cleaning up $TEST_DIR..."
rm -rf "$TEST_DIR"
echo "  OK: Test directory removed"

echo ""
echo "============================================================"
echo "  Swarm Smoke Test Complete"
echo "============================================================"
echo ""
echo "NEXT STEPS:"
echo "  - If scoreboard.tsv had rows: swarm coordination is working."
echo "  - If agents ran 0 experiments: increase --time-budget or check API credits."
echo "  - For a real run: uv run automl data.csv target metric --agents N"
echo "    (run from a terminal outside of Claude Code)"
echo "============================================================"
