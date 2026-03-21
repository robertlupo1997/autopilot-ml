# Phase 16: Wire Template Runtime Artifacts - Research

**Researched:** 2026-03-20
**Domain:** Jinja2 template modification, scikit-learn model persistence, CSV output
**Confidence:** HIGH

## Summary

This phase closes two integration gaps (INT-01 and INT-02) identified in the v1.0 re-audit: the tabular train template (`tabular_train.py.j2`) never writes `predictions.csv` and never saves `best_model.joblib`. Both files are expected by existing infrastructure -- `engine.py:_run_diagnostics()` reads `predictions.csv` and `export.py:export_artifact()` reads `best_model.joblib`. The code that consumes these artifacts is already built and tested; the only missing piece is the template producing them.

The changes are straightforward Jinja2 template edits plus a CLAUDE.md rule addition. The DL template (`dl_train.py.j2`) already demonstrates the pattern: it saves `best_model.pt` via `torch.save()` at line 213 during the early-stopping best-checkpoint save. The tabular template needs an analogous pattern using `joblib.dump()` for the model and `pandas.DataFrame.to_csv()` for predictions.

**Primary recommendation:** After the Optuna study completes, retrain the best model on full training data, generate test-set predictions as a CSV with columns `y_true` and `y_pred`, and save the model via `joblib.dump()`. Add a CLAUDE.md domain rule preserving these artifact writes.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Write predictions.csv with test set predictions after model training
- Columns: actual, predicted (and index if available)
- Written after best trial completes (not every trial) -- matches the keep-only pattern
- Full test set predictions, not just misses
- Save full trained model via joblib.dump() as best_model.joblib
- Model only (not full pipeline) -- keep it simple, match what export_artifact() expects
- No sidecar metadata file -- metric/params already tracked in experiment journal
- Add clear instruction in templates: "preserve predictions.csv and best_model.joblib writes"
- Treat as frozen behavior -- agent should not remove these writes
- Brief explanation of WHY: "diagnostics and export depend on these files"

### Claude's Discretion
- Exact placement of artifact writes in template code
- Whether to also update DL/FT templates (only tabular is required by success criteria)
- Error handling approach for write failures
- Test strategy for template artifact writes

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTL-03 | Diagnostics engine analyzes WHERE the model fails (worst predictions, bias direction, feature correlations) | predictions.csv with y_true/y_pred columns enables _run_diagnostics() which calls diagnose_regression/diagnose_classification |
| UX-03 | Best model artifact exported with metadata (metric, config, training history) after session completes | best_model.joblib enables export_artifact() which copies model + writes metadata.json sidecar |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| joblib | (bundled with sklearn) | Model serialization | Standard sklearn pattern; what export_artifact() expects |
| pandas | (already imported via prepare.py) | CSV output | DataFrame.to_csv for predictions.csv |
| Jinja2 | 3.x (already in deps) | Template rendering | Existing template engine |

### Supporting
No new dependencies required. All needed libraries are already available in the rendered train.py environment.

## Architecture Patterns

### Current Template Flow (tabular_train.py.j2)
```
1. Define objective() with Optuna trial
2. In __main__: create study, optimize, print JSON result
```

### Required Template Flow (after this phase)
```
1. Define objective() with Optuna trial          [unchanged]
2. In __main__: create study, optimize            [unchanged]
3. Retrain best model on full train data          [NEW]
4. Generate predictions on test set               [NEW]
5. Write predictions.csv (y_true, y_pred)         [NEW]
6. Save best_model.joblib via joblib.dump()       [NEW]
7. Print JSON result                              [unchanged - must remain LAST]
```

### Column Name Contract
The engine's `_run_diagnostics()` method (engine.py line 426-427) reads:
```python
y_true = df["y_true"].values
y_pred = df["y_pred"].values
```

