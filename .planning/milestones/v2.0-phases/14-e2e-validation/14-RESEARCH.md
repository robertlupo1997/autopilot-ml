# Phase 14: E2E Validation - Research

**Researched:** 2026-03-14
**Domain:** End-to-end integration testing of the v2.0 forecasting loop — synthetic dataset generation, autonomous loop execution, MAPE beat-baseline verification, FINDINGS.md documentation
**Confidence:** HIGH

---

## Summary

Phase 14 is a validation-only phase: no new code is added to `src/automl/`. The
deliverable is a shell script (`scripts/run-forecast-validation-test.sh`) plus a
structured `FINDINGS.md` that certifies every behavior claim made by Phases 11-13.

Phase 14 is structurally identical to Phase 7 (v1.0 validation), except it exercises
the **forecasting path** instead of the classification path. The Phase 7 script
(`scripts/run-validation-test.sh`) is the proven template. Phase 14 creates a new
script — never modifies the Phase 7 file (historical record).

**What makes Phase 14 distinct from Phase 7:**

- Dataset: synthetic quarterly revenue (40 rows, time-series) instead of noisy.csv (300 rows, classification)
- Scaffold invocation: `--date-column quarter` flag required
- Metric: MAPE (minimize) instead of accuracy (maximize)
- Beat-baseline test: new MAPE < both `naive` and `seasonal_naive` (both are walk-forward MAPE values)
- CLAUDE.md used: `claude_forecast.md.tmpl` (dual-baseline gate, MAPE-direction awareness)
- Frozen files: `prepare.py` AND `forecast.py` (two frozen files vs. one in v1.0)
- Loop instructions: `claude_forecast.md.tmpl` which includes the dual-baseline gate

Empirical verification (computed during research): With `noise_std=30000` (~2% of mean),
`naive MAPE = 0.0895` and `seasonal_naive MAPE = 0.0608`. A Ridge model with starter
features achieves `MAPE = 0.0291` — well below both baselines. The dataset is winnable
with the starting template. MAPE with `noise_std=80000` pushes seasonal naive to 0.073,
giving the agent genuine headroom to improve.

