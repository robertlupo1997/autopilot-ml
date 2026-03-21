---
phase: 6
slug: fix-engine-subprocess-flags
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-19
validated: 2026-03-20
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml |
| **Quick run command** | `python3 -m pytest tests/mlforge/test_engine.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/mlforge/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/test_engine.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/mlforge/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | CORE-03 | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestCommandFlags::test_uses_append_system_prompt_with_inline_content -x` | Yes | green |
| 06-01-02 | 01 | 1 | INTL-07 | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestCommandFlags::test_no_max_turns_flag tests/mlforge/test_engine.py::TestCommandFlags::test_max_budget_usd_still_present -x` | Yes | green |
| 06-01-03 | 01 | 1 | CORE-02 | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestRunLoop -x` | Yes | green |
| 06-01-04 | 01 | 1 | GUARD-03 | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestRunLoop::test_saves_checkpoint_before_each_experiment -x` | Yes | green |

*Status: pending -- green -- red -- flaky*

---

## Wave 0 Requirements

- [x] New test in `tests/mlforge/test_engine.py` -- verify `--append-system-prompt` with inline CLAUDE.md content (`TestCommandFlags::test_uses_append_system_prompt_with_inline_content`)
- [x] New test -- verify `--max-turns` is NOT in subprocess command (`TestCommandFlags::test_no_max_turns_flag`)
- [x] New test -- verify command works when CLAUDE.md is missing (graceful degradation) (`TestCommandFlags::test_no_append_system_prompt_when_claude_md_missing`)
- [x] Update existing tests that assert on old flag structure (`TestCommandFlags::test_max_budget_usd_still_present`)

*Wave 0 tests created as part of Plan 01 tasks. All 4 verified green on 2026-03-20.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E2E experiment runs without subprocess crash | CORE-02 | Requires actual claude CLI binary | Run `mlforge run --dataset test.csv` and verify experiment executes |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-03-20 (Nyquist auditor)
