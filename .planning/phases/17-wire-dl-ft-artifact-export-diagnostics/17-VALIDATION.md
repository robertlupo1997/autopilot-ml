---
phase: 17
slug: wire-dl-ft-artifact-export-diagnostics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python3 -m pytest tests/mlforge/ -x -q` |
| **Full suite command** | `python3 -m pytest tests/mlforge/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/ -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/mlforge/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | UX-03 | unit | `python3 -m pytest tests/mlforge/test_export.py -x` | Exists, needs new tests | ⬜ pending |
| 17-01-02 | 01 | 1 | DL-04 | unit | `python3 -m pytest tests/mlforge/test_templates.py -x` | Exists, needs new tests | ⬜ pending |
| 17-01-03 | 01 | 1 | FT-04 | unit | `python3 -m pytest tests/mlforge/test_templates.py -x` | Exists, needs new tests | ⬜ pending |
| 17-01-04 | 01 | 1 | INTL-03 | unit | `python3 -m pytest tests/mlforge/test_templates.py -x` | Exists, needs new tests | ⬜ pending |
| 17-01-05 | 01 | 1 | SWARM-04 | unit | `python3 -m pytest tests/mlforge/test_swarm.py -x` | Exists, needs new tests | ⬜ pending |
| 17-01-06 | 01 | 1 | INTL-03 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x` | Exists, needs new tests | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. New tests added alongside implementation.

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
