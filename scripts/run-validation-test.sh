#!/usr/bin/env bash
# =============================================================================
# run-validation-test.sh
# Phase 7: E2E Validation Test -- Re-run the autonomous ML loop after Phase 5-6 fixes
#
# IMPORTANT: Run this script from a terminal OUTSIDE of Claude Code.
# Claude Code cannot launch 'claude -p' inside another Claude Code session.
# If you are currently in a Claude Code terminal session, open a NEW terminal
# and run this script from there.
#
# Usage:
#   cd /home/tlupo/AutoML
#   ./scripts/run-validation-test.sh
#
# Expected runtime: 5-10 minutes (capped at $4.00 budget, 50 turns max).
#
# Key differences from Phase 4 (run-baseline-test.sh):
#   - Uses noisy.csv (300 rows, 10% label noise) instead of iris.csv
#   - Max turns: 50 (not 30) -- exercises stagnation handling (5+ reverts needed)
#   - Budget cap: $4.00 (not $2.00)
#   - --allowedTools flag passed (project settings.json alone isn't sufficient in headless -p mode)
#   - Automated assertions section validates Phase 5-6 fixes
# =============================================================================

# OBSERVATION CHECKLIST (for manual review after the run):
#   Phase 5 (Hooks + Graceful Shutdown):
#   - Did hooks fire? (permission_denials count in automated assertions below)
#   - Is stop_reason end_turn or max_turns (not tool_use)?
#   - Is prepare.py unchanged? (frozen file enforcement)
#   - Did agent start without --dangerously-skip-permissions?
#
#   Phase 6 (Structured Output):
#   - Is json_output line present in run.log?
#   - Is json_output parseable and values consistent with key:value block?
#
#   Core Loop:
#   - Did 3-5 drafts generate with different algorithm families?
#   - Was best draft selected correctly?
#   - Did git commits happen on keep? Did reset happen on revert?
#   - Did stagnation trigger strategy shift? (5+ consecutive reverts needed)
#   - Did any crashes occur and were they handled?

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXPERIMENT_DIR="$PROJECT_ROOT/experiment-noisy"
NOISY_CSV="$PROJECT_ROOT/tests/fixtures/noisy.csv"

echo "============================================================"
echo "  AutoML Phase 7: E2E Validation Test"
echo "  Project root : $PROJECT_ROOT"
echo "  Experiment   : $EXPERIMENT_DIR"
echo "  Dataset      : noisy.csv (300 rows, 10 features, 10% label noise)"
echo "  Target metric: accuracy (ceiling ~0.88-0.90)"
echo "  Max turns    : 50 | Budget cap: \$4.00"
echo "============================================================"
echo ""
echo "NOTE: This script must be run OUTSIDE of a Claude Code session."
echo "      'claude -p' cannot be launched inside another CC session."
echo "      If you see an error about nested sessions, open a new terminal."
echo "      Tool permissions are governed by settings.json (no allowedTools flag)."
echo ""

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
echo "[1/8] Pre-flight checks..."

if [ ! -f "$NOISY_CSV" ]; then
    echo "ERROR: noisy.csv not found at $NOISY_CSV"
    echo "       Run from AutoML project root:"
    echo "         uv run python3 -c \"from sklearn.datasets import make_classification; import pandas as pd; X, y = make_classification(n_samples=300, n_features=10, n_informative=5, n_redundant=3, flip_y=0.10, random_state=42); df = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(10)]); df['target'] = y; df.to_csv('tests/fixtures/noisy.csv', index=False)\""
    exit 1
fi

