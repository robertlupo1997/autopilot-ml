#!/usr/bin/env bash
# =============================================================================
# run-v3-validation-test.sh
# Phase 18: E2E Validation Test -- v3.0 Intelligent Iteration (Phases 15-17)
#
# IMPORTANT: Run this script from a terminal OUTSIDE of Claude Code.
# Claude Code cannot launch 'claude -p' inside another Claude Code session.
# If you are currently in a Claude Code terminal session, open a NEW terminal
# and run this script from there.
#
# Usage:
#   cd /home/tlupo/AutoML
#   ./scripts/run-v3-validation-test.sh
#
# Expected runtime: 10-25 minutes (capped at $6.00 budget, 75 turns max).
#
# What this validates:
#   - Phases 15-17 work together as a complete v3.0 intelligent iteration system
#   - Scaffold with --date-column creates correct forecasting experiment layout
#   - Autonomous loop runs Optuna-tuned models with walk-forward validation
#   - Agent respects frozen files (prepare.py AND forecast.py)
#   - Agent beats seasonal naive baseline (EVAL-01)
#   - At least 5 experiments and 1 keep decision (EVAL-02)
#   - EVAL-03: Agent reads and modifies experiments.md (journal usage)
#   - EVAL-04: Agent creates explore-* branches after 3+ consecutive reverts (stagnation)
#
# Key differences from Phase 14 (run-forecast-validation-test.sh):
#   - Max turns: 75 (was 50) to allow enough iterations for stagnation to trigger
#   - Budget cap: $6.00 (was $4.00) to support longer run
#   - Captures initial experiments.md hash before loop (for EVAL-03 comparison)
#   - EVAL-03: Checks if agent modified experiments.md and populated knowledge sections
#   - EVAL-04: Checks for explore-* branches and counts consecutive reverts
#   - Output file: v3-validation-run-output.json (was forecast-validation-run-output.json)
# =============================================================================

# OBSERVATION CHECKLIST (for manual review after the run):
#   Phase 15 (Diagnosis and Journal Infrastructure):
#   - Was experiments.md generated at scaffold? (journal seeded)
#   - Did agent modify experiments.md during the run? (EVAL-03)
#
#   Phase 16 (Template and Protocol Updates):
#   - Is diagnostic_output: line present in run.log? (DIAG-02/03)
#   - Did agent follow the v3.0 journal read/write protocol? (Steps 2 and 12)
#   - Did agent commit hypotheses with descriptive messages?
#
#   Phase 17 (Branch-on-Stagnation):
#   - Were any explore-* branches created? (EVAL-04)
#   - Did max consecutive reverts reach 3+? (stagnation condition)
#   - Do results.tsv rows span multiple branches?
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
echo "  AutoML Phase 18: E2E v3.0 Intelligent Iteration Validation"
echo "  Project root : $PROJECT_ROOT"
echo "  Experiment   : $EXPERIMENT_DIR"
echo "  Dataset      : quarterly_revenue.csv (40 rows, quarterly time-series)"
echo "  Target metric: MAPE (lower is better)"
echo "  Max turns    : 75 | Budget cap: \$6.00"
echo "  Validates    : EVAL-03 (journal usage) + EVAL-04 (branch-on-stagnation)"
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
    echo "         cd $PROJECT_ROOT && ./scripts/run-v3-validation-test.sh"
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

if [ -f "$EXPERIMENT_DIR/experiments.md" ]; then
    echo "  OK: experiments.md exists in experiment dir (journal seeded by Phase 15)"
else
    echo "  WARN: experiments.md not found in experiment dir (Phase 15 journal feature may not be active)"
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
# Capture initial experiments.md state (for EVAL-03 comparison)
# ---------------------------------------------------------------------------
INITIAL_EXPERIMENTS_MD_HASH=$(git hash-object experiments.md 2>/dev/null || echo "missing")
INITIAL_EXPERIMENTS_MD_LINES=$(wc -l < experiments.md 2>/dev/null || echo "0")
echo "  OK: Captured initial experiments.md state (hash: $INITIAL_EXPERIMENTS_MD_HASH, lines: $INITIAL_EXPERIMENTS_MD_LINES)"

