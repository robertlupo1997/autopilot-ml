---
phase: 6
slug: fix-engine-subprocess-flags
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
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
| 06-01-01 | 01 | 1 | CORE-03 | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestRunOneExperiment -x` | Yes (needs update) | ⬜ pending |
| 06-01-02 | 01 | 1 | INTL-07 | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestRunOneExperiment -x` | Yes (needs update) | ⬜ pending |
| 06-01-03 | 01 | 1 | CORE-02 | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestRunLoop -x` | Yes | ⬜ pending |
| 06-01-04 | 01 | 1 | GUARD-03 | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestRunLoop -x` | Yes | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] New test in `tests/mlforge/test_engine.py` — verify `--append-system-prompt` with inline CLAUDE.md content
- [ ] New test — verify `--max-turns` is NOT in subprocess command
- [ ] New test — verify command works when CLAUDE.md is missing (graceful degradation)
- [ ] Update existing tests that assert on old flag structure

*Wave 0 tests created as part of Plan 01 tasks.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E2E experiment runs without subprocess crash | CORE-02 | Requires actual claude CLI binary | Run `mlforge run --dataset test.csv` and verify experiment executes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