NOISY_ROW_COUNT=$(python3 -c "
import csv
with open('$NOISY_CSV') as f:
    rows = sum(1 for _ in csv.reader(f)) - 1  # subtract header
print(rows)
" 2>/dev/null || echo "0")
if [ "$NOISY_ROW_COUNT" -lt 300 ]; then
    echo "ERROR: noisy.csv has only $NOISY_ROW_COUNT rows (expected 300+)"
    exit 1
fi
echo "  OK: noisy.csv found with $NOISY_ROW_COUNT rows"

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
    echo "         cd $PROJECT_ROOT && ./scripts/run-validation-test.sh"
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
cp "$NOISY_CSV" .
uv run automl noisy.csv target accuracy \
    --goal "Binary classification on a noisy synthetic dataset (10% label noise, ~0.88-0.90 accuracy ceiling). Push for accuracy above 0.90 if possible."

if [ ! -d "$EXPERIMENT_DIR" ]; then
    echo "ERROR: Expected experiment directory not created: $EXPERIMENT_DIR"
    echo "       The scaffold command may have failed or created a different directory."
    echo "       Available dirs: $(ls -d */ 2>/dev/null | head -5)"
    exit 1
fi
echo "  OK: Experiment scaffolded at $EXPERIMENT_DIR"

# Clean up the copied CSV from project root
rm -f "$PROJECT_ROOT/noisy.csv"

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
echo "[6/8] Running autonomous ML loop (this may take 5-10 minutes)..."
echo "      Max turns: 50 | Budget cap: \$4.00"
echo "      Output: $EXPERIMENT_DIR/validation-run-output.json"
echo "      NOTE: --allowedTools passed for headless mode (settings.json alone is insufficient)"
echo ""

claude -p "Follow the CLAUDE.md protocol exactly. NEVER STOP until max-turns is reached." \
    --max-turns 50 \
    --max-budget-usd 4.00 \
    --output-format json \
    --allowedTools "Bash(*)" "Edit(train.py)" "Write(train.py)" "Write(results.tsv)" "Write(run.log)" "Read" "Glob" "Grep" \
    2>&1 | tee validation-run-output.json

echo ""
echo "  OK: Claude loop completed"

# ---------------------------------------------------------------------------
# Post-run diagnostics
# ---------------------------------------------------------------------------
echo "[7/8] Collecting post-run diagnostics..."

echo ""
echo "--- parse_run_result.py output ---"
python3 "$PROJECT_ROOT/scripts/parse_run_result.py" validation-run-output.json 2>&1 || echo "WARN: parse_run_result.py failed"
echo ""

echo "--- Automated Assertions ---"

# Assert stop_reason is not tool_use
STOP_REASON=$(python3 "$PROJECT_ROOT/scripts/parse_run_result.py" \
    validation-run-output.json 2>/dev/null | grep "^stop_reason:" | cut -d' ' -f2 || echo "unknown")
if [ "$STOP_REASON" = "tool_use" ]; then
    echo "  FAIL: stop_reason=tool_use -- agent interrupted mid-action (Phase 5 graceful shutdown not working)"
else
    echo "  OK: stop_reason=$STOP_REASON (acceptable, not tool_use)"
fi

# Assert prepare.py unchanged (frozen file compliance)
if [ -z "$(git diff HEAD -- prepare.py 2>/dev/null)" ]; then
    echo "  OK: prepare.py unchanged (frozen file compliance PASSED)"
else
    echo "  FAIL: prepare.py was modified! (hooks enforcement FAILED)"
    git diff HEAD -- prepare.py 2>/dev/null | head -20
fi

# Check json_output in run.log (Phase 6 structured output)
if [ -f run.log ] && grep -q "^json_output:" run.log; then
    echo "  OK: json_output line present in run.log (Phase 6 structured output PASSED)"
else
    echo "  WARN: json_output line not found in run.log (Phase 6 structured output not verified)"
fi

# Check permission_denials (Phase 5 hooks)
python3 -c "
import json
with open('validation-run-output.json') as f:
    data = json.load(f)
denials = data.get('permission_denials', [])
print(f'  permission_denials: {len(denials)} ({denials if denials else \"none\"})')
" 2>/dev/null || echo "  WARN: could not parse permission_denials from validation-run-output.json"

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

# ---------------------------------------------------------------------------
# Print human-readable summary
# ---------------------------------------------------------------------------
echo "[8/8] Summary"
echo "============================================================"

if [ -f validation-run-output.json ]; then
    python3 -c "
import json
try:
    with open('validation-run-output.json') as f:
        data = json.load(f)
    print('  stop_reason   :', data.get('stop_reason', 'N/A'))
    print('  num_turns     :', data.get('num_turns', 'N/A'))
    print('  total_cost_usd:', data.get('total_cost_usd', 'N/A'))
    print('  is_error      :', data.get('is_error', 'N/A'))
    denials = data.get('permission_denials', [])
    print('  perm_denials  :', len(denials))
except:
    print('  (could not parse JSON output)')
" 2>&1
fi

if [ -f results.tsv ]; then
    EXPERIMENT_COUNT=$(( $(wc -l < results.tsv) - 1 ))
    echo "  experiments   : $EXPERIMENT_COUNT (rows in results.tsv)"
    BEST_METRIC=$(tail -n +2 results.tsv | sort -t$'\t' -k2 -rn | head -1 | cut -f2 2>/dev/null || echo "N/A")
    echo "  best_metric   : $BEST_METRIC"
else
    echo "  results.tsv   : NOT FOUND"
fi

echo ""
echo "============================================================"
echo "  NEXT STEP: Return to Claude Code and provide:"
echo "  1. The automated assertion results (OK/FAIL/WARN lines above)"
echo "  2. Output of: python3 $PROJECT_ROOT/scripts/parse_run_result.py validation-run-output.json"
echo "     (stop_reason, num_turns, total_cost_usd)"
echo "  3. Contents of: $EXPERIMENT_DIR/results.tsv (if it exists)"
echo "  4. Output of:   git log --oneline  (run inside $EXPERIMENT_DIR)"
echo "  5. Whether permission_denials had any entries"
echo "  6. Any error messages or unexpected behavior observed"
echo "============================================================"
