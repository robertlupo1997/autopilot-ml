---
phase: 08
slug: register-domain-plugins-swarm-cli
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-20
validated: 2026-03-20
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `python3 -m pytest tests/mlforge/ -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/ -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | DL-01..DL-05 | unit | `python3 -m pytest tests/mlforge/test_scaffold.py -x -k deeplearning` | Yes | green |
| 08-01-02 | 01 | 1 | FT-01..FT-05 | unit | `python3 -m pytest tests/mlforge/test_scaffold.py -x -k finetuning` | Yes | green |
| 08-02-01 | 02 | 1 | SWARM-01..SWARM-03 | unit | `python3 -m pytest tests/mlforge/test_cli.py -x -k swarm` | Yes | green |
| 08-02-02 | 02 | 1 | SWARM-04 | unit | `python3 -m pytest tests/mlforge/test_swarm.py -x -k verify` | Yes | green |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `tests/mlforge/test_scaffold.py` -- TestPluginRegistrationDispatch (5 tests) + TestScaffoldDomainDispatch (2 tests) cover DL/FT plugin registration
- [x] `tests/mlforge/test_cli.py` -- TestSwarmCli (5 tests) cover --swarm/--n-agents flags
- [x] `tests/mlforge/test_swarm.py` -- TestVerifierWiringInRun (2 tests) cover verify_best_result() call in run()

*All Wave 0 tests created during plan execution (TDD). 14 tests total covering all 14 requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (2026-03-20, Nyquist auditor)
