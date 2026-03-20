---
phase: 12-wire-plugin-validation-task-mapping
verified: 2026-03-20T22:30:00Z
status: passed
score: 5/5 must-haves verified
---

# Phase 12: Wire Plugin Validation + Task Type Mapping — Verification Report

**Phase Goal:** Call validate_config() before scaffolding and map profiler task types to DL/FT expected types so simple mode works for all domains
**Verified:** 2026-03-20T22:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Invalid configs are rejected before scaffolding with clear error messages | VERIFIED | `scaffold_experiment()` calls `plugin.validate_config()` at lines 168-173 before `plugin.scaffold()`. Tests `TestScaffoldValidation` (5 tests) pass — invalid tabular metric, missing FT model_name, invalid DL task all raise `ValueError`. |
| 2 | Profiler task types map to DL-specific types so simple mode works for all domains | VERIFIED | `_map_task_for_domain()` at scaffold.py:98-115 translates `classification -> image_classification` and `regression -> custom` for DL domain. Runs at line 165 before validation and before `plugin.scaffold()`. DL `scaffold()` uses the mapped value to select model architecture (resnet50 vs distilbert). |
| 3 | FineTuningPlugin rejects missing model_name with actionable error | VERIFIED | FT `validate_config()` at finetuning/__init__.py:112-115 returns error `"plugin_settings missing 'model_name' -- required for fine-tuning"`. Test `test_rejects_ft_without_model_name` passes (raises `ValueError` matching "model_name"). |
| 4 | DL-native task types (image_classification, text_classification) pass through unmapped | VERIFIED | `_map_task_for_domain()` only remaps if `current_task in domain_map`. `image_classification` and `text_classification` are not in `_TASK_TYPE_MAP["deeplearning"]` so they pass through. Test `test_dl_native_task_not_remapped` passes. |
| 5 | Tabular task types pass through unchanged | VERIFIED | `_TASK_TYPE_MAP` has no entry for `"tabular"` domain — `_map_task_for_domain()` returns early. Tests `test_tabular_task_passthrough` and `test_ft_task_no_mapping` pass. |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mlforge/scaffold.py` | validate_config() call + _map_task_for_domain() function | VERIFIED | `_TASK_TYPE_MAP` dict at line 90, `_map_task_for_domain()` function at line 98, validate_config() call at line 168, `_map_task_for_domain()` called at line 165 — all substantive, all wired into `scaffold_experiment()`. |
| `tests/mlforge/test_scaffold.py` | Tests for validation wiring and task mapping | VERIFIED | `TestScaffoldValidation` (5 tests: nonexistent dataset, invalid tabular metric, FT missing model_name, DL invalid task, valid config regression check) and `TestTaskTypeMapping` (5 tests: DL classification->image_classification, DL regression->custom, DL native passthrough, tabular passthrough, FT passthrough) — all substantive and integrated into the test run. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/mlforge/scaffold.py` | `plugin.validate_config()` | call before plugin.scaffold() | VERIFIED | Lines 168-173: `errors = plugin.validate_config(config)` followed by raise if errors, executed before `plugin.scaffold()` at line 176. Pattern `validate_config` confirmed in file. |
| `src/mlforge/scaffold.py` | `config.plugin_settings` | `_map_task_for_domain` mutates task key | VERIFIED | `_map_task_for_domain(config)` at line 165 mutates `config.plugin_settings["task"]` in-place. DL plugin's `scaffold()` at deeplearning/__init__.py:59 then reads `config.plugin_settings.get("task", "image_classification")` for template rendering — the mapped value flows into architecture selection. |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FT-04 | 12-01-PLAN.md | Plugin generates domain-specific CLAUDE.md protocol with fine-tuning rules and anti-patterns | SATISFIED | FT plugin's `claude_md_context()` generates protocol rules (LoRA/QLoRA, VRAM, gradient checkpointing). Phase 12 wires `validate_config()` so invalid FT configs (missing model_name, invalid metric) are caught before scaffold — making the gate that enforces protocol compliance. Traceability table marks Phase 12 as the completing phase. |
| DL-03 | 12-01-PLAN.md | Plugin supports learning rate scheduling, early stopping, and gradient clipping as protocol rules | SATISFIED | DL plugin's `claude_md_context()` includes "Use early stopping with patience=5 on validation loss", "Apply gradient clipping: torch.nn.utils.clip_grad_norm_(...)", "Use ReduceLROnPlateau scheduler". Phase 12 wires `validate_config()` to enforce DL metric and task constraints, making DL plugin protocol gates active. Traceability table attributes DL-03 completion to Phase 12. |
| UX-01 | 12-01-PLAN.md | Simple mode auto-detects task type, selects metrics, and generates protocol from minimal user input | SATISFIED | Task type mapping (`classification -> image_classification`) closes the gap where profiler-detected types were incompatible with DL plugin validation. Simple mode now works for DL domain without user manually specifying DL-native task types. Note: UX-01 traceability table lists Phase 9 as the primary phase; Phase 12 completes the DL-domain task-mapping portion. |
| TABL-01 | 12-01-PLAN.md | Tabular ML plugin handles classification and regression tasks on CSV/Parquet tabular data | SATISFIED | Tabular `validate_config()` enforces valid metrics. Task types pass through unchanged for tabular (no mapping). Test `test_tabular_task_passthrough` and `test_valid_config_scaffolds_ok` confirm tabular domain functions correctly end-to-end. |
| DL-01 | 12-01-PLAN.md | Deep learning plugin handles image classification, text classification, and custom architecture training with PyTorch | SATISFIED | `_TASK_TYPE_MAP` maps profiler `classification -> image_classification` so DL plugin correctly handles profiler output. DL `_VALID_TASKS` = {image_classification, text_classification, custom}. Validate_config gate enforces these. Tests cover image_classification and custom mappings. |
| FT-01 | 12-01-PLAN.md | Fine-tuning plugin handles LoRA/QLoRA fine-tuning of open models via PEFT/TRL | SATISFIED | FT plugin scaffolds `train.py` and `prepare.py` for LoRA/QLoRA. Phase 12 wires `validate_config()` which enforces `model_name` is present before scaffolding — making FT plugin correctly guarded at the entry point. Test `test_ft_task_no_mapping` confirms FT scaffold succeeds with valid config. |

