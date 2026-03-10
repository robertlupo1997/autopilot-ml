---
phase: 2
slug: core-loop
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
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
| 2-01-01 | 01 | 1 | LOOP-01 | integration | `uv run pytest tests/test_loop_helpers.py::test_keep_revert_decision -x` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | LOOP-02 | unit | `uv run pytest tests/test_runner.py::TestExperimentRun::test_run_captures_log -x` | ✅ | ⬜ pending |
| 2-01-03 | 01 | 1 | LOOP-03 | unit | `uv run pytest tests/test_runner.py::TestMetricExtraction -x` | ✅ | ⬜ pending |
| 2-01-04 | 01 | 1 | LOOP-04 | unit | `uv run pytest tests/test_loop_helpers.py::test_should_keep -x` | ❌ W0 | ⬜ pending |
| 2-01-05 | 01 | 1 | LOOP-05 | manual | Verify CLAUDE.md contains loop protocol | N/A | ⬜ pending |
| 2-01-06 | 01 | 1 | LOOP-06 | unit | `uv run pytest tests/test_runner.py::TestErrorHandling::test_run_timeout -x` | ✅ | ⬜ pending |
| 2-01-07 | 01 | 1 | LOOP-07 | unit | `uv run pytest tests/test_loop_helpers.py::test_crash_recovery_threshold -x` | ❌ W0 | ⬜ pending |
| 2-01-08 | 01 | 1 | LOOP-08 | unit | `uv run pytest tests/test_loop_helpers.py::test_stagnation_detection -x` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 1 | CTX-01 | unit | `uv run pytest tests/test_templates.py::test_program_md_template -x` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 1 | CTX-02 | manual | Verify CLAUDE.md instructs re-reading program.md | N/A | ⬜ pending |
| 2-02-03 | 02 | 1 | CTX-03 | unit | `uv run pytest tests/test_templates.py::test_claude_md_template -x` | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 1 | DRAFT-01 | unit | `uv run pytest tests/test_drafts.py::test_generate_drafts -x` | ❌ W0 | ⬜ pending |
| 2-03-02 | 03 | 1 | DRAFT-02 | integration | `uv run pytest tests/test_drafts.py::test_draft_evaluation -x` | ❌ W0 | ⬜ pending |
| 2-03-03 | 03 | 1 | DRAFT-03 | unit | `uv run pytest tests/test_drafts.py::test_select_best_draft -x` | ❌ W0 | ⬜ pending |
| 2-03-04 | 03 | 1 | DRAFT-04 | unit | `uv run pytest tests/test_drafts.py::test_draft_logging_status -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_loop_helpers.py` — stubs for LOOP-01, LOOP-04, LOOP-07, LOOP-08
- [ ] `tests/test_templates.py` — stubs for CTX-01, CTX-03
- [ ] `tests/test_drafts.py` — stubs for DRAFT-01 through DRAFT-04

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Agent runs autonomously and indefinitely | LOOP-05 | Agent behavior, not code behavior | Verify CLAUDE.md contains "NEVER STOP" and loop protocol |
| Agent reads program.md each iteration | CTX-02 | Agent behavior, not code behavior | Verify CLAUDE.md instructs re-reading program.md |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
