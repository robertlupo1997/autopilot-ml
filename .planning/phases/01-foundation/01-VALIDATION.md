---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (latest) |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | PIPE-01 | unit | `uv run pytest tests/test_prepare.py::test_load_data -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | PIPE-02 | unit | `uv run pytest tests/test_prepare.py::test_split_data -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | PIPE-03 | unit | `uv run pytest tests/test_prepare.py::test_evaluate -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | PIPE-04 | unit | `uv run pytest tests/test_prepare.py::test_baselines -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | PIPE-05 | unit | `uv run pytest tests/test_prepare.py::test_holdout_split -x` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | PIPE-06 | unit | `uv run pytest tests/test_prepare.py::test_preprocess -x` | ❌ W0 | ⬜ pending |
| 1-01-07 | 01 | 1 | PIPE-07 | unit | `uv run pytest tests/test_prepare.py::test_data_summary -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | MODEL-01 | smoke | manual verification | N/A | ⬜ pending |
| 1-02-02 | 02 | 1 | MODEL-02 | smoke | `uv run pytest tests/test_train.py::test_template_runs -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | MODEL-03 | smoke | `uv run pytest tests/test_train.py::test_imports -x` | ❌ W0 | ⬜ pending |
| 1-02-04 | 02 | 1 | MODEL-04 | unit | `uv run pytest tests/test_train.py::test_structured_output -x` | ❌ W0 | ⬜ pending |
| 1-02-05 | 02 | 1 | MODEL-05 | unit | `uv run pytest tests/test_train.py::test_timeout -x` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 1 | GIT-01 | integration | `uv run pytest tests/test_git.py::test_create_branch -x` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 1 | GIT-02 | integration | `uv run pytest tests/test_git.py::test_commit -x` | ❌ W0 | ⬜ pending |
| 1-03-03 | 03 | 1 | GIT-03 | integration | `uv run pytest tests/test_git.py::test_revert -x` | ❌ W0 | ⬜ pending |
| 1-03-04 | 03 | 1 | GIT-04 | unit | `uv run pytest tests/test_git.py::test_gitignore -x` | ❌ W0 | ⬜ pending |
| 1-03-05 | 03 | 1 | GIT-05 | unit | manual verification (no GitPython import) | N/A | ⬜ pending |
| 1-04-01 | 04 | 1 | LOG-01 | unit | `uv run pytest tests/test_logging.py::test_log_fields -x` | ❌ W0 | ⬜ pending |
| 1-04-02 | 04 | 1 | LOG-02 | unit | `uv run pytest tests/test_logging.py::test_tsv_format -x` | ❌ W0 | ⬜ pending |
| 1-04-03 | 04 | 1 | LOG-03 | integration | `uv run pytest tests/test_logging.py::test_run_log -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (sample CSV, temp git repos)
- [ ] `tests/test_prepare.py` — stubs for PIPE-01 through PIPE-07
- [ ] `tests/test_train.py` — stubs for MODEL-01 through MODEL-05
- [ ] `tests/test_git.py` — stubs for GIT-01 through GIT-05
- [ ] `tests/test_logging.py` — stubs for LOG-01 through LOG-03
- [ ] Framework install: `uv add pytest` — pytest not yet in project
- [ ] Sample test CSV fixture needed for all data tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| train.py is a single editable file | MODEL-01 | Structural constraint, not behavioral | Verify train.py exists as single file |
| Git via subprocess only | GIT-05 | Import check, not behavioral | Verify no GitPython in requirements or imports |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
