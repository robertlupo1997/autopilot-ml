---
phase: 17-wire-dl-ft-artifact-export-diagnostics
verified: 2026-03-20T00:00:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 17: Wire DL/FT Artifact Export and Diagnostics Verification Report

**Phase Goal:** Make artifact export, diagnostics, and swarm verification work for DL and FT domains, not just tabular
**Verified:** 2026-03-20
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | export_artifact() finds and exports .pt files for DL domain | VERIFIED | `_MODEL_CANDIDATES` ordered list with `("best_model.pt", False)` at index 1; `test_export_artifact_pt_file` PASSED |
| 2  | export_artifact() finds and exports best_adapter/ directory for FT domain | VERIFIED | `("best_adapter", True)` at index 2 with `shutil.copytree()`; `test_export_artifact_adapter_dir` PASSED |
| 3  | verify_best_result() uses "python train.py" as default eval command (no --eval-only) | VERIFIED | `eval_script: str = "python train.py"` at line 21 in verifier.py; `test_verify_default_eval_script` PASSED |
| 4  | _run_diagnostics() correctly calls diagnose_classification for image_classification and text_classification tasks | VERIFIED | `_CLASSIFICATION_TASKS` frozenset includes both; tests for image_classification, text_classification, and custom task type dispatch all PASSED |
| 5  | DL train template writes predictions.csv with y_true and y_pred columns after training | VERIFIED | `pd.DataFrame({"y_true": all_labels, "y_pred": all_preds}).to_csv("predictions.csv", ...)` at line 246 of dl_train.py.j2 |
| 6  | FT train template writes predictions.csv with per-sample loss values for loss/perplexity metrics | VERIFIED | Loss-guarded write at line 209-222 of ft_train.py.j2; `test_ft_template_writes_predictions` and `test_ft_template_predictions_guarded` PASSED |
| 7  | DL CLAUDE.md protocol includes artifact preservation rule for predictions.csv and best_model.pt | VERIFIED | Rule at deeplearning/__init__.py line 98; `test_dl_template_context_artifact_rule` PASSED |
| 8  | FT CLAUDE.md protocol includes artifact preservation rule for predictions.csv and best_adapter | VERIFIED | Rule at finetuning/__init__.py line 91; `test_ft_template_context_artifact_rule` PASSED |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mlforge/export.py` | Multi-format artifact discovery and export | VERIFIED | `_MODEL_CANDIDATES` list, `shutil.copytree()` for directories, `shutil.copy2()` for files; 8 tests pass |
| `src/mlforge/swarm/verifier.py` | Domain-agnostic eval command default | VERIFIED | Default `eval_script = "python train.py"` (no --eval-only); docstring updated to explain rationale |
| `src/mlforge/engine.py` | DL/FT task type mapping in diagnostics | VERIFIED | `_CLASSIFICATION_TASKS` frozenset at module level includes image_classification, text_classification, custom; normalized task_type passed to `_format_diagnostics` |
| `src/mlforge/templates/dl_train.py.j2` | Predictions.csv write after DL training | VERIFIED | Best model reloaded via state dict, inference over val_loader, `.cpu().numpy()` GPU safety, `to_csv("predictions.csv")` before JSON output |
| `src/mlforge/templates/ft_train.py.j2` | Predictions.csv write after FT training (loss-based) | VERIFIED | Guarded by `if METRIC in ("perplexity", "loss")`, per-sample loss collected, `to_csv("predictions.csv")` before JSON output |
| `src/mlforge/deeplearning/__init__.py` | Artifact preservation domain rule | VERIFIED | Rule mentions both `predictions.csv` and `best_model.pt` |
| `src/mlforge/finetuning/__init__.py` | Artifact preservation domain rule | VERIFIED | Rule mentions both `predictions.csv` and `best_adapter` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/mlforge/export.py` | `best_model.pt`, `best_adapter/` | Ordered candidate search with file/dir distinction | WIRED | `_MODEL_CANDIDATES` iterated; `is_dir` flag distinguishes file vs directory copy path |
| `src/mlforge/engine.py` | `src/mlforge/intelligence/diagnostics.py` | Task type mapping before diagnose call | WIRED | `_CLASSIFICATION_TASKS` set membership check at line 436; `diagnose_classification` or `diagnose_regression` called; normalized `task_type` passed to `_format_diagnostics` |
| `src/mlforge/templates/dl_train.py.j2` | `predictions.csv` | pandas DataFrame.to_csv after val inference | WIRED | `pd.DataFrame({"y_true": all_labels, "y_pred": all_preds}).to_csv("predictions.csv", index=False)` at line 246 |
| `src/mlforge/templates/ft_train.py.j2` | `predictions.csv` | pandas DataFrame.to_csv with per-sample loss | WIRED | `pd.DataFrame({"y_true": [0.0] * len(all_losses), "y_pred": all_losses}).to_csv("predictions.csv", index=False)` at line 222 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DL-04 | 17-02-PLAN.md | Plugin generates domain-specific CLAUDE.md protocol with deep learning rules and anti-patterns | SATISFIED | Artifact preservation rule added to `template_context()` in deeplearning/__init__.py at line 98; 11 total domain rules now present |
| FT-04 | 17-02-PLAN.md | Plugin generates domain-specific CLAUDE.md protocol with fine-tuning rules and anti-patterns | SATISFIED | Artifact preservation rule added to `template_context()` in finetuning/__init__.py at line 91; 11 total domain rules now present |
| UX-03 | 17-01-PLAN.md | Best model artifact exported with metadata (metric, config, training history) after session completes | SATISFIED | export_artifact() now handles .joblib, .pt, and best_adapter/ directory in priority order with metadata.json sidecar |
| SWARM-04 | 17-01-PLAN.md | Verification agent checks metric improvement claims against actual holdout performance | SATISFIED | verify_best_result() default eval_script fixed to "python train.py" — functional across all three domain templates |
| INTL-03 | Both PLANs | Diagnostics engine analyzes WHERE the model fails (worst predictions, bias direction, feature correlations) | SATISFIED | _run_diagnostics() correctly dispatches DL/FT task types; DL/FT templates write predictions.csv so diagnostics engine can fire for all three domains |

