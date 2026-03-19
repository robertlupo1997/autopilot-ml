---
phase: 2
slug: tabular-plugin-experiment-intelligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (latest) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `python3 -m pytest tests/mlforge/ -x -q` |
| **Full suite command** | `python3 -m pytest tests/mlforge/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/ -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/mlforge/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | TABL-01 | unit | `python3 -m pytest tests/mlforge/test_tabular.py -x` | No -- Wave 0 | pending |
| 02-01-02 | 01 | 1 | TABL-02 | unit | `python3 -m pytest tests/mlforge/test_tabular.py::test_algorithm_families -x` | No -- Wave 0 | pending |
| 02-01-03 | 01 | 1 | TABL-03 | unit | `python3 -m pytest tests/mlforge/test_tabular.py::test_temporal_validation -x` | No -- Wave 0 | pending |
| 02-01-04 | 01 | 1 | TABL-04 | unit | `python3 -m pytest tests/mlforge/test_tabular.py::test_template_context -x` | No -- Wave 0 | pending |
| 02-01-05 | 01 | 1 | TABL-05 | unit | `python3 -m pytest tests/mlforge/test_tabular.py::test_scaffold -x` | No -- Wave 0 | pending |
| 02-01-06 | 01 | 1 | INTL-01 | unit | `python3 -m pytest tests/mlforge/test_baselines.py -x` | No -- Wave 0 | pending |
| 02-01-07 | 01 | 1 | INTL-02 | unit | `python3 -m pytest tests/mlforge/test_baselines.py::test_gate -x` | No -- Wave 0 | pending |
| 02-02-01 | 02 | 1 | INTL-03 | unit | `python3 -m pytest tests/mlforge/test_diagnostics.py -x` | No -- Wave 0 | pending |
| 02-02-02 | 02 | 1 | INTL-04 | unit | `python3 -m pytest tests/mlforge/test_stagnation.py -x` | No -- Wave 0 | pending |
| 02-02-03 | 02 | 1 | INTL-05 | unit | `python3 -m pytest tests/mlforge/test_drafts.py -x` | No -- Wave 0 | pending |
| 02-02-04 | 02 | 1 | INTL-06 | unit | `python3 -m pytest tests/mlforge/test_journal.py -x` | Partial | pending |
| 02-02-05 | 02 | 1 | INTL-08 | unit | `python3 -m pytest tests/mlforge/test_journal.py -x` | Partial | pending |
| 02-03-01 | 03 | 2 | ALL | integration | `python3 -m pytest tests/mlforge/ -v` | No -- Wave 0 | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_tabular.py` — stubs for TABL-01 through TABL-05
- [ ] `tests/mlforge/test_baselines.py` — stubs for INTL-01, INTL-02
- [ ] `tests/mlforge/test_diagnostics.py` — stubs for INTL-03
- [ ] `tests/mlforge/test_stagnation.py` — stubs for INTL-04
- [ ] `tests/mlforge/test_drafts.py` — stubs for INTL-05
- [ ] ML dependencies: `pip install scikit-learn pandas numpy xgboost lightgbm optuna pyarrow`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CLAUDE.md protocol renders correctly for agent consumption | TABL-04 | Requires agent interpretation | Inspect rendered CLAUDE.md for tabular domain rules |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
