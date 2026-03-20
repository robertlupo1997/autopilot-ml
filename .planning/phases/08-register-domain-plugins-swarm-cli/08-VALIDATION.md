---
phase: 08
slug: register-domain-plugins-swarm-cli
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `python -m pytest tests/mlforge/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/mlforge/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | DL-01..DL-05 | unit | `python -m pytest tests/mlforge/test_scaffold.py -x -k deeplearning` | No — W0 | pending |
| 08-01-02 | 01 | 1 | FT-01..FT-05 | unit | `python -m pytest tests/mlforge/test_scaffold.py -x -k finetuning` | No — W0 | pending |
| 08-02-01 | 02 | 1 | SWARM-01..SWARM-03 | unit | `python -m pytest tests/mlforge/test_cli.py -x -k swarm` | No — W0 | pending |
| 08-02-02 | 02 | 1 | SWARM-04 | unit | `python -m pytest tests/mlforge/test_swarm.py -x -k verify` | No — W0 | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_scaffold.py` — add tests for DL/FT plugin registration
- [ ] `tests/mlforge/test_cli.py` — add tests for --swarm/--n-agents flags
- [ ] `tests/mlforge/test_swarm.py` — add test for verify_best_result() call in run()

*Existing test infrastructure covers framework setup. Only new test functions needed.*

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
