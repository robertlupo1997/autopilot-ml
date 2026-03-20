---
phase: 15-fix-ft-simple-mode-metric-mapping
verified: 2026-03-20T23:45:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 15: Fix FT Simple Mode Metric Mapping Verification Report

**Phase Goal:** Add finetuning domain to task type mapping and set valid default metric so `--domain finetuning` simple mode works without ValueError
**Verified:** 2026-03-20T23:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | FT simple mode (`--domain finetuning`) reaches scaffold without ValueError | VERIFIED | `test_ft_simple_mode_reaches_scaffold` passes; `_map_task_for_domain` overrides metric before `validate_config` runs (scaffold.py:190-198) |
| 2 | FT metric is overridden from profiler default (accuracy) to FT-valid metric (loss) | VERIFIED | `_METRIC_DEFAULTS = {"finetuning": ("loss", "minimize")}` at scaffold.py:101-103; override fires when `config.metric not in _VALID_METRICS` (scaffold.py:133-135); `test_ft_simple_mode_metric_override` confirms cfg.metric == "loss" |
| 3 | FT direction is set to minimize alongside metric override | VERIFIED | Same override block sets `config.direction = "minimize"` (scaffold.py:135); `test_ft_direction_set_to_minimize` passes |
| 4 | Expert mode FT metric (e.g. perplexity) is preserved, not overridden | VERIFIED | Override guarded by `if config.metric not in valid_metrics` — perplexity is in `_VALID_METRICS` so it passes through; `test_ft_expert_mode_metric_preserved` confirms cfg.metric == "perplexity" |
| 5 | FT simple mode sets default model_name so validate_config passes | VERIFIED | `_MODEL_NAME_DEFAULTS = {"finetuning": "meta-llama/Llama-3.2-1B"}` at scaffold.py:105-107; default applied only when `plugin_settings` lacks "model_name" (scaffold.py:139-140); `test_ft_simple_mode_default_model_name` and `test_ft_without_model_name_gets_default` both pass |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/mlforge/scaffold.py` | FT domain entry in `_TASK_TYPE_MAP`, metric/direction override in `_map_task_for_domain`, default model_name | VERIFIED | Contains `"finetuning": {"classification": "sft", "regression": "sft"}` in `_TASK_TYPE_MAP` (line 95-98); `_METRIC_DEFAULTS` and `_MODEL_NAME_DEFAULTS` dicts (lines 101-107); metric/direction override logic in `_map_task_for_domain` (lines 128-140) |
| `tests/mlforge/test_scaffold.py` | FT metric override, direction, expert mode preservation, and E2E scaffold tests | VERIFIED | 7 FT-specific tests present: `test_ft_task_mapped_to_sft`, `test_ft_simple_mode_metric_override`, `test_ft_expert_mode_metric_preserved`, `test_ft_direction_set_to_minimize`, `test_ft_simple_mode_default_model_name`, `test_ft_simple_mode_reaches_scaffold`, `test_ft_without_model_name_gets_default` |

---

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `scaffold.py::_map_task_for_domain` | `finetuning/__init__.py::_VALID_METRICS` | lazy import inside conditional | WIRED | `from mlforge.finetuning import FineTuningPlugin` inside `if metric_default is not None:` block (scaffold.py:130-132); `valid_metrics = FineTuningPlugin._VALID_METRICS` used for guard check (line 132) |
| `scaffold.py::_map_task_for_domain` | `scaffold.py::scaffold_experiment` | called before `validate_config` in `scaffold_experiment` | WIRED | `_map_task_for_domain(config)` at line 190; `plugin.validate_config(config)` at line 193 — mapping runs first, so overridden metric/model_name are in place before validation |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| FT-04 | 15-01-PLAN.md | Plugin generates domain-specific CLAUDE.md protocol with fine-tuning rules and anti-patterns | SATISFIED | `FineTuningPlugin.template_context()` returns 9+ domain rules (finetuning/__init__.py:80-91); `render_claude_md` called in `scaffold_experiment` (line 211); Phase 15 completes the FT end-to-end path so the CLAUDE.md generation becomes reachable via simple mode |
| UX-01 | 15-01-PLAN.md | Simple mode auto-detects task type, selects metrics, and generates protocol from minimal user input | SATISFIED | FT simple mode with `metric="accuracy"` (profiler default) now auto-overrides to valid FT metric, auto-sets model_name, and completes scaffold — the user provides only `--domain finetuning` and the system handles the rest |

No orphaned requirements — both FT-04 and UX-01 are declared in the plan frontmatter and verified in the codebase.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| None found | — | — | — | — |

No TODO/FIXME/placeholder comments, empty return stubs, or console.log-only implementations found in the modified files.

---

### Test Suite Status

- `tests/mlforge/test_scaffold.py::TestTaskTypeMapping` — 9 tests, 9 passed
- `tests/mlforge/test_scaffold.py::TestScaffoldValidation` — 6 tests, 6 passed
- `tests/mlforge/` (all mlforge tests) — 502 passed, 0 failed
- `tests/test_cli.py::test_cli_valid_args` — 1 pre-existing failure (uses old `automl` module, "string dtypes are not allowed" — unrelated to Phase 15's `mlforge` changes; confirmed failing on parent commit before Phase 15 work)

---

### Human Verification Required

None. All observable truths are verifiable programmatically via the test suite. No UI, real-time behavior, or external service integration involved.

---

### Gaps Summary

No gaps. All five must-have truths are verified, both artifacts are substantive and wired, both key links are active, and both requirement IDs are satisfied. The single pre-existing test failure (`test_cli_valid_args`) is in the legacy `automl` module and was present before Phase 15's commit `a60134b`.

---

_Verified: 2026-03-20T23:45:00Z_
_Verifier: Claude (gsd-verifier)_
