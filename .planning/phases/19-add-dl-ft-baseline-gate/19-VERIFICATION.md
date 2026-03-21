---
phase: 19-add-dl-ft-baseline-gate
verified: 2026-03-20T00:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 19: Add DL/FT Baseline Gate Verification Report

**Phase Goal:** Implement baseline computation and gate enforcement for DL and FT domains so the dual-baseline gate applies to all domains, not just tabular
**Verified:** 2026-03-20
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | DL experiments compute random and most_frequent baselines from labels before loop starts | VERIFIED | `_compute_dl_baselines()` calls `_load_dl_labels()` then `dl_baselines(labels, metric, task)` at line 564-573 of engine.py; `state.baselines` populated before loop (line 99) |
| 2 | FT experiments compute theoretical loss/perplexity baselines before loop starts | VERIFIED | `_compute_ft_baselines()` calls `ft_baselines(metric, vocab_size)` with `log(vocab_size)` at line 618-623 of engine.py; no model loading required |
| 3 | DL/FT experiments that fail to beat baselines are downgraded from keep to revert | VERIFIED | `passes_baseline_gate` (imported from tabular/baselines.py at line 36) called in `_process_result` at lines 232-242 — domain-agnostic, applies whenever `state.baselines` is non-None |
| 4 | Engine gracefully returns None when DL label extraction fails | VERIFIED | `_load_dl_labels()` returns None on missing `dataset_path`, missing directory, empty class dirs, or any exception (lines 575-616); `_compute_dl_baselines` propagates None (line 567-568) |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mlforge/deeplearning/baselines.py` | DL baseline computation via DummyClassifier | VERIFIED | 64 lines; exports `compute_baselines(labels, scoring, task)`; classification path uses StratifiedKFold + DummyClassifier; loss path uses theoretical cross-entropy |
| `src/mlforge/finetuning/baselines.py` | FT baseline computation via theoretical bounds | VERIFIED | 39 lines; exports `compute_baselines(metric, vocab_size=32000)`; loss: `log(vocab_size)`; perplexity: `float(vocab_size)` |
| `src/mlforge/engine.py` | Domain dispatch in `_compute_baselines` for deeplearning and finetuning | VERIFIED | Lines 516-534: explicit dispatch to `_compute_tabular_baselines`, `_compute_dl_baselines`, `_compute_ft_baselines`; unknown domains return None |
| `tests/mlforge/test_dl_baselines.py` | Unit tests for DL baseline computation | VERIFIED | 12 tests across `TestDLComputeBaselinesClassification` and `TestDLComputeBaselinesLoss`; all pass |
| `tests/mlforge/test_ft_baselines.py` | Unit tests for FT baseline computation | VERIFIED | 8 tests across `TestFTComputeBaselinesLoss`, `TestFTComputeBaselinesPerplexity`, `TestFTComputeBaselinesCustomVocab`; all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/mlforge/engine.py` | `src/mlforge/deeplearning/baselines.py` | lazy import in `_compute_dl_baselines` when `domain=='deeplearning'` | WIRED | Line 570: `from mlforge.deeplearning.baselines import compute_baselines as dl_baselines` |
| `src/mlforge/engine.py` | `src/mlforge/finetuning/baselines.py` | lazy import in `_compute_ft_baselines` when `domain=='finetuning'` | WIRED | Line 620: `from mlforge.finetuning.baselines import compute_baselines as ft_baselines` |
| `src/mlforge/engine.py` | `src/mlforge/tabular/baselines.py` | `passes_baseline_gate` already imported and used in `_process_result` | WIRED | Line 36 (top-level import), lines 232-242 (`_process_result` gate enforcement) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| INTL-01 | 19-01-PLAN.md | Baseline establishment runs naive + domain-specific baselines before agent starts experimenting | SATISFIED | DL baselines (DummyClassifier) and FT baselines (theoretical bounds) computed at engine startup via `_compute_baselines()` called before loop (engine.py line 99) |
| INTL-02 | 19-01-PLAN.md | Dual-baseline gate requires agent to beat both naive and domain-specific baselines before keeping an experiment | SATISFIED | `passes_baseline_gate` in `_process_result` applies gate to all domains whenever `state.baselines` is non-None; 6 engine dispatch tests verify DL/FT baseline population and gate application |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No TODO, FIXME, placeholder, or stub patterns found in the new or modified files. No torch/transformers imports in `deeplearning/baselines.py` or `finetuning/baselines.py`.

### Human Verification Required

None — all phase behaviors have automated verification. The gate enforcement logic is tested via mocked engine runs (test_baselines_computed_for_finetuning verifies the metric value 2.0 passes a minimize gate since 2.0 < log(32000) ~= 10.4).

### Test Suite Results

| Test command | Result |
|---|---|
| `python3 -m pytest tests/mlforge/test_dl_baselines.py tests/mlforge/test_ft_baselines.py -x -q` | 20 passed |
| `python3 -m pytest tests/mlforge/test_engine.py -k "baselines" -x -q` | 6 passed |
| `python3 -m pytest tests/mlforge/ -x -q` | 555 passed |
| `python3 -m pytest tests/ -x -q` | 1 failed (pre-existing), 581 passed |

The single failure (`tests/test_cli.py::test_cli_valid_args` — "string dtypes are not allowed") is pre-existing. Git history confirms this test file was last modified in commit `b8f24a5` (Phase 13), which predates Phase 19. Phase 19 made no changes to `tests/test_cli.py` or `tests/test_e2e.py`.

### Gaps Summary

No gaps. All four observable truths are verified. All five artifacts exist and are substantive and wired. All three key links are confirmed present in the actual code. Requirements INTL-01 and INTL-02 are both satisfied with direct implementation evidence.

---

_Verified: 2026-03-20_
_Verifier: Claude (gsd-verifier)_
