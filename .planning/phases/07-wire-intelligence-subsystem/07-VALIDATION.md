---
phase: 07
slug: wire-intelligence-subsystem
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-19
validated: 2026-03-20
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (stdlib) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `python3 -m pytest tests/mlforge/test_engine.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/mlforge/ -x -q` |
| **Estimated runtime** | ~4 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/test_engine.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/mlforge/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 4 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | INTL-01 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k baseline` | Yes | green |
| 07-01-02 | 01 | 1 | INTL-02 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k gate` | Yes | green |
| 07-01-03 | 01 | 1 | CORE-08, INTL-06 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k journal` | Yes | green |
| 07-01-04 | 01 | 1 | INTL-03 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k diagnos` | Yes | green |
| 07-01-05 | 01 | 1 | INTL-04 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k stagnation` | Yes | green |
| 07-01-06 | 01 | 1 | INTL-05 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k draft` | Yes | green |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `tests/mlforge/test_engine.py` -- extended with `TestIntelligenceIntegration` (10 tests), `TestMultiDraftIntegration` (7 tests), `TestDiagnosticsIntegration` (6 tests)
- [x] Existing tests (466 total) continue passing -- no regressions

*All Wave 0 requirements satisfied. Tests exist and pass.*

---

## Test Coverage Detail

| Task ID | Requirement | Tests (count) | Key Test Names |
|---------|-------------|---------------|----------------|
| 07-01-01 | INTL-01 | 4 | `test_compute_baselines_called_before_loop`, `test_baselines_skipped_for_non_tabular`, `test_baseline_gate_rejects_sub_baseline_keep`, `test_baseline_gate_passes_when_beating_baselines` |
| 07-01-02 | INTL-02 | 2 | `test_baseline_gate_rejects_sub_baseline_keep`, `test_baseline_gate_passes_when_beating_baselines` |
| 07-01-03 | CORE-08, INTL-06 | 3 | `test_journal_entry_written_on_keep`, `test_journal_entry_written_on_revert`, `test_journal_diff_captured_on_keep` |
| 07-01-04 | INTL-03 | 6 | `test_diagnostics_run_after_experiment`, `test_diagnostics_skipped_when_no_predictions`, `test_diagnostics_output_written_to_file`, `test_diagnostics_injected_into_prompt`, `test_regression_diagnostics_used_for_regression`, `test_classification_diagnostics_used_for_classification` |
| 07-01-05 | INTL-04 | 3 | `test_stagnation_branch_triggered`, `test_stagnation_picks_untried_family`, `test_no_stagnation_below_threshold` |
| 07-01-06 | INTL-05 | 7 | `test_draft_phase_runs_when_enabled`, `test_draft_phase_skipped_when_disabled`, `test_draft_runs_each_family`, `test_best_draft_selected`, `test_best_draft_checkout`, `test_draft_results_none_handled`, `test_tried_families_populated` |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-draft prompt directs agent to specific family | INTL-05 | Requires live claude session | Run engine with `enable_drafts=true`, verify agent uses specified family |
| Diagnostics text useful to agent | INTL-03 | Subjective quality check | Review diagnostics.md content after a run |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s (measured: ~4s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-03-20 -- all 6 task entries green, 466 tests passing, 0 failures
