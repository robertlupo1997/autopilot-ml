#!/usr/bin/env bash
# =============================================================================
# run-forecast-validation-test.sh
# Phase 14: E2E Validation Test -- Forecasting path (Phases 11-13)
#
# IMPORTANT: Run this script from a terminal OUTSIDE of Claude Code.
# Claude Code cannot launch 'claude -p' inside another Claude Code session.
# If you are currently in a Claude Code terminal session, open a NEW terminal
# and run this script from there.
#
# Usage:
#   cd /home/tlupo/AutoML
#   ./scripts/run-forecast-validation-test.sh
#
# Expected runtime: 5-15 minutes (capped at $4.00 budget, 50 turns max).
#
# What this validates:
#   - Phases 11-13 work together as a complete forecasting system
#   - Scaffold with --date-column creates correct forecasting experiment layout
#   - Autonomous loop runs Optuna-tuned models with walk-forward validation
#   - Agent respects frozen files (prepare.py AND forecast.py)
#   - Agent beats seasonal naive baseline (EVAL-01)
#   - At least 5 experiments and 1 keep decision (EVAL-02)
#
# Key differences from Phase 7 (run-validation-test.sh):
#   - Uses quarterly_revenue.csv (40 rows, time-series) instead of noisy.csv
#   - Scaffold command uses --date-column quarter flag (forecasting mode)
#   - Metric is MAPE (lower is better) instead of accuracy
#   - Checks BOTH frozen files: prepare.py AND forecast.py
#   - Asserts beats_seasonal_naive from json_output (EVAL-01)
#   - Counts experiments in results.tsv for EVAL-02
# =============================================================================

# OBSERVATION CHECKLIST (for manual review after the run):
#   Phase 11 (Forecasting Infrastructure):
#   - Is forecast.py unchanged? (frozen file enforcement -- new in Phase 11)
#   - Is prepare.py unchanged? (frozen file enforcement -- established in Phase 5)
#
#   Phase 12 (Forecast Template):
#   - Did agent run Optuna trials and produce MAPE output?
#   - Did agent enforce dual-baseline gate (beats_naive AND beats_seasonal_naive)?
#   - Is json_output line present in run.log?
#
#   Phase 13 (Scaffold + CLI):
#   - Did scaffold create train.py with DATE_COLUMN defined?
#   - Did scaffold create forecast.py in experiment dir?
#   - Did program.md include MAPE baseline scores?
#
#   Core Loop (EVAL-01 / EVAL-02):
#   - beats_seasonal_naive: True in json_output?
#   - At least 5 experiments completed?
#   - At least 1 keep decision?

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXPERIMENT_DIR="$PROJECT_ROOT/experiment-quarterly_revenue"
DATASET_CSV="$PROJECT_ROOT/tests/fixtures/quarterly_revenue.csv"

echo "============================================================"
echo "  AutoML Phase 14: E2E Forecasting Validation Test"
echo "  Project root : $PROJECT_ROOT"
echo "  Experiment   : $EXPERIMENT_DIR"
echo "  Dataset      : quarterly_revenue.csv (40 rows, quarterly time-series)"
echo "  Target metric: MAPE (lower is better)"
echo "  Max turns    : 50 | Budget cap: \$4.00"
echo "============================================================"
echo ""
echo "NOTE: This script must be run OUTSIDE of a Claude Code session."
echo "      'claude -p' cannot be launched inside another CC session."
echo "      If you see an error about nested sessions, open a new terminal."
echo "      Tool permissions: --allowedTools + guard-frozen.sh hook for prepare.py + forecast.py."
echo ""

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
echo "[1/8] Pre-flight checks..."

if [ ! -f "$DATASET_CSV" ]; then
    echo "ERROR: quarterly_revenue.csv not found at $DATASET_CSV"
    echo "       Run from AutoML project root to regenerate:"
    echo "         uv run python3 -c \""
    echo "import numpy as np, pandas as pd"
    echo "np.random.seed(42)"
    echo "n=40"
    echo "quarters = pd.date_range('2014-01-01', periods=n, freq='QS')"
    echo "trend = np.linspace(1_000_000, 2_000_000, n)"
    echo "seasonal = np.tile([0.85, 1.1, 1.0, 1.05], 10)"
    echo "noise = np.random.normal(0, 30_000, n)"
    echo "revenue = trend * seasonal + noise"
    echo "df = pd.DataFrame({'quarter': quarters, 'revenue': revenue})"
    echo "df.to_csv('tests/fixtures/quarterly_revenue.csv', index=False)"
    echo "\""
    exit 1
