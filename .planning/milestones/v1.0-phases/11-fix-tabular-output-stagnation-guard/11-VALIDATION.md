---
phase: 11
slug: fix-tabular-output-stagnation-guard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python3 -m pytest tests/mlforge/test_stagnation.py tests/mlforge/test_engine.py tests/mlforge/test_templates.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/mlforge/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/test_stagnation.py tests/mlforge/test_engine.py tests/mlforge/test_templates.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/mlforge/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | CORE-02 | unit | `python3 -m pytest tests/mlforge/test_templates.py -x -q -k "tabular"` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | CORE-03 | unit | `python3 -m pytest tests/mlforge/test_templates.py -x -q -k "claude"` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | CORE-09 | unit | `python3 -m pytest tests/mlforge/test_stagnation.py -x -q` | ✅ (needs update) | ⬜ pending |
| 11-01-04 | 01 | 1 | INTL-04 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -q -k "stagnation"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_templates.py` — add test: rendered tabular_train.py contains `json.dumps` and `metric_value`
- [ ] `tests/mlforge/test_templates.py` — add test: rendered CLAUDE.md contains output format section
- [ ] `tests/mlforge/test_stagnation.py::test_no_best_commit_raises` — update: assert returns None instead of ValueError
- [ ] `tests/mlforge/test_engine.py` — add test: stagnation with best_commit=None does not crash and does not append to tried_families

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