**CRITICAL:** The CONTEXT.md says "columns: actual, predicted" but the engine expects `y_true` and `y_pred`. The template MUST use `y_true` and `y_pred` as column names to match the existing consumer. The user's "actual, predicted" description is conceptual, not literal column names.

### Pattern: Post-Study Retraining
After `study.optimize()`, the best hyperparameters are in `study.best_params`. The template must:
1. Reconstruct the best model from `study.best_params`
2. Fit on `X_train_processed`
3. Predict on `X_test_processed`
4. Save predictions and model

This requires the train/test split and preprocessor to be accessible outside `objective()`. Currently they are created inside `objective()` on every trial call. The template needs restructuring to make the data available in the `__main__` block.

### Pattern: DL Template Reference (dl_train.py.j2 line 213)
```python
torch.save(model.state_dict(), "best_model.pt")
```
The DL template saves during early stopping. The tabular template will save after study completion (different pattern, same principle).

### CLAUDE.md Rule Placement
The `base_claude.md.j2` template has a `## Domain Rules` section rendered from `domain_rules` list in `TabularPlugin.template_context()`. The new rule should be added to this list in the plugin.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model serialization | Custom pickle/save | `joblib.dump(model, "best_model.joblib")` | joblib handles large numpy arrays efficiently; matches export_artifact() expectations |
| CSV predictions | Manual string formatting | `pd.DataFrame({"y_true": y_test, "y_pred": preds}).to_csv("predictions.csv", index=False)` | Handles edge cases (quoting, encoding); clean column names |
| Model reconstruction | Re-running Optuna | Reconstruct from `study.best_params` with if/elif chain | study.best_params gives exact hyperparameters; no need to re-optimize |

## Common Pitfalls

### Pitfall 1: Column Name Mismatch
**What goes wrong:** Using "actual"/"predicted" column names instead of "y_true"/"y_pred"
**Why it happens:** CONTEXT.md describes columns conceptually; engine.py hardcodes `y_true`/`y_pred`
**How to avoid:** Use `y_true` and `y_pred` exactly -- verified from engine.py line 426-427
**Warning signs:** _run_diagnostics() silently fails with KeyError, no diagnostics.md produced

### Pitfall 2: Data Not Accessible After Study
**What goes wrong:** train/test data and preprocessor are only available inside `objective()` scope
**Why it happens:** Current template creates data inside the Optuna objective function
**How to avoid:** Move data loading/splitting to module level or `__main__` block, pass into objective via closure or recreate after study
**Warning signs:** NameError when trying to access X_test_processed in __main__

### Pitfall 3: JSON Output Must Remain Last
**What goes wrong:** Predictions/model save code placed after the `print(json.dumps(...))` call
**Why it happens:** Developer adds artifact writes at the end of the file
**How to avoid:** Insert artifact writes BEFORE the final JSON print -- the engine parses the last JSON line
**Warning signs:** Engine can't parse metric, experiments auto-revert

### Pitfall 4: joblib Import Missing
**What goes wrong:** Template uses joblib.dump() but doesn't import joblib
**Why it happens:** joblib is available (comes with sklearn) but needs explicit import
**How to avoid:** Add `import joblib` to template imports section
**Warning signs:** NameError at runtime

### Pitfall 5: Model vs Pipeline Confusion
**What goes wrong:** Saving the preprocessor+model pipeline instead of just the model
**Why it happens:** sklearn Pipeline pattern is common
**How to avoid:** User decision: "Model only (not full pipeline)" -- save just the fitted estimator
**Warning signs:** export_artifact copies a larger-than-expected file, but functionally OK

## Code Examples

### Predictions CSV Write (matches engine.py consumer)
```python
# Source: engine.py lines 420-427 (consumer contract)
import pandas as pd

# After retraining best model on train data:
preds = best_model.predict(X_test_processed)
pred_df = pd.DataFrame({"y_true": y_test, "y_pred": preds})
pred_df.to_csv("predictions.csv", index=False)
```

