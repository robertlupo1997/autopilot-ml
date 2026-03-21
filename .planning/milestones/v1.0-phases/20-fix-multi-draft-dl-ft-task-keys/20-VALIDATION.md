---
phase: 20
slug: fix-multi-draft-dl-ft-task-keys
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/mlforge/test_drafts.py tests/mlforge/test_engine.py -x -q` |
| **Full suite command** | `python -m pytest tests/mlforge/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/mlforge/test_drafts.py tests/mlforge/test_engine.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/mlforge/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | INTL-05 | unit | `pytest tests/mlforge/test_drafts.py -x -q` | Needs update | pending |
| 20-01-02 | 01 | 1 | INTL-05 | unit | `pytest tests/mlforge/test_drafts.py -x -q` | New test | pending |
| 20-01-03 | 01 | 1 | DL-04 | unit | `pytest tests/mlforge/test_engine.py -x -q` | Needs update | pending |
| 20-01-04 | 01 | 1 | INTL-05 | unit | `pytest tests/mlforge/test_engine.py -x -q` | Needs update | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Tests need updating, not new framework setup.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
