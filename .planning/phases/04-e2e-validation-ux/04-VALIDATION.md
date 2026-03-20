---
phase: 4
slug: e2e-validation-ux
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
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
| 04-01-01 | 01 | 1 | UX-01 | unit | `python3 -m pytest tests/mlforge/test_profiler.py -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | UX-04 | unit | `python3 -m pytest tests/mlforge/test_profiler.py -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | UX-02 | unit | `python3 -m pytest tests/mlforge/test_cli.py::TestExpertMode -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | TABL-03 | integration | `python3 -m pytest tests/mlforge/test_profiler.py::test_temporal_detection -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | UX-03 | unit | `python3 -m pytest tests/mlforge/test_export.py -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | UX-05 | unit | `python3 -m pytest tests/mlforge/test_retrospective.py -x` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 2 | GUARD-06 | unit | `python3 -m pytest tests/mlforge/test_retrospective.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_profiler.py` — stubs for UX-01, UX-04, TABL-03
- [ ] `tests/mlforge/test_export.py` — stubs for UX-03
- [ ] `tests/mlforge/test_retrospective.py` — stubs for UX-05, GUARD-06
- [ ] Update `tests/mlforge/test_cli.py` — stubs for UX-02 expert mode flags

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E2E run on real dataset beats baselines | TABL-03 | Requires full claude -p agent loop with real data | Run `mlforge run --dataset titanic.csv --target Survived` and verify best model beats both baselines |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