# ---------------------------------------------------------------------------
# Run the autonomous ML loop via claude -p
# ---------------------------------------------------------------------------
echo "[6/8] Running autonomous v3.0 intelligent iteration loop (this may take 10-25 minutes)..."
echo "      Max turns: 75 | Budget cap: \$6.00"
echo "      Output: $EXPERIMENT_DIR/v3-validation-run-output.json"
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
    --max-turns 75 \
    --max-budget-usd 6.00 \
    --output-format json \
    --allowedTools "Bash(*)" "Edit(*)" "Write(*)" "Read" "Glob" "Grep" \
    2>&1 | tee v3-validation-run-output.json

echo ""
echo "  OK: Claude v3.0 intelligent iteration loop completed"

# ---------------------------------------------------------------------------
# Post-run diagnostics
# ---------------------------------------------------------------------------
echo "[7/8] Collecting post-run diagnostics..."

echo ""
echo "--- parse_run_result.py output ---"
python3 "$PROJECT_ROOT/scripts/parse_run_result.py" v3-validation-run-output.json 2>&1 || echo "WARN: parse_run_result.py failed"
echo ""

echo "--- Automated Assertions ---"

# Assert stop_reason is not tool_use
STOP_REASON=$(python3 "$PROJECT_ROOT/scripts/parse_run_result.py" \
    v3-validation-run-output.json 2>/dev/null | grep "^stop_reason:" | cut -d' ' -f2 || echo "unknown")
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

# Assert forecast.py unchanged (frozen file compliance -- from Phase 11)
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

# Check diagnostic_output in run.log (Phase 16 diagnostics)
if [ -f run.log ] && grep -q "^diagnostic_output:" run.log; then
    echo "  OK: diagnostic_output line present in run.log (Phase 16 diagnostics PASSED)"
else
    echo "  WARN: diagnostic_output line not found in run.log (Phase 16 diagnostics not verified)"
fi

# Check permission_denials
python3 -c "
import json
with open('v3-validation-run-output.json') as f:
    data = json.load(f)
denials = data.get('permission_denials', [])
print(f'  permission_denials: {len(denials)} ({denials if denials else \"none\"})')
" 2>/dev/null || echo "  WARN: could not parse permission_denials from v3-validation-run-output.json"

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

echo "--- git log --oneline --all ---"
git log --oneline --all 2>&1
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
# EVAL-03: Journal Usage
# ---------------------------------------------------------------------------
echo "--- EVAL-03: Journal Usage ---"
# Check if experiments.md was modified from scaffold state
FINAL_EXPERIMENTS_MD_HASH=$(git hash-object experiments.md 2>/dev/null || echo "missing")
FINAL_EXPERIMENTS_MD_LINES=$(wc -l < experiments.md 2>/dev/null || echo "0")

if [ "$INITIAL_EXPERIMENTS_MD_HASH" != "$FINAL_EXPERIMENTS_MD_HASH" ]; then
    echo "  OK: experiments.md was modified by the agent (hash changed)"
    echo "       Initial lines: $INITIAL_EXPERIMENTS_MD_LINES -> Final lines: $FINAL_EXPERIMENTS_MD_LINES"
else
    echo "  FAIL: experiments.md was NOT modified (agent did not update journal)"
fi

# Check if experiments.md appears in git log (agent committed journal updates)
JOURNAL_COMMITS=$(git log --oneline --all -- experiments.md | wc -l)
echo "  Commits touching experiments.md: $JOURNAL_COMMITS"

# Check for Best Result population (EXPL-01 evidence)
if grep -q "Commit:.*[a-f0-9]\{7\}" experiments.md 2>/dev/null; then
    echo "  OK: Best Result section has a commit hash (EXPL-01 evidence)"
else
    echo "  INFO: Best Result section does not have a commit hash"
fi

# Check for content in What Works / What Doesn't / Error Patterns sections
# (evidence agent wrote findings)
python3 - <<'PYEOF'
with open("experiments.md") as f:
    content = f.read()