**Primary recommendation:** Use `noise_std=30000` (the default clean dataset). The agent
starts with a beatable MAPE, the baselines are non-trivial, and 50 turns is sufficient
for 5+ keep/revert cycles.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EVAL-01 | End-to-end test on synthetic quarterly revenue data (40 quarters) produces forecast that beats seasonal naive | Dataset empirically verified: Ridge with starter features achieves MAPE=0.029 vs seasonal_naive=0.061. Winnable. Script assertion checks `beats_seasonal_naive` from json_output. |
| EVAL-02 | Agent completes at least 5 keep/revert cycles within 50 turns (efficiency improvement over v1.0's 11 experiments) | Phase 7 ran 10 experiments in 51 turns. Forecasting experiments are slower (Optuna 80 trials x ~1s each = 80s/run). Budget estimate: 50 turns at $1.50-2.50 total. |
</phase_requirements>

---

## Standard Stack

### Core (all pre-existing — no new dependencies)

| Tool/Library | Version | Purpose | Status |
|-------------|---------|---------|--------|
| `claude` CLI | current | Headless loop execution via `claude -p` | Pre-installed |
| `uv` | current | `uv run automl` scaffold + `uv sync` in experiment dir | Pre-installed |
| `pytest` | 7.x | Syntax and fixture checks for the harness | In pyproject.toml |
| `scripts/parse_run_result.py` | project | Extracts stop_reason, num_turns, cost from JSON output | Built Phase 6 |
| `scripts/run-validation-test.sh` | project | Phase 7 harness — structural template for Phase 14 script | Exists |
| `automl forecast.py` | project | `get_forecasting_baselines`, `walk_forward_evaluate` | Frozen, exists |
| `automl scaffold.py` | project | `scaffold_experiment` with `date_col` branch | Exists (Phase 13) |
| `pandas` | 2.x | Quarterly date generation (`pd.date_range(..., freq='QS')`) | In pyproject.toml |
| `numpy` | 2.x | Revenue array construction | In pyproject.toml |

### Dataset Requirements

The synthetic quarterly revenue dataset must:

- Be **40 rows** (exactly 40 quarters = 10 years) — matches Phase 14 success criteria
- Have a **`quarter`** date column (DatetimeIndex after load_data) and a **`revenue`** target column
- Use **quarterly start frequency** (`freq='QS'`) starting 2014-01-01
- Have trend + seasonality + small noise so baselines are non-trivial but ML is winnable
- Be stored at `tests/fixtures/quarterly_revenue.csv`

**Recommended generation (computed and verified during research):**

```python
import numpy as np
import pandas as pd

np.random.seed(42)
n = 40
quarters = pd.date_range("2014-01-01", periods=n, freq="QS")
trend = np.linspace(1_000_000, 2_000_000, n)
seasonal = np.tile([0.85, 1.1, 1.0, 1.05], 10)   # Q1 low, Q2 high, Q3 normal, Q4 slight bump
noise = np.random.normal(0, 30_000, n)
revenue = trend * seasonal + noise
df = pd.DataFrame({"quarter": quarters, "revenue": revenue})
df.to_csv("tests/fixtures/quarterly_revenue.csv", index=False)
```

**Verified baselines on this dataset** (computed during research using `get_forecasting_baselines`):

| Baseline | Walk-Forward MAPE (5 folds) |
|----------|---------------------------|
| Naive | 0.0895 (8.9%) |
| Seasonal naive | 0.0608 (6.1%) |
| Ridge (starter features, alpha=1.0) | **0.0291 (2.9%)** — beats both |

The dataset is winnable from the starting template. The agent has room to improve through
Optuna tuning and feature engineering.

---

## Architecture Patterns

### Recommended Project Structure

```
scripts/
  run-forecast-validation-test.sh   # Phase 14 new harness (DO NOT modify Phase 7 script)
  run-validation-test.sh            # Phase 7 — historical record

tests/fixtures/
  iris.csv                          # Phase 4 dataset — unchanged
  noisy.csv                         # Phase 7 dataset — unchanged
  quarterly_revenue.csv             # Phase 14 dataset — NEW

.planning/phases/14-e2e-validation/
  FINDINGS.md                       # Populated after human runs the script
```

### Pattern 1: Validation Test Harness (extends Phase 7 pattern)

Phase 7's `run-validation-test.sh` is the proven template. Phase 14 creates
`run-forecast-validation-test.sh` with these differences:

**Scaffold invocation — forecasting path:**

```bash
# Phase 7 (classification)
uv run automl noisy.csv target accuracy \
    --goal "Binary classification..."

# Phase 14 (forecasting) — MUST pass --date-column
uv run automl quarterly_revenue.csv revenue mape \
    --date-column quarter \
    --goal "Forecast quarterly revenue for 40 quarters of synthetic data..." \
    --time-budget 120
```

**Claude -p invocation — identical to Phase 7:**

```bash
# CRITICAL: no --date-column needed here; the scaffolded CLAUDE.md drives the agent.
# The --allowedTools flag is REQUIRED (settings.json permissions.allow ignored in headless mode).
claude -p "Follow the CLAUDE.md protocol exactly. NEVER STOP until max-turns is reached." \
    --max-turns 50 \
    --max-budget-usd 4.00 \
    --output-format json \
    --allowedTools "Bash(*)" "Edit(*)" "Write(*)" "Read" "Glob" "Grep" \
    2>&1 | tee forecast-validation-run-output.json
```

**MAPE-specific assertion (new in Phase 14):**

The Phase 7 script only checks `stop_reason` and `json_output` presence. Phase 14
must also check that the best model beats seasonal naive. The `json_output` in
`run.log` includes `beats_seasonal_naive` field (see `train_template_forecast.py`
lines 145-147). Extract it:

```bash
# Assert best experiment beats seasonal naive
BEATS_SEASONAL=$(grep "^json_output:" run.log | tail -1 | \
    python3 -c "import json,sys; d=json.loads(sys.stdin.read().strip().replace('json_output: ','')); print(d.get('beats_seasonal_naive','unknown'))" 2>/dev/null || echo "unknown")
if [ "$BEATS_SEASONAL" = "True" ]; then
    echo "  OK: beats_seasonal_naive=True (EVAL-01 PASSED)"
else
    echo "  WARN: beats_seasonal_naive=$BEATS_SEASONAL (EVAL-01 not confirmed from last run)"
fi
```

**Keep-cycle count assertion (new in Phase 14 — EVAL-02):**

```bash
# Count all experiments in results.tsv (drafts + iterations)
if [ -f results.tsv ]; then
    EXPERIMENT_COUNT=$(( $(wc -l < results.tsv) - 1 ))
    KEEP_COUNT=$(grep -c "draft-keep\|^.*keep" results.tsv 2>/dev/null || echo 0)
    echo "  experiments total : $EXPERIMENT_COUNT"
    echo "  keep decisions    : $KEEP_COUNT"
    if [ "$EXPERIMENT_COUNT" -ge 5 ]; then
        echo "  OK: EVAL-02 -- at least 5 experiments completed (keep/revert cycles present)"
    else
        echo "  WARN: fewer than 5 experiments -- EVAL-02 may not be satisfied"
    fi
fi
```

Note: "5 keep/revert cycles" in EVAL-02 means 5 experiment outcomes (draft or iteration),
not 5 keeps. The success criterion is that the loop ran enough iterations to demonstrate
cycling behavior.

### Pattern 2: CLAUDECODE env var guard (keep from Phase 7)

```bash
if [ -n "${CLAUDECODE:-}" ]; then
    echo "ERROR: Must be run outside Claude Code session"
    exit 1
fi
```

### Pattern 3: Experiment directory naming

Phase 7 created `experiment-noisy/`. Phase 14 will create `experiment-quarterly_revenue/`
(scaffold derives name from CSV stem). Set `EXPERIMENT_DIR` accordingly:

```bash
EXPERIMENT_DIR="$PROJECT_ROOT/experiment-quarterly_revenue"
```

### Pattern 4: Frozen file check — TWO frozen files in v2.0

Phase 7 checked only `prepare.py`. Phase 14 must check BOTH frozen files:

```bash
# Check both frozen files (v2.0 has prepare.py AND forecast.py frozen)
for frozen in prepare.py forecast.py; do
    if [ -z "$(git diff HEAD -- $frozen 2>/dev/null)" ]; then
        echo "  OK: $frozen unchanged (frozen file compliance PASSED)"
    else
        echo "  FAIL: $frozen was modified! (hooks enforcement FAILED)"
    fi
done
```

### Anti-Patterns to Avoid

- **Passing `--date-column` to `claude -p`** — that flag doesn't exist for the claude CLI. `--date-column` is a `uv run automl` CLI flag. Once scaffolded, the agent reads `CLAUDE.md` which has all the forecasting instructions.
- **Modifying `run-validation-test.sh`** — Phase 7 is the historical record. Create a new script.
- **Asserting `beats_seasonal_naive` from the LAST run.log** — the last experiment may be a revert. To truly confirm EVAL-01, check if ANY kept experiment beat seasonal naive, or check `git log` for a "keep" commit. The harness should note this limitation honestly.
- **Using `iris.csv` or `noisy.csv`** — both are classification datasets. The forecasting path requires a time-indexed CSV with a date column.
- **Forgetting `--time-budget 120`** — the default is 60s but Optuna on 40 rows can run 80 trials easily in 120s. The template uses `TIME_BUDGET = 120`.
- **Hard-coding `experiment-quarterly_revenue`** — verify by checking what directory scaffold creates (it may differ if `output_dir` is specified).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parse claude -p output JSON | Custom jq / python inline | `scripts/parse_run_result.py` | Built in Phase 6 for exactly this purpose |
| Generate quarterly dataset | Custom pandas one-off | Python script in harness or standalone generator | Deterministic, reproducible |
| Compute MAPE baselines in script | Custom math in bash | Read from `program.md` (pre-computed at scaffold time) or from `json_output` in run.log | Baselines already computed by `get_forecasting_baselines()` at scaffold time |
| Walk-forward evaluation | Custom fold loops | `forecast.py::walk_forward_evaluate()` (frozen) | Agent uses frozen infrastructure; harness doesn't evaluate models |
| Scaffold invocation | Custom Python in harness | `uv run automl ... --date-column` | That's the CLI's job |

---

## Common Pitfalls

### Pitfall 1: Missing `--date-column` in scaffold invocation
**What goes wrong:** Running `uv run automl quarterly_revenue.csv revenue mape` without
`--date-column quarter` triggers the v1.0 classification/regression path. The scaffolded
`train.py` will be the standard template (no `engineer_features`, no Optuna, no MAPE
infrastructure). The loop will fail or produce meaningless results.
**How to avoid:** Always pass `--date-column quarter` to the scaffold invocation in
the harness script. Validate after scaffolding: `grep "DATE_COLUMN" experiment-*/train.py`
should return `DATE_COLUMN = "quarter"`.

### Pitfall 2: `beats_seasonal_naive` assertion on wrong run.log entry
**What goes wrong:** The harness reads `json_output` from the last line of `run.log`.
If the agent's final experiment was reverted, the last `run.log` reflects that reverted
experiment's score, not the best kept score. An agent with best_mape=0.03 that
ends on a failed experiment (mape=0.09) will show `beats_seasonal_naive=False` even
though EVAL-01 is satisfied.
**How to avoid:** The harness should note this limitation and also check `results.tsv`
for any row with `status=keep` or `status=draft-keep`. FINDINGS.md should document
the best kept MAPE and compare it to baselines manually if needed.

### Pitfall 3: Optuna trial budget causes TIME_BUDGET exceeded
**What goes wrong:** `N_TRIALS = min(50, 2 * len(y_raw))` = `min(50, 80)` = 50 trials.
With 40 rows, each Optuna trial runs `walk_forward_evaluate` (5 folds) on 40-row data.
This is fast (~0.1-0.5s per trial), so 50 trials completes in ~10-25s. However,
if the agent increases `n_splits` or adds expensive features, trials can slow down.
The 120s TIME_BUDGET should be sufficient but could trigger if the agent experiments
with expensive models (GBM with many estimators).
**How to avoid:** If `run.log` shows `TimeoutError`, note it in FINDINGS.md. The agent
should handle crashes gracefully (3-crash retry then revert per CLAUDE.md protocol).

### Pitfall 4: Confusing walk-forward MAPE with holdout MAPE
**What goes wrong:** The success criteria mentions "best model's holdout MAPE is lower
than seasonal-naive holdout MAPE". But the current architecture uses walk-forward CV
for all evaluation — there is no separate holdout evaluation in `train.py`. The
`temporal_split` function exists in `prepare.py` but the template doesn't use it.
**How to avoid:** Phase 14 FINDINGS.md should document walk-forward MAPE as the
evaluation metric (this is what `results.tsv` tracks). The success criterion's "holdout
MAPE" can be interpreted as "walk-forward MAPE on the test folds" given the current
architecture. Document this interpretation in FINDINGS.md.

### Pitfall 5: Experiment count confusion (keep/revert cycles)
**What goes wrong:** "5 keep/revert cycles" is ambiguous. The success criteria says
"at least 5 keep/revert cycles with at least one 'keep' decision". This means:
at minimum 5 experiments (drafts + iterations) must complete, AND at least one must
be a `keep` (model beats both baselines).
**How to avoid:** Count total rows in `results.tsv` (minus header). Ensure at least
one row has status `draft-keep` or `keep` (not just `draft-discard` or `revert`).

### Pitfall 6: `allowedTools` flag — exact pattern required
**What goes wrong:** Passing `--allowedTools "Bash" "Edit" "Write"` without the `(*)`
wildcards causes tool access failures in headless mode. The agent cannot run shell
commands or edit files.
**How to avoid:** Copy the exact patterns from Phase 7:
`--allowedTools "Bash(*)" "Edit(*)" "Write(*)" "Read" "Glob" "Grep"`

### Pitfall 7: `pd.date_range` freq string for quarterly
**What goes wrong:** Using `freq='Q'` instead of `freq='QS'` generates quarter-end
dates (March 31, June 30...) instead of quarter-start dates (January 1, April 1...).
`pd.infer_freq` will return `QE` for quarter-end, which looks odd in `program.md`.
**How to avoid:** Use `freq='QS'` (quarter start) for the dataset generator. The
scaffold calls `pd.infer_freq(X.index)` and puts the result in `program.md`.

---

## Code Examples

Verified patterns from project source code:

### Generate quarterly_revenue.csv (insert into harness or run once)

```python
# Source: research computation (verified against get_forecasting_baselines output)
import numpy as np
import pandas as pd

np.random.seed(42)
n = 40
quarters = pd.date_range("2014-01-01", periods=n, freq="QS")
trend = np.linspace(1_000_000, 2_000_000, n)
seasonal = np.tile([0.85, 1.1, 1.0, 1.05], 10)
noise = np.random.normal(0, 30_000, n)
revenue = trend * seasonal + noise
df = pd.DataFrame({"quarter": quarters, "revenue": revenue})
df.to_csv("tests/fixtures/quarterly_revenue.csv", index=False)
# Verified: naive MAPE=0.0895, seasonal_naive MAPE=0.0608
# Verified: Ridge (starter features) achieves MAPE=0.0291 -- beats both baselines
```

### Scaffold invocation (Phase 14 — forecasting mode)

```bash
# CRITICAL: --date-column required to trigger forecasting scaffold path
uv run automl quarterly_revenue.csv revenue mape \
    --date-column quarter \
    --goal "Forecast quarterly revenue for 40 synthetic quarters (2014-2024). \
Beat both naive (repeat last) and seasonal-naive (same quarter last year) baselines." \
    --time-budget 120
```

### Claude -p invocation (identical structure to Phase 7)

```bash
# Source: scripts/run-validation-test.sh (Phase 7 proven pattern)
# CRITICAL: --allowedTools required; settings.json permissions.allow ignored in headless mode
claude -p "Follow the CLAUDE.md protocol exactly. NEVER STOP until max-turns is reached." \
    --max-turns 50 \
    --max-budget-usd 4.00 \
    --output-format json \
    --allowedTools "Bash(*)" "Edit(*)" "Write(*)" "Read" "Glob" "Grep" \
    2>&1 | tee forecast-validation-run-output.json
```

### Verify forecasting scaffold completeness

```bash
# After scaffold, verify forecasting mode was activated
grep "DATE_COLUMN" "$EXPERIMENT_DIR/train.py"         # Should print: DATE_COLUMN = "quarter"
grep "walk_forward_evaluate" "$EXPERIMENT_DIR/train.py" # Should exist
grep -i "mape" "$EXPERIMENT_DIR/program.md" | head -5   # Should show baseline scores
ls "$EXPERIMENT_DIR/forecast.py"                       # Should exist (frozen copy)
```

### MAPE-aware beat-baseline assertion

```bash
# Source: train_template_forecast.py lines 145-147 (json_output includes beats_* fields)
# Extract beats_seasonal_naive from last json_output in run.log
if [ -f run.log ]; then
    LAST_JSON=$(grep "^json_output:" run.log | tail -1 | sed 's/^json_output: //')
    if [ -n "$LAST_JSON" ]; then
        python3 -c "
import json
d = json.loads('$LAST_JSON'.replace(\"'\", '\"'))
print('  last_mape              :', d.get('metric_value', 'N/A'))
print('  beats_naive            :', d.get('beats_naive', 'N/A'))
print('  beats_seasonal_naive   :', d.get('beats_seasonal_naive', 'N/A'))
baselines = d.get('baselines', {})
print('  naive_baseline         :', baselines.get('naive', 'N/A'))
print('  seasonal_naive_baseline:', baselines.get('seasonal_naive', 'N/A'))
" 2>/dev/null || echo "  WARN: could not parse last json_output"
    fi
fi
```

### FINDINGS.md template for Phase 14

```markdown
## Run Summary

| Field | Value |
|-------|-------|
| stop_reason | {from parse_run_result.py} |
| num_turns | {N} |
| total_cost_usd | ${X.XX} |
| experiments_run | {N drafts + N iterations} |
| best_mape | {value} (from results.tsv) |
| naive_baseline_mape | {value} (from program.md or json_output) |
| seasonal_naive_baseline_mape | {value} (from program.md or json_output) |
| beats_naive | {True/False} |
| beats_seasonal_naive | {True/False} |
| frozen_file_compliance | PASSED/FAILED |
| permission_denials | {N} |

## EVAL-01: Beat Seasonal Naive

- [ ] Best model MAPE < seasonal naive MAPE (walk-forward)
- best_mape: {value} | seasonal_naive: {value}
- Notes: {what the best kept experiment achieved}

## EVAL-02: 5+ Keep/Revert Cycles

- [ ] At least 5 experiments completed (rows in results.tsv)
- [ ] At least 1 keep decision (status=draft-keep or keep in results.tsv)
- total experiments: {N}
- keep decisions: {N}
- Notes: {describe draft phase + iteration phase behavior}

## Forecasting Loop Behavior

### Draft Phase
- [ ] 3-5 drafts generated with different algorithm families
- [ ] Best draft selected by lowest MAPE
- Notes: {draft families tried, winner}

### Keep/Revert Cycle
- [ ] git commit on keep decisions
- [ ] git reset on revert decisions
- [ ] Dual-baseline gate enforced (beats_naive AND beats_seasonal_naive checked)
- Notes: {describe first keep, first revert, any interesting patterns}

### Stagnation Handling
- [ ] Stagnation observed (5+ consecutive reverts) — if yes, describe
- Notes: {what strategy shift occurred, or "not triggered"}

## Frozen File Compliance

- [ ] prepare.py unchanged (git diff HEAD -- prepare.py empty)
- [ ] forecast.py unchanged (git diff HEAD -- forecast.py empty)
- permission_denials: {N from output JSON}
- Notes: {any hook firing observed?}

## Issues Found

| # | Category | Severity | Description |
|---|----------|----------|-------------|
| 1 | {category} | {severity} | {description} |
```

---

## State of the Art

| Old Approach (Phase 7) | Phase 14 Approach | What Changed | Impact |
|----------------------|-------------------|--------------|--------|
| Classification dataset (noisy.csv) | Quarterly time-series (quarterly_revenue.csv) | v2.0 adds forecasting | Tests the new scaffold path end-to-end |
| `uv run automl noisy.csv target accuracy` | `uv run automl quarterly_revenue.csv revenue mape --date-column quarter` | `--date-column` flag (Phase 13) | Exercises entire forecasting scaffold branch |
| One frozen file (prepare.py) | Two frozen files (prepare.py + forecast.py) | Phase 11 added forecast.py | Both files must remain unchanged |
| Standard CLAUDE.md (no MAPE gate) | `claude_forecast.md.tmpl` (dual-baseline gate) | Phase 12 | Agent enforces beats_naive AND beats_seasonal_naive for every keep |
| Metric: accuracy (maximize) | Metric: MAPE (minimize) | v2.0 core change | Harness must check lower=better, not higher=better |
| `json_output` without baseline fields | `json_output` includes `beats_naive`, `beats_seasonal_naive` | Phase 12 template | Enables automated EVAL-01 assertion |
| Single keep gate (best accuracy) | Dual-baseline gate (beat naive + seasonal naive) | Phase 12 | Agent cannot keep if it fails to beat either baseline |
| Walk-forward: N/A (standard CV) | Walk-forward: `walk_forward_evaluate()` (5 folds) | Phase 11 | Evaluation is temporally correct; no data leakage |

---

## Open Questions

1. **Will the agent beat seasonal naive within 50 turns?**
   - What we know: Ridge with starter features achieves MAPE=0.029, well below seasonal_naive=0.061. The starting template already beats the baseline. Any draft with a reasonable model and the provided `engineer_features` should succeed on the first or second draft.
   - What's unclear: If the agent introduces a bug (e.g., removes dropna() causing NaN errors), it may spend turns in crash recovery. The 3-crash-then-revert protocol handles this.
   - Recommendation: EVAL-01 should be satisfied within the first few experiments. Document the first experiment that achieved a keep.

2. **How long do forecasting experiments take vs. classification?**
   - What we know: 40 rows, 5-fold walk-forward, 50 Optuna trials. With Ridge, each trial takes ~0.05s = 2.5s total Optuna + overhead ≈ 5-10s per experiment. With GBM (100 estimators), each trial may take 0.3-0.5s = 15-25s total = 25-30s per experiment.
   - What's unclear: The agent may use expensive models. With `TIME_BUDGET=120`, even slow models should complete.
   - Recommendation: 50 turns at 10-30s each = 500-1500s = 8-25 minutes wall clock. Budget cap at $4.00 with headroom.

3. **Will `pd.infer_freq` detect 'QS' correctly for program.md?**
   - What we know: `_format_forecast_summary` in scaffold.py calls `pd.infer_freq(X.index)`. With `freq='QS'` and 40 rows, pandas should infer `'QS-JAN'` or `'QS'`.
   - What's unclear: The exact string returned by `pd.infer_freq` for quarterly start may vary by pandas version.
   - Recommendation: Verify during Task 1 by inspecting `program.md` after scaffolding. Either value is acceptable.

4. **Is there a risk the dual-baseline gate prevents ANY keeps?**
   - What we know: Empirically, Ridge with default features achieves MAPE=0.029 < seasonal_naive=0.061. The very first draft should pass the gate. The baseline-gate risk is only if the agent's model is somehow worse than naive (MAPE > 0.09), which would require a fundamentally broken model.
   - Recommendation: Low risk. If no keeps are observed, the agent likely has a bug in model_fn (e.g., returning constant predictions). Document in FINDINGS.md.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths=["tests"] |
| Quick run command | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` |
| Full suite command | `uv run pytest tests/ -q` |
| Estimated runtime | ~20s (313 tests currently passing) |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVAL-01 | quarterly_revenue.csv fixture is correct (40 rows, date + revenue columns) | smoke | `python3 -c "import pandas as pd; df=pd.read_csv('tests/fixtures/quarterly_revenue.csv'); assert len(df)==40; assert 'quarter' in df.columns; assert 'revenue' in df.columns; print('OK')"` | No — Wave 0 |
| EVAL-01 | run-forecast-validation-test.sh passes bash syntax | smoke | `bash -n scripts/run-forecast-validation-test.sh` | No — Wave 0 |
| EVAL-01 | beat seasonal naive (beats_seasonal_naive=True) | manual | Inspect `run.log` json_output after human run | N/A |
| EVAL-02 | at least 5 experiments completed | manual | Count rows in `results.tsv` after human run | N/A |
| EVAL-02 | at least 1 keep decision | manual | Check `results.tsv` for `draft-keep` or `keep` status | N/A |

### Sampling Rate

- **Per task commit (Task 1):** `uv run pytest tests/ -q --ignore=tests/test_e2e.py`
- **After Task 2 (human gate):** No automated test — human provides run output
- **Phase gate (before /gsd:verify-work):** Full suite green + FINDINGS.md populated with all required fields

### Wave 0 Gaps

- [ ] `tests/fixtures/quarterly_revenue.csv` — covers EVAL-01 fixture requirement (generated in Task 1)
- [ ] `tests/test_phase14_validation.py` — smoke tests for fixture and harness script (pattern from `tests/test_phase7_validation.py`)
- [ ] `scripts/run-forecast-validation-test.sh` — the harness script itself (Task 1 primary deliverable)

*(Existing 313 tests cover all src/ modules; no gaps in unit infrastructure.)*

---

## Plan Structure (Recommended)

Phase 14 maps to the Phase 7 plan structure: one plan, three sequential tasks.

| Task | Type | Description |
|------|------|-------------|
| Task 1 | `auto` | Generate `quarterly_revenue.csv`, write `scripts/run-forecast-validation-test.sh`, write `tests/test_phase14_validation.py` |
| Task 2 | `checkpoint:human-action` (blocking) | User runs the validation script outside Claude Code; provides output |
| Task 3 | `auto` | Analyze results, populate `FINDINGS.md`, certify EVAL-01 and EVAL-02 |

**Single plan is appropriate.** Tasks are sequentially dependent. Task 2 is a human gate
(claude -p cannot run inside Claude Code). No parallelism possible.

**`autonomous: false`** — same as Phase 7, because Task 2 requires human execution of
`claude -p` outside Claude Code.

---

## Sources

### Primary (HIGH confidence)

- `scripts/run-validation-test.sh` — Phase 7 harness; structural template for Phase 14
- `src/automl/scaffold.py` — verified: `date_col` branch, `_format_forecast_baselines`, `_render_forecast_program_md`
- `src/automl/forecast.py` — verified: `get_forecasting_baselines`, `walk_forward_evaluate` signatures and behavior
- `src/automl/train_template_forecast.py` — verified: `json_output` includes `beats_naive` and `beats_seasonal_naive`
- `src/automl/templates/claude_forecast.md.tmpl` — verified: dual-baseline gate rule, MAPE direction rule, frozen file rule
- `src/automl/cli.py` — verified: `--date-column` flag wired through to `scaffold_experiment(date_col=...)`
- `.planning/phases/07-e2e-validation-test/FINDINGS.md` — Phase 7 run observations (template for FINDINGS.md)
- `.planning/phases/07-e2e-validation-test/07-RESEARCH.md` — Phase 7 research patterns
- `.planning/STATE.md` — decisions block (Phase 12 MAPE direction, dual-baseline gate, Phase 13 scaffold decisions)
- Research computation — `get_forecasting_baselines` run on synthetic dataset; Ridge MAPE verified at 0.029

### Secondary (MEDIUM confidence)

- `tests/test_phase7_validation.py` — pattern for `test_phase14_validation.py` test structure

### Tertiary (LOW confidence)

- None

---

## Metadata

**Confidence breakdown:**

- Plan structure: HIGH — Phase 7 is a proven template; Phase 14 is structurally identical with forecasting-specific differences
- Dataset: HIGH — baselines and Ridge performance empirically verified during research using actual project code
- Beat-baseline achievability: HIGH — Ridge with starter features achieves MAPE=0.029 vs seasonal_naive=0.061; verified
- Harness assertions: HIGH — json_output format with `beats_seasonal_naive` verified from train_template_forecast.py source
- Agent behavior (50 turns): MEDIUM — agent will follow claude_forecast.md.tmpl but behavior in live run is probabilistic

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable domain — all infrastructure is frozen)
