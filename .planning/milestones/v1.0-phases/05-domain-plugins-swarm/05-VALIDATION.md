---
phase: 05
slug: domain-plugins-swarm
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-20
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python3 -m pytest tests/mlforge/ -x -q --timeout=30` |
| **Full suite command** | `python3 -m pytest tests/mlforge/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/ -x -q --timeout=30`
- **After every plan wave:** Run `python3 -m pytest tests/mlforge/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | DL-01 | unit | `pytest tests/mlforge/test_dl_plugin.py -x -q` | TDD self-created | pending |
| 05-01-02 | 01 | 1 | DL-02 | unit | `pytest tests/mlforge/test_dl_plugin.py -x -q` | TDD self-created | pending |
| 05-01-03 | 01 | 1 | DL-03, DL-04, DL-05 | unit | `pytest tests/mlforge/test_dl_plugin.py -x -q` | TDD self-created | pending |
| 05-02-01 | 02 | 1 | FT-01 | unit | `pytest tests/mlforge/test_ft_plugin.py -x -q` | TDD self-created | pending |
| 05-02-02 | 02 | 1 | FT-02, FT-05 | unit | `pytest tests/mlforge/test_ft_plugin.py -x -q` | TDD self-created | pending |
| 05-02-03 | 02 | 1 | FT-03, FT-04 | unit | `pytest tests/mlforge/test_ft_plugin.py -x -q` | TDD self-created | pending |
| 05-03-01 | 03 | 1 | SWARM-02 | unit | `pytest tests/mlforge/test_scoreboard.py -x -q` | TDD self-created | pending |
| 05-03-02 | 03 | 1 | SWARM-01, SWARM-03, SWARM-04 | unit | `pytest tests/mlforge/test_swarm.py -x -q` | TDD self-created | pending |

*Status: pending -- green -- red -- flaky*

---

## Wave 0 Requirements

All plans use TDD pattern where Task 1 writes tests before implementation. Test files are self-created by the TDD tasks -- no separate Wave 0 scaffolding needed.

- [x] `tests/mlforge/test_dl_plugin.py` -- created by Plan 01 Task 1 (TDD: tests written first)
- [x] `tests/mlforge/test_ft_plugin.py` -- created by Plan 02 Task 1 (TDD: tests written first)
- [x] `tests/mlforge/test_swarm.py` -- created by Plan 03 Task 2 (TDD: tests written first)
- [x] `tests/mlforge/test_scoreboard.py` -- created by Plan 03 Task 1 (TDD: tests written first)

*Wave 0 is satisfied by TDD self-creation pattern. No pre-existing test stubs required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GPU training completes within time budget | DL-04 | Requires GPU hardware | Run `mlforge --domain dl <dataset> <goal>` on GPU machine, verify time cap |
| LoRA fine-tuning produces valid adapter | FT-01 | Requires GPU + model download | Run `mlforge --domain ft <dataset> <goal>`, verify adapter weights saved |
| Swarm agents coordinate in real worktrees | SWARM-01 | Requires live claude -p sessions | Run `mlforge --swarm <dataset> <goal>`, verify parallel agent execution |
| Verification agent catches inflated metrics | SWARM-04 | Requires live claude -p + holdout data | Run swarm session, check verification agent re-evaluates best model |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (TDD self-creation resolves all)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