**Requirement analysis notes:**
- DL-03 and FT-04 are attributed in the REQUIREMENTS.md traceability table to Phase 12. The plugins' protocol rule content was established in Phase 8, but Phase 12 activates those rules through the validation gate — a legitimate "completing" contribution.
- UX-01 has a split attribution: Phase 9 (simple mode task detection infrastructure) and Phase 12 (task mapping that makes simple mode work for DL domain). Both are correctly marked complete.
- All 6 requirement IDs from the PLAN frontmatter are accounted for and satisfied.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | — |

No TODOs, FIXMEs, stub returns, or placeholder patterns found in the modified files.

---

### Human Verification Required

None. All behaviors are fully verified programmatically:
- Tests confirm validation error messages are raised with correct text
- Tests confirm task mapping mutates config in-place with correct values
- Tests confirm no regression (482/482 mlforge tests pass)

---

### Test Suite Results

| Test Class | Tests | Result |
|------------|-------|--------|
| `TestScaffoldValidation` | 5 | 5/5 pass |
| `TestTaskTypeMapping` | 5 | 5/5 pass |
| Full mlforge suite | 482 | 482/482 pass |

Command verified: `python3 -m pytest tests/mlforge/ -q` → `482 passed, 2 warnings in 3.08s`

---

### Gaps Summary

No gaps. All must-haves are verified against the actual codebase:

1. `validate_config()` is wired into `scaffold_experiment()` at the correct position (after task mapping, before plugin.scaffold).
2. `_map_task_for_domain()` correctly translates `classification -> image_classification` and `regression -> custom` for DL, and passes through for tabular and FT.
3. All three plugins have substantive `validate_config()` implementations (not stubs).
4. The mapped task value flows into DL plugin's `scaffold()` for correct architecture selection.
5. 10 new test cases cover all specified behaviors with no regressions.

---

_Verified: 2026-03-20T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
