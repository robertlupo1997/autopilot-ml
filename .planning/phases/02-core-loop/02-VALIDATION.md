---
phase: 2
slug: core-loop
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-10
audited: 2026-03-14
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | LOOP-01 | unit | `uv run pytest tests/test_loop_helpers.py::TestShouldKeep -x` | ✅ | ✅ green |
| 2-01-02 | 01 | 1 | LOOP-02 | unit | `uv run pytest tests/test_runner.py::TestExperimentRun::test_run_captures_log -x` | ✅ | ✅ green |
| 2-01-03 | 01 | 1 | LOOP-03 | unit | `uv run pytest tests/test_runner.py::TestMetricExtraction -x` | ✅ | ✅ green |
| 2-01-04 | 01 | 1 | LOOP-04 | unit | `uv run pytest tests/test_loop_helpers.py::TestShouldKeep -x` | ✅ | ✅ green |
| 2-01-05 | 01 | 1 | LOOP-05 | automated | `uv run pytest tests/test_templates.py::TestClaudeMdTemplate::test_claude_md_has_never_stop -x` | ✅ | ✅ green |
| 2-01-06 | 01 | 1 | LOOP-06 | unit | `uv run pytest tests/test_runner.py::TestErrorHandling::test_run_timeout -x` | ✅ | ✅ green |
| 2-01-07 | 01 | 1 | LOOP-07 | unit | `uv run pytest tests/test_loop_helpers.py::TestIsCrashStuck -x` | ✅ | ✅ green |
| 2-01-08 | 01 | 1 | LOOP-08 | unit | `uv run pytest tests/test_loop_helpers.py::TestIsStagnating -x` | ✅ | ✅ green |
| 2-02-01 | 02 | 1 | CTX-01 | unit | `uv run pytest tests/test_templates.py::TestProgramMdTemplate -x` | ✅ | ✅ green |
| 2-02-02 | 02 | 1 | CTX-02 | automated | `uv run pytest tests/test_templates.py::TestClaudeMdTemplate::test_claude_md_references_program_md -x` | ✅ | ✅ green |
| 2-02-03 | 02 | 1 | CTX-03 | unit | `uv run pytest tests/test_templates.py::TestClaudeMdTemplate -x` | ✅ | ✅ green |
| 2-03-01 | 03 | 1 | DRAFT-01 | unit | `uv run pytest tests/test_drafts.py::TestAlgorithmFamilies tests/test_drafts.py::TestGenerateDraft -x` | ✅ | ✅ green |
| 2-03-02 | 03 | 1 | DRAFT-02 | unit | `uv run pytest tests/test_drafts.py::TestGenerateDraft -x` | ✅ | ✅ green |
| 2-03-03 | 03 | 1 | DRAFT-03 | unit | `uv run pytest tests/test_drafts.py::TestSelectBestDraft::test_select_best_draft -x` | ✅ | ✅ green |
| 2-03-04 | 03 | 1 | DRAFT-04 | unit | `uv run pytest tests/test_drafts.py::TestSelectBestDraft::test_draft_status_strings -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_loop_helpers.py` — 17 tests covering LOOP-01, LOOP-04, LOOP-07, LOOP-08
- [x] `tests/test_templates.py` — 20+ tests covering CTX-01, CTX-03
- [x] `tests/test_drafts.py` — 10 tests covering DRAFT-01 through DRAFT-04

---

## Actual Test Coverage (Audited 2026-03-14)

| Test File | Test Count | Classes |
|-----------|------------|---------|
| `tests/test_loop_helpers.py` | 17 | TestShouldKeep, TestLoopStateDefaults, TestIsStagnating, TestIsCrashStuck, TestSuggestStrategyShift, TestStrategyCategories |
| `tests/test_drafts.py` | 10 | TestAlgorithmFamilies, TestGenerateDraft, TestDraftResult, TestSelectBestDraft |
| `tests/test_templates.py` | 20+ | TestProgramMdTemplate, TestClaudeMdTemplate, TestRenderFunctions, TestClaudeMdResumeSection |
| `tests/test_runner.py` | 10 | TestExperimentRun, TestMetricExtraction, TestErrorHandling, TestJsonOutputParsing |

All 68 tests across these four files pass (confirmed via `uv run pytest` run on 2026-03-14).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Automated Proxy | Status |
|----------|-------------|------------|-----------------|--------|
| Agent runs autonomously and indefinitely | LOOP-05 | Agent behavior | `test_claude_md_has_never_stop` confirms protocol text present | ✅ green |
| Agent reads program.md each iteration | CTX-02 | Agent behavior | `test_claude_md_references_program_md` confirms instruction present | ✅ green |

---

## Validation Sign-Off

- [x] All tasks have automated verify commands pointing to passing tests
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all requirements
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** nyquist_compliant — audited 2026-03-14
