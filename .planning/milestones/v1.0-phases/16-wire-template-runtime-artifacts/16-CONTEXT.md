# Phase 16: Wire Template Runtime Artifacts - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Make tabular_train.py.j2 write predictions.csv and best_model.joblib so the existing diagnostics engine and artifact export actually fire at runtime. Update CLAUDE.md templates to instruct agent to preserve these writes.

</domain>

<decisions>
## Implementation Decisions

### Predictions output
- Write predictions.csv with test set predictions after model training
- Columns: actual, predicted (and index if available)
- Written after best trial completes (not every trial) — matches the keep-only pattern
- Full test set predictions, not just misses

### Model persistence
- Save full trained model via joblib.dump() as best_model.joblib
- Model only (not full pipeline) — keep it simple, match what export_artifact() expects
- No sidecar metadata file — metric/params already tracked in experiment journal

### CLAUDE.md rules
- Add clear instruction in templates: "preserve predictions.csv and best_model.joblib writes"
- Treat as frozen behavior — agent should not remove these writes
- Brief explanation of WHY: "diagnostics and export depend on these files"

### Claude's Discretion
- Exact placement of artifact writes in template code
- Whether to also update DL/FT templates (only tabular is required by success criteria)
- Error handling approach for write failures
- Test strategy for template artifact writes

</decisions>

<specifics>
## Specific Ideas

No specific requirements — follow the existing DL template pattern (dl_train.py.j2 already saves best_model.pt via torch.save) and adapt for tabular's joblib approach.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine.py:_run_diagnostics()` (line 414): Already looks for `predictions.csv` in experiment_dir
- `export.py:export_artifact()` (line 19): Already looks for `best_model.joblib`, copies to artifacts dir
- `dl_train.py.j2` (line 213): Saves `best_model.pt` via `torch.save()` — pattern to follow

### Established Patterns
- Templates print JSON metrics via `json.dumps()` at end of execution
- DL template saves model state dict after training completes
- Engine calls `_run_diagnostics()` after both keep and revert in `_process_result`

### Integration Points
- `tabular_train.py.j2` → writes `predictions.csv` → `engine.py:_run_diagnostics()` reads it
- `tabular_train.py.j2` → writes `best_model.joblib` → `export.py:export_artifact()` reads it
- `base_claude.md.j2` → instructs agent to preserve artifact writes

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-wire-template-runtime-artifacts*
*Context gathered: 2026-03-20*
