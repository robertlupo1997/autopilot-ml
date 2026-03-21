---
phase: 1
slug: foundation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-09
audited: 2026-03-14
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
| 1-01-01 | 01 | 1 | PIPE-01 | unit | `uv run pytest tests/test_prepare.py::TestLoadData -x` | ✅ | ✅ green |
| 1-01-02 | 01 | 1 | PIPE-02 | unit | `uv run pytest tests/test_prepare.py::TestSplitData::test_split_data -x` | ✅ | ✅ green |
| 1-01-03 | 01 | 1 | PIPE-03 | unit | `uv run pytest tests/test_prepare.py::TestEvaluate -x` | ✅ | ✅ green |
| 1-01-04 | 01 | 1 | PIPE-04 | unit | `uv run pytest tests/test_prepare.py::TestBaselines -x` | ✅ | ✅ green |
| 1-01-05 | 01 | 1 | PIPE-05 | unit | `uv run pytest tests/test_prepare.py::TestSplitData::test_holdout_split_no_overlap -x` | ✅ | ✅ green |
| 1-01-06 | 01 | 1 | PIPE-06 | unit | `uv run pytest tests/test_prepare.py::TestPreprocessor -x` | ✅ | ✅ green |
| 1-01-07 | 01 | 1 | PIPE-07 | unit | `uv run pytest tests/test_prepare.py::TestDataSummary -x` | ✅ | ✅ green |
| 1-02-01 | 02 | 1 | MODEL-01 | smoke | `uv run pytest tests/test_train.py::TestTemplateFile::test_template_is_single_file -x` | ✅ | ✅ green |
| 1-02-02 | 02 | 1 | MODEL-02 | smoke | `uv run pytest tests/test_train.py::TestTemplateExecution::test_template_runs -x` | ✅ | ✅ green |
| 1-02-03 | 02 | 1 | MODEL-03 | smoke | `uv run pytest tests/test_train.py::TestTemplateFile::test_template_imports_prepare -x` | ✅ | ✅ green |
| 1-02-04 | 02 | 1 | MODEL-04 | unit | `uv run pytest tests/test_train.py::TestTemplateExecution::test_structured_output -x` | ✅ | ✅ green |
| 1-02-05 | 02 | 1 | MODEL-05 | unit | `uv run pytest tests/test_train.py::TestTimeoutEnforcement::test_timeout_enforced -x` | ✅ | ✅ green |
| 1-03-01 | 03 | 1 | GIT-01 | integration | `uv run pytest tests/test_git.py::TestCreateBranch::test_create_branch -x` | ✅ | ✅ green |
| 1-03-02 | 03 | 1 | GIT-02 | integration | `uv run pytest tests/test_git.py::TestCommit::test_commit -x` | ✅ | ✅ green |
| 1-03-03 | 03 | 1 | GIT-03 | integration | `uv run pytest tests/test_git.py::TestRevert::test_revert -x` | ✅ | ✅ green |
| 1-03-04 | 03 | 1 | GIT-04 | unit | `uv run pytest tests/test_git.py::TestGitignore::test_gitignore -x` | ✅ | ✅ green |
| 1-03-05 | 03 | 1 | GIT-05 | unit | `uv run pytest tests/test_git.py::TestNoGitPython::test_no_gitpython -x` | ✅ | ✅ green |
| 1-04-01 | 04 | 1 | LOG-01 | unit | `uv run pytest tests/test_logging.py::TestLogResult::test_log_fields -x` | ✅ | ✅ green |
| 1-04-02 | 04 | 1 | LOG-02 | unit | `uv run pytest tests/test_logging.py::TestLogResult::test_tsv_format -x` | ✅ | ✅ green |
| 1-04-03 | 04 | 1 | LOG-03 | integration | `uv run pytest tests/test_logging.py::TestRunLog::test_write_run_log -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/conftest.py` — shared fixtures (sample CSV, temp git repos)
- [x] `tests/test_prepare.py` — stubs for PIPE-01 through PIPE-07
- [x] `tests/test_train.py` — stubs for MODEL-01 through MODEL-05
- [x] `tests/test_git.py` — stubs for GIT-01 through GIT-05
- [x] `tests/test_logging.py` — stubs for LOG-01 through LOG-03
- [x] Framework install: `uv add pytest` — pytest installed (v9.0.2)
- [x] Sample test CSV fixture needed for all data tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| train.py is a single editable file | MODEL-01 | Originally manual — now automated | `TestTemplateFile::test_template_is_single_file` passes |
| Git via subprocess only | GIT-05 | Originally manual — now automated | `TestNoGitPython::test_no_gitpython` passes |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s (11.38s measured)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** audited 2026-03-14 — 46/46 tests passing, all 19 VALIDATION rows green
