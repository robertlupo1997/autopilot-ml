---
phase: 19
slug: add-dl-ft-baseline-gate
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml (pytest section) |
| **Quick run command** | `python -m pytest tests/mlforge/test_baselines.py tests/mlforge/test_engine.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/mlforge/test_baselines.py tests/mlforge/test_engine.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | INTL-01 | unit | `pytest tests/mlforge/test_dl_baselines.py -x` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | INTL-01 | unit | `pytest tests/mlforge/test_ft_baselines.py -x` | ❌ W0 | ⬜ pending |
| 19-01-03 | 01 | 1 | INTL-01 | unit | `pytest tests/mlforge/test_engine.py -k baselines -x` | ✅ partial | ⬜ pending |
| 19-01-04 | 01 | 1 | INTL-02 | unit | `pytest tests/mlforge/test_engine.py -k "baselines and deeplearning" -x` | ❌ W0 | ⬜ pending |
| 19-01-05 | 01 | 1 | INTL-02 | unit | `pytest tests/mlforge/test_engine.py -k "baselines and finetuning" -x` | ❌ W0 | ⬜ pending |
| 19-01-06 | 01 | 1 | INTL-02 | unit | `pytest tests/mlforge/test_baselines.py -x` | ✅ partial | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_dl_baselines.py` — stubs for INTL-01 DL baseline computation
- [ ] `tests/mlforge/test_ft_baselines.py` — stubs for INTL-01 FT baseline computation
- [ ] Update `test_baselines_skipped_for_non_tabular` in test_engine.py — currently asserts None, must verify baselines populated

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
