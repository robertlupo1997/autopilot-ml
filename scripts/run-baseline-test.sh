#!/usr/bin/env bash
# =============================================================================
# run-baseline-test.sh
# Phase 4: E2E Baseline Test -- Run the autonomous ML loop on the iris dataset
#
# IMPORTANT: Run this script from a terminal OUTSIDE of Claude Code.
# Claude Code cannot launch 'claude -p' inside another Claude Code session.
# If you are currently in a Claude Code terminal session, open a NEW terminal
# and run this script from there.
#
# Usage:
#   cd /home/tlupo/AutoML
#   ./scripts/run-baseline-test.sh
#
# Expected runtime: 2-5 minutes (capped at $2.00 budget).
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXPERIMENT_DIR="$PROJECT_ROOT/experiment-iris"
IRIS_CSV="$PROJECT_ROOT/tests/fixtures/iris.csv"

echo "============================================================"
echo "  AutoML Phase 4: E2E Baseline Test"
echo "  Project root : $PROJECT_ROOT"
echo "  Experiment   : $EXPERIMENT_DIR"
echo "============================================================"
echo ""
echo "NOTE: This script must be run OUTSIDE of a Claude Code session."
echo "      'claude -p' cannot be launched inside another CC session."
echo "      If you see an error about nested sessions, open a new terminal."
echo ""

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
echo "[1/8] Pre-flight checks..."

if [ ! -f "$IRIS_CSV" ]; then
    echo "ERROR: iris.csv not found at $IRIS_CSV"
    echo "       Run: uv run python -c \"from sklearn.datasets import load_iris; ...\" to generate it."
    exit 1
fi

if command -v uv &> /dev/null; then
    echo "  OK: uv is available ($(uv --version))"
else
    echo "ERROR: 'uv' is not installed or not in PATH"
    exit 1
fi

if command -v claude &> /dev/null; then
    echo "  OK: claude is available ($(claude --version 2>&1 | head -1))"
else
    echo "ERROR: 'claude' CLI is not installed or not in PATH"
    exit 1
fi

# Check we are NOT inside a Claude Code session
if [ -n "${CLAUDECODE:-}" ]; then
    echo ""
    echo "ERROR: You are running this script inside a Claude Code session."
    echo "       'claude -p' cannot be launched inside another CC session."
    echo "       Please open a NEW terminal outside of Claude Code and run:"
    echo "         cd $PROJECT_ROOT && ./scripts/run-baseline-test.sh"
    exit 1
fi

# ---------------------------------------------------------------------------
# Clean up any previous experiment directory
# ---------------------------------------------------------------------------
echo "[2/8] Preparing experiment directory..."

if [ -d "$EXPERIMENT_DIR" ]; then
    echo "  Removing existing $EXPERIMENT_DIR..."
    rm -rf "$EXPERIMENT_DIR"
fi

# ---------------------------------------------------------------------------
# Scaffold the experiment using the AutoML CLI
# ---------------------------------------------------------------------------
echo "[3/8] Scaffolding experiment with 'uv run automl'..."

cd "$PROJECT_ROOT"
uv run automl "$IRIS_CSV" species accuracy \
    --goal "Classify iris species (0=setosa, 1=versicolor, 2=virginica)"

if [ ! -d "$EXPERIMENT_DIR" ]; then
    echo "ERROR: Expected experiment directory not created: $EXPERIMENT_DIR"
    echo "       The scaffold command may have failed or created a different directory."
    exit 1
fi
echo "  OK: Experiment scaffolded at $EXPERIMENT_DIR"

# ---------------------------------------------------------------------------
# Install dependencies in experiment directory
# ---------------------------------------------------------------------------
echo "[4/8] Installing experiment dependencies (uv sync)..."

cd "$EXPERIMENT_DIR"
uv sync
echo "  OK: Dependencies installed"

# ---------------------------------------------------------------------------
# Initialize git repository
# ---------------------------------------------------------------------------
echo "[5/8] Initializing git repository..."

git init
git add .
git commit -m "initial scaffold"
echo "  OK: Git repository initialized with initial commit"

# ---------------------------------------------------------------------------
# Run the autonomous ML loop via claude -p
# ---------------------------------------------------------------------------
echo "[6/8] Running autonomous ML loop (this may take 2-5 minutes)..."
echo "      Max turns: 30 | Budget cap: \$2.00"
echo "      Output: $EXPERIMENT_DIR/baseline-run-output.json"
echo ""

