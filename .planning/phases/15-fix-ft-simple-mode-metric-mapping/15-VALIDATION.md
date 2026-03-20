---
phase: 15
slug: fix-ft-simple-mode-metric-mapping
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_scaffold.py tests/test_cli.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_scaffold.py tests/test_cli.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | FT-04 | unit | `python -m pytest tests/test_scaffold.py -k "finetuning" -x -q` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | UX-01 | unit | `python -m pytest tests/test_scaffold.py -k "metric" -x -q` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 1 | UX-01 | unit | `python -m pytest tests/test_cli.py -k "finetuning" -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scaffold.py` — add finetuning domain task mapping tests
- [ ] `tests/test_scaffold.py` — add FT metric override tests
- [ ] `tests/test_cli.py` — add FT simple mode integration tests

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