sections = {
    "What Works": "## What Works" in content and len(content.split("## What Works")[1].split("##")[0].strip()) > 20,
    "What Doesn't": "## What Doesn't" in content and len(content.split("## What Doesn't")[1].split("##")[0].strip()) > 20,
    "Error Patterns": "## Error Patterns" in content and len(content.split("## Error Patterns")[1].split("##")[0].strip()) > 20,
}

for section, has_content in sections.items():
    status = "OK" if has_content else "INFO"
    print(f"  {status}: {section} section {'has agent-written content' if has_content else 'is empty/minimal'}")
PYEOF

echo ""
echo "--- experiments.md (full contents) ---"
cat experiments.md 2>/dev/null || echo "  WARNING: experiments.md not found"
echo ""

# ---------------------------------------------------------------------------
# EVAL-04: Branch-on-Stagnation
# ---------------------------------------------------------------------------
echo "--- EVAL-04: Branch-on-Stagnation ---"
# Check for explore-* branches
EXPLORE_BRANCHES=$(git branch --all | grep "explore-" | wc -l)
if [ "$EXPLORE_BRANCHES" -gt 0 ]; then
    echo "  OK: EVAL-04 PASSED -- $EXPLORE_BRANCHES explore branch(es) found:"
    git branch --all | grep "explore-" | sed 's/^/       /'
else
    echo "  INFO: No explore-* branches found"
    echo "       (Agent may not have hit 3 consecutive reverts)"
fi

# Count consecutive reverts in results.tsv to check if stagnation conditions existed
python3 - <<'PYEOF'
import csv
import sys

try:
    with open("results.tsv") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)
except FileNotFoundError:
    print("  WARN: results.tsv not found")
    sys.exit(0)

# Find the status column (may be "status" or "decision")
status_col = None
for col in ["status", "decision"]:
    if col in (rows[0].keys() if rows else []):
        status_col = col
        break

if status_col is None:
    print("  WARN: Cannot determine status column in results.tsv")
    sys.exit(0)

# Count max consecutive reverts
max_consec_reverts = 0
current_streak = 0
for row in rows:
    status = row.get(status_col, "").lower()
    if "revert" in status:
        current_streak += 1
        max_consec_reverts = max(max_consec_reverts, current_streak)
    else:
        current_streak = 0

print(f"  Max consecutive reverts: {max_consec_reverts}")
if max_consec_reverts >= 3:
    print("  OK: Stagnation condition (3+ consecutive reverts) was reached")
else:
    print("  INFO: Stagnation condition NOT reached (fewer than 3 consecutive reverts)")
    print("        EVAL-04 may need a longer run or different dataset to trigger")
PYEOF

# Check if explore branch has results in results.tsv
if [ "$EXPLORE_BRANCHES" -gt 0 ]; then
    # Results from explore branches should appear in the same results.tsv
    echo "  Results in results.tsv from all branches:"
    if [ -f results.tsv ]; then
        TOTAL_ROWS=$(( $(wc -l < results.tsv) - 1 ))
        echo "       Total experiments across all branches: $TOTAL_ROWS"
    fi
fi

echo ""
echo "--- git branch --all ---"
git branch --all 2>&1
echo ""

# ---------------------------------------------------------------------------
# Print human-readable summary
# ---------------------------------------------------------------------------
echo "[8/8] Summary"
echo "============================================================"

if [ -f v3-validation-run-output.json ]; then
    python3 -c "
import json
try:
    with open('v3-validation-run-output.json') as f:
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
echo "  1. The automated assertion results (OK/FAIL/WARN/INFO lines above)"
echo "  2. Output of parse_run_result.py (stop_reason, num_turns, cost)"
echo "  3. Contents of results.tsv"
echo "  4. EVAL-03 results: Was experiments.md modified? What sections had content?"
echo "  5. EVAL-04 results: Were explore-* branches created? Max consecutive reverts?"
echo "  6. Contents of experiments.md (cat experiments.md)"
echo "  7. Git branch listing (git branch --all)"
echo "  8. Git log (git log --oneline --all)"
echo "  9. Any errors or unexpected behavior"
echo "============================================================"