# OBSERVATION CHECKLIST (for manual review after the run):
#   - Did 3-5 drafts run? Were they different algorithm families?
#   - Was best draft selected and checked out?
#   - Did git commits happen on keep? Did reset happen on revert?
#   - Did 'grep "^metric_value:"' reliably return a float?
#   - Is results.tsv being written? Correct format?
#   - Was run.log captured? No context flooding?
#   - Did agent touch prepare.py? (should be NO)
#   - Did stagnation trigger strategy shift? (may not trigger in 30 turns)
#   - If a crash happened, was it handled?
#   - Were any tool uses blocked (permission denials)?
#   - What was the stop_reason?

claude -p "Follow the CLAUDE.md protocol exactly. NEVER STOP until max-turns is reached." \
    --max-turns 30 \
    --max-budget-usd 2.00 \
    --allowedTools "Bash Edit Read Write" \
    --output-format json \
    2>&1 | tee baseline-run-output.json

echo ""
echo "  OK: Claude loop completed"

# ---------------------------------------------------------------------------
# Post-run diagnostics
# ---------------------------------------------------------------------------
echo "[7/8] Collecting post-run diagnostics..."

DIAGNOSTICS_FILE="$EXPERIMENT_DIR/diagnostics.txt"

{
    echo "====== POST-RUN DIAGNOSTICS ======"
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""

    echo "--- baseline-run-output.json (key fields) ---"
    if [ -f baseline-run-output.json ]; then
        python3 -c "
import json, sys
try:
    with open('baseline-run-output.json') as f:
        data = json.load(f)
    print('stop_reason     :', data.get('stop_reason', 'N/A'))
    print('num_turns       :', data.get('num_turns', 'N/A'))
    print('total_cost_usd  :', data.get('total_cost_usd', 'N/A'))
    print('is_error        :', data.get('is_error', 'N/A'))
    usage = data.get('usage', {})
    if usage:
        print('input_tokens    :', usage.get('input_tokens', 'N/A'))
        print('output_tokens   :', usage.get('output_tokens', 'N/A'))
except Exception as e:
    print('ERROR parsing JSON:', e)
" 2>&1
    else
        echo "WARNING: baseline-run-output.json not found"
    fi
    echo ""

    echo "--- results.tsv ---"
    if [ -f results.tsv ]; then
        cat results.tsv
    else
        echo "WARNING: results.tsv does not exist (agent may not have completed any experiments)"
    fi
    echo ""

    echo "--- git log --oneline ---"
    git log --oneline 2>&1
    echo ""

    echo "--- prepare.py diff (should be empty) ---"
    git diff HEAD -- prepare.py 2>&1
    if [ -z "$(git diff HEAD -- prepare.py 2>/dev/null)" ]; then
        echo "(no changes -- frozen file compliance PASSED)"
    fi
    echo ""

    echo "--- run.log (last 20 lines) ---"
    if [ -f run.log ]; then
        tail -20 run.log
    else
        echo "WARNING: run.log does not exist"
    fi
    echo ""

} | tee "$DIAGNOSTICS_FILE"

# ---------------------------------------------------------------------------
# Print human-readable summary
# ---------------------------------------------------------------------------
echo "[8/8] Summary"
echo "============================================================"

if [ -f baseline-run-output.json ]; then
    python3 -c "
import json
try:
    with open('baseline-run-output.json') as f:
        data = json.load(f)
    print('  stop_reason   :', data.get('stop_reason', 'N/A'))
    print('  num_turns     :', data.get('num_turns', 'N/A'))
    print('  total_cost_usd:', data.get('total_cost_usd', 'N/A'))
except:
    print('  (could not parse JSON output)')
" 2>&1
fi

if [ -f results.tsv ]; then
    EXPERIMENT_COUNT=$(( $(wc -l < results.tsv) - 1 ))
    echo "  experiments   : $EXPERIMENT_COUNT (rows in results.tsv)"
    BEST_METRIC=$(tail -n +2 results.tsv | sort -t$'\t' -k3 -rn | head -1 | cut -f3 2>/dev/null || echo "N/A")
    echo "  best_metric   : $BEST_METRIC"
else
    echo "  results.tsv   : NOT FOUND"
fi

echo ""
echo "Full diagnostics saved to: $DIAGNOSTICS_FILE"
echo ""
echo "============================================================"
echo "  NEXT STEP: Return to Claude Code and provide:"
echo "  1. Contents of: $EXPERIMENT_DIR/baseline-run-output.json"
echo "  2. Contents of: $EXPERIMENT_DIR/results.tsv (if it exists)"
echo "  3. Output of:   git log --oneline  (run inside $EXPERIMENT_DIR)"
echo "  4. Any errors or unexpected behavior you observed"
echo "  5. Whether 'git diff HEAD -- prepare.py' showed any changes"
echo "============================================================"
