---
phase: 07
slug: wire-intelligence-subsystem
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
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
| **Estimated runtime** | ~15 seconds |

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
| 07-01-01 | 01 | 1 | INTL-01 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k baseline` | No — W0 | pending |
| 07-01-02 | 01 | 1 | INTL-02 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k gate` | No — W0 | pending |
| 07-01-03 | 01 | 1 | CORE-08, INTL-06 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k journal` | No — W0 | pending |
| 07-01-04 | 01 | 1 | INTL-03 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k diagnos` | No — W0 | pending |
| 07-01-05 | 01 | 1 | INTL-04 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k stagnation` | No — W0 | pending |
| 07-01-06 | 01 | 1 | INTL-05 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k draft` | No — W0 | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_engine.py` — extend with test classes for baseline, gate, journal, diagnostics, stagnation, draft integration points
- [ ] Existing tests (421 total) must continue passing — no regressions

*Existing infrastructure covers test framework setup. Only new test stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-draft prompt directs agent to specific family | INTL-05 | Requires live claude session | Run engine with `enable_drafts=true`, verify agent uses specified family |
| Diagnostics text useful to agent | INTL-03 | Subjective quality check | Review diagnostics.md content after a run |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
