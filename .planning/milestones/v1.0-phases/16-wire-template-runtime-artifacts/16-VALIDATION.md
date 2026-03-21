---
phase: 16
slug: wire-template-runtime-artifacts
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/mlforge/test_templates.py tests/mlforge/test_engine.py tests/mlforge/test_export.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/mlforge/test_templates.py tests/mlforge/test_engine.py tests/mlforge/test_export.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | INTL-03, UX-03 | unit | `python -m pytest tests/mlforge/test_templates.py -k "predictions or joblib" -x -q` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | INTL-03 | unit | `python -m pytest tests/mlforge/test_engine.py -k "diagnostics" -x -q` | ❌ W0 | ⬜ pending |
| 16-01-03 | 01 | 1 | UX-03 | unit | `python -m pytest tests/mlforge/test_export.py -k "artifact" -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_templates.py` — add tabular template artifact write tests
- [ ] `tests/mlforge/test_engine.py` — add diagnostics integration tests
- [ ] `tests/mlforge/test_export.py` — add export artifact integration tests

*Existing infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