Note: REQUIREMENTS.md traceability table lists DL-04 as "Phase 8 Complete", FT-04 as "Phase 15 Complete", UX-03 as "Phase 16 Complete", SWARM-04 as "Phase 14 Complete", and INTL-03 as "Phase 16 Complete". Phase 17 extends these capabilities to DL/FT domains — the requirements are satisfied more completely now, but the traceability table was not updated to reflect phase 17's contribution. This is a documentation gap, not a code gap.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/mlforge/templates/dl_train.py.j2` | 50, 89, 96 | TODO comments | Info | Intentional — inside `{% if task == "custom" %}` block; these are instructions to the user for the custom task scaffold pattern, not implementation stubs |

No blockers or warnings found.

### Human Verification Required

None. All observable behaviors are mechanically verifiable:
- File/directory detection uses `is_file()` / `is_dir()` — deterministic
- Default parameter value is code-level, not runtime-dependent
- Frozenset membership check is code-level
- Template string presence is testable via rendering

### Test Results

| Test Suite | Before Phase 17 | After Phase 17 | New Tests |
|-----------|----------------|----------------|-----------|
| `tests/mlforge/test_export.py` | 5 tests | 8 tests | +3 (.pt file, adapter dir, priority order) |
| `tests/mlforge/test_swarm.py` | existing | +1 | +1 (default eval_script check) |
| `tests/mlforge/test_engine.py` | existing | +4 | +4 (image_classification, text_classification, custom, normalized task_type) |
| `tests/mlforge/test_templates.py` | existing | +9 | +9 (DL/FT predictions, artifact rules) |
| **mlforge module total** | 512 | 529 | **+17** |

All 529 mlforge module tests pass. The 33 failures in `tests/` root are pre-existing failures unrelated to phase 17 (they fail in the legacy test_scaffold.py, test_e2e.py, test_prepare.py, test_cli.py, and test_train.py files from older milestone architectures).

### Gaps Summary

None. All 8 observable truths are verified, all artifacts exist and are substantive, all key links are wired.

---

_Verified: 2026-03-20_
_Verifier: Claude (gsd-verifier)_