fi

DATASET_ROW_COUNT=$(python3 -c "
import csv
with open('$DATASET_CSV') as f:
    rows = sum(1 for _ in csv.reader(f)) - 1  # subtract header
print(rows)
" 2>/dev/null || echo "0")
if [ "$DATASET_ROW_COUNT" -lt 40 ]; then
    echo "ERROR: quarterly_revenue.csv has only $DATASET_ROW_COUNT rows (expected 40)"
    exit 1
fi
echo "  OK: quarterly_revenue.csv found with $DATASET_ROW_COUNT rows"

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
    echo "         cd $PROJECT_ROOT && ./scripts/run-forecast-validation-test.sh"
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
# Scaffold the experiment using the AutoML CLI (forecasting mode)
# ---------------------------------------------------------------------------
echo "[3/8] Scaffolding experiment with 'uv run automl' (forecasting mode)..."

cd "$PROJECT_ROOT"
cp "$DATASET_CSV" .
uv run automl quarterly_revenue.csv revenue mape \
    --date-column quarter \
    --goal "Forecast quarterly revenue for 40 synthetic quarters (2014-2024). Beat both naive (repeat last) and seasonal-naive (same quarter last year) baselines." \
    --time-budget 120

if [ ! -d "$EXPERIMENT_DIR" ]; then
    echo "ERROR: Expected experiment directory not created: $EXPERIMENT_DIR"
    echo "       The scaffold command may have failed or created a different directory."
    echo "       Available dirs: $(ls -d */ 2>/dev/null | head -10)"
    exit 1
fi
echo "  OK: Experiment scaffolded at $EXPERIMENT_DIR"

# Post-scaffold verification: check key forecasting artifacts
echo "  Verifying forecasting scaffold artifacts..."

if grep -q "DATE_COLUMN" "$EXPERIMENT_DIR/train.py" 2>/dev/null; then
    echo "  OK: train.py contains DATE_COLUMN (forecasting mode confirmed)"
else
    echo "  WARN: train.py does not contain DATE_COLUMN -- scaffold may not have used forecasting mode"
fi

if [ -f "$EXPERIMENT_DIR/forecast.py" ]; then
    echo "  OK: forecast.py exists in experiment dir (frozen file seeded)"
else
    echo "  WARN: forecast.py not found in experiment dir"
fi

if grep -q "mape" "$EXPERIMENT_DIR/program.md" 2>/dev/null || grep -q "MAPE" "$EXPERIMENT_DIR/program.md" 2>/dev/null; then
    echo "  OK: program.md references MAPE baseline scores"
else
    echo "  WARN: program.md may not contain MAPE baseline scores"
fi

# Clean up the copied CSV from project root
rm -f "$PROJECT_ROOT/quarterly_revenue.csv"

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
echo "[6/8] Running autonomous forecasting loop (this may take 5-15 minutes)..."
echo "      Max turns: 50 | Budget cap: \$4.00"
echo "      Output: $EXPERIMENT_DIR/forecast-validation-run-output.json"
echo "      NOTE: --allowedTools passed for headless mode"
echo ""

# ---------------------------------------------------------------------------
# HEADLESS PERMISSIONS NOTE (Phase 8):
# settings.json permissions.allow rules are silently ignored in headless
# claude -p mode (GitHub issue #18160, open as of 2026-03-13).
# The --allowedTools flag below is REQUIRED for tool access. Do NOT remove it.
# The scaffolded settings.json allow rules serve as documentation of intent
# for interactive mode only. The guard-frozen.sh hook remains the primary
# enforcement mechanism for frozen file protection (both prepare.py and forecast.py).
# ---------------------------------------------------------------------------
claude -p "Follow the CLAUDE.md protocol exactly. NEVER STOP until max-turns is reached." \
    --max-turns 50 \
    --max-budget-usd 4.00 \
    --output-format json \
    --allowedTools "Bash(*)" "Edit(*)" "Write(*)" "Read" "Glob" "Grep" \
    2>&1 | tee forecast-validation-run-output.json

echo ""
echo "  OK: Claude forecasting loop completed"

# ---------------------------------------------------------------------------
# Post-run diagnostics
# ---------------------------------------------------------------------------
echo "[7/8] Collecting post-run diagnostics..."

echo ""
echo "--- parse_run_result.py output ---"
python3 "$PROJECT_ROOT/scripts/parse_run_result.py" forecast-validation-run-output.json 2>&1 || echo "WARN: parse_run_result.py failed"
echo ""

echo "--- Automated Assertions ---"

# Assert stop_reason is not tool_use
STOP_REASON=$(python3 "$PROJECT_ROOT/scripts/parse_run_result.py" \
    forecast-validation-run-output.json 2>/dev/null | grep "^stop_reason:" | cut -d' ' -f2 || echo "unknown")
if [ "$STOP_REASON" = "tool_use" ]; then
    echo "  FAIL: stop_reason=tool_use -- agent interrupted mid-action (graceful shutdown not working)"
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

# Assert forecast.py unchanged (frozen file compliance -- new in Phase 11)
if [ -z "$(git diff HEAD -- forecast.py 2>/dev/null)" ]; then
    echo "  OK: forecast.py unchanged (frozen file compliance PASSED)"
else
    echo "  FAIL: forecast.py was modified! (hooks enforcement FAILED for forecasting frozen file)"
    git diff HEAD -- forecast.py 2>/dev/null | head -20
fi

# Check json_output in run.log (Phase 6 structured output)
if [ -f run.log ] && grep -q "^json_output:" run.log; then
    echo "  OK: json_output line present in run.log (structured output PASSED)"
else
    echo "  WARN: json_output line not found in run.log (structured output not verified)"
fi

# Check permission_denials
python3 -c "
import json
with open('forecast-validation-run-output.json') as f:
    data = json.load(f)
denials = data.get('permission_denials', [])
print(f'  permission_denials: {len(denials)} ({denials if denials else \"none\"})')
" 2>/dev/null || echo "  WARN: could not parse permission_denials from forecast-validation-run-output.json"

# Extract EVAL-01 / EVAL-02 metrics from last json_output line in run.log
echo ""
echo "--- EVAL-01 / EVAL-02 Metric Extraction ---"
echo "  NOTE: last json_output may be from a reverted experiment."
echo "        Cross-reference with results.tsv for the actual best kept MAPE."
python3 - <<'PYEOF'
import json
import re
import sys

runlog = "run.log"
try:
    with open(runlog) as f:
        content = f.read()
except FileNotFoundError:
    print("  WARN: run.log not found -- cannot extract metrics")
    sys.exit(0)

# Find last json_output line
lines = content.splitlines()
last_json_line = None
for line in reversed(lines):
    if line.startswith("json_output:"):
        last_json_line = line
        break

if last_json_line is None:
    print("  WARN: No json_output line found in run.log")
    sys.exit(0)

# Parse the JSON payload after "json_output:"
json_str = last_json_line[len("json_output:"):].strip()
try:
    data = json.loads(json_str)
except json.JSONDecodeError as e:
    print(f"  WARN: Could not parse json_output: {e}")
    sys.exit(0)

beats_naive = data.get("beats_naive", "N/A")
beats_seasonal_naive = data.get("beats_seasonal_naive", "N/A")
metric_value = data.get("metric_value", "N/A")
naive_baseline = data.get("naive_baseline", data.get("naive_mape", "N/A"))
seasonal_naive_baseline = data.get("seasonal_naive_baseline", data.get("seasonal_naive_mape", "N/A"))

print(f"  metric_value (MAPE)       : {metric_value}")
print(f"  naive_baseline_mape       : {naive_baseline}")
print(f"  seasonal_naive_baseline   : {seasonal_naive_baseline}")
print(f"  beats_naive               : {beats_naive}")
print(f"  beats_seasonal_naive      : {beats_seasonal_naive}")
PYEOF

# Count experiments and keeps in results.tsv
echo ""
echo "--- results.tsv ---"
if [ -f results.tsv ]; then
    cat results.tsv
    TOTAL_EXPERIMENTS=$(( $(wc -l < results.tsv) - 1 ))
    KEEP_COUNT=$(tail -n +2 results.tsv | grep -cE "(draft-keep|keep)" || true)
    echo ""
    echo "  Total experiments : $TOTAL_EXPERIMENTS"
    echo "  Keep decisions    : $KEEP_COUNT"
else
    echo "  WARNING: results.tsv does not exist (agent may not have completed any experiments)"
    TOTAL_EXPERIMENTS=0
    KEEP_COUNT=0
fi
echo ""

echo "--- git log --oneline ---"
git log --oneline 2>&1
echo ""

echo "--- run.log (last 30 lines) ---"
if [ -f run.log ]; then
    tail -30 run.log
else
    echo "WARNING: run.log does not exist"
fi
echo ""

# ---------------------------------------------------------------------------
# EVAL-01: Beat Seasonal Naive assertion
# ---------------------------------------------------------------------------
echo "--- EVAL-01: Beat Seasonal Naive ---"
python3 - <<'PYEOF'
import json
import sys

runlog = "run.log"
try:
    with open(runlog) as f:
        content = f.read()
except FileNotFoundError:
    print("  WARN: run.log not found -- EVAL-01 cannot be auto-asserted")
    sys.exit(0)

last_json_line = None
for line in reversed(content.splitlines()):
    if line.startswith("json_output:"):
        last_json_line = line
        break

if last_json_line is None:
    print("  WARN: No json_output line in run.log -- EVAL-01 cannot be auto-asserted")
    sys.exit(0)

json_str = last_json_line[len("json_output:"):].strip()
try:
    data = json.loads(json_str)
except json.JSONDecodeError as e:
    print(f"  WARN: Could not parse json_output: {e}")
    sys.exit(0)

beats_seasonal_naive = data.get("beats_seasonal_naive")
if beats_seasonal_naive is True:
    print("  OK: EVAL-01 PASSED -- beats_seasonal_naive=True")
elif beats_seasonal_naive is False:
    print("  FAIL: EVAL-01 NOT MET -- beats_seasonal_naive=False (check results.tsv for best kept MAPE)")
else:
    print(f"  WARN: EVAL-01 status unclear -- beats_seasonal_naive={beats_seasonal_naive!r}")
PYEOF

# ---------------------------------------------------------------------------
# EVAL-02: Experiment count assertion
# ---------------------------------------------------------------------------
echo "--- EVAL-02: Experiment Count ---"
if [ -f results.tsv ]; then
    TOTAL_EXPERIMENTS=$(( $(wc -l < results.tsv) - 1 ))
    KEEP_COUNT=$(tail -n +2 results.tsv | grep -cE "(draft-keep|keep)" || true)
    if [ "$TOTAL_EXPERIMENTS" -ge 5 ] && [ "$KEEP_COUNT" -ge 1 ]; then
        echo "  OK: EVAL-02 PASSED -- $TOTAL_EXPERIMENTS experiments, $KEEP_COUNT keep(s)"
    elif [ "$TOTAL_EXPERIMENTS" -ge 5 ]; then
        echo "  WARN: EVAL-02 PARTIAL -- $TOTAL_EXPERIMENTS experiments but only $KEEP_COUNT keep(s) (need at least 1)"
    else
        echo "  FAIL: EVAL-02 NOT MET -- only $TOTAL_EXPERIMENTS experiments (need 5+), $KEEP_COUNT keep(s)"
    fi
else
    echo "  FAIL: EVAL-02 NOT MET -- results.tsv missing"
fi

# ---------------------------------------------------------------------------
# Print human-readable summary
# ---------------------------------------------------------------------------
echo "[8/8] Summary"
echo "============================================================"

if [ -f forecast-validation-run-output.json ]; then
    python3 -c "
import json
try:
    with open('forecast-validation-run-output.json') as f:
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
    # MAPE is lower=better, so sort ascending and take first
    BEST_MAPE=$(tail -n +2 results.tsv | sort -t$'\t' -k2 -n | head -1 | cut -f2 2>/dev/null || echo "N/A")
    echo "  best_mape     : $BEST_MAPE (lower is better)"
else
    echo "  results.tsv   : NOT FOUND"
fi

echo ""
echo "============================================================"
echo "  NEXT STEP: Return to Claude Code and provide:"
echo "  1. The automated assertion results (OK/FAIL/WARN lines above)"
echo "  2. Output of parse_run_result.py (stop_reason, num_turns, cost)"
echo "  3. Contents of results.tsv (shown above)"
echo "  4. beats_naive / beats_seasonal_naive values from json_output"
echo "  5. Whether prepare.py and forecast.py remained unchanged"
echo "  6. Any errors or unexpected behavior observed"
echo "============================================================"