### Model Save (matches export.py consumer)
```python
# Source: export.py lines 35-36 (consumer contract)
import joblib

joblib.dump(best_model, "best_model.joblib")
```

### Best Model Reconstruction from Optuna
```python
# After study.optimize():
best_params = study.best_params
model_name = best_params["model"]

# Regression example:
if model_name == "rf":
    best_model = RandomForestRegressor(
        n_estimators=best_params["n_estimators"],
        max_depth=best_params["max_depth"],
        random_state=42,
    )
elif model_name == "ridge":
    best_model = Ridge(alpha=best_params["alpha"])

best_model.fit(X_train_processed, y_train)
```

### CLAUDE.md Rule Addition (TabularPlugin.template_context)
```python
# Add to rules list in template_context():
"Do NOT remove predictions.csv or best_model.joblib writes -- diagnostics and export depend on these files"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Template only prints JSON | Template writes artifacts + prints JSON | Phase 16 | Enables diagnostics and export pipelines |

**No deprecated/outdated concerns** -- this is straightforward Jinja2 template modification.

## Open Questions

1. **Should DL/FT templates also get predictions.csv?**
   - What we know: Only tabular is required by success criteria. DL template already saves best_model.pt. Neither DL nor FT write predictions.csv.
   - What's unclear: Whether diagnostics should work for DL/FT domains
   - Recommendation: Skip for now -- tabular only. DL/FT can be added later if needed.

2. **Error handling for write failures**
   - What we know: Disk full or permission errors could prevent artifact writes
   - What's unclear: Whether to wrap in try/except or let it fail loudly
   - Recommendation: Let it fail -- if the filesystem can't write, the experiment has bigger problems. The engine already handles crash status.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml (pytest section) |
| Quick run command | `python3 -m pytest tests/ -x -q` |
| Full suite command | `python3 -m pytest tests/ -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTL-03 | tabular_train.py.j2 rendered output contains predictions.csv write with y_true/y_pred columns | unit | `python3 -m pytest tests/test_tabular_template_artifacts.py -x` | No -- Wave 0 |
| INTL-03 | _run_diagnostics() finds and processes predictions.csv | unit | `python3 -m pytest tests/test_tabular_template_artifacts.py -x` | No -- Wave 0 |
| UX-03 | tabular_train.py.j2 rendered output contains joblib.dump best_model.joblib | unit | `python3 -m pytest tests/test_tabular_template_artifacts.py -x` | No -- Wave 0 |
| UX-03 | export_artifact() finds best_model.joblib and exports with metadata | unit | Existing test in test suite | Yes |
| INTL-03+UX-03 | CLAUDE.md template includes artifact preservation rule | unit | `python3 -m pytest tests/test_tabular_template_artifacts.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_tabular_template_artifacts.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -q`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
- [ ] `tests/test_tabular_template_artifacts.py` -- tests for rendered template containing predictions.csv write, joblib.dump, correct column names, and CLAUDE.md rule
- No new framework install needed -- pytest already configured

## Sources

### Primary (HIGH confidence)
- `src/mlforge/engine.py` lines 414-437 -- _run_diagnostics() reads predictions.csv with y_true/y_pred columns
- `src/mlforge/export.py` lines 19-58 -- export_artifact() reads best_model.joblib
- `src/mlforge/templates/tabular_train.py.j2` -- current template (no artifact writes)
- `src/mlforge/templates/dl_train.py.j2` line 213 -- DL model save pattern reference
- `src/mlforge/tabular/__init__.py` -- TabularPlugin.template_context() for domain rules
- `src/mlforge/templates/base_claude.md.j2` -- CLAUDE.md template structure

### Secondary (MEDIUM confidence)
- CONTEXT.md user decisions on column naming (conceptual "actual/predicted" vs literal y_true/y_pred)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new deps, all libraries already in environment
- Architecture: HIGH -- consumer code is read directly, column contract verified
- Pitfalls: HIGH -- all pitfalls derived from reading actual source code

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable -- template modification, no moving targets)
