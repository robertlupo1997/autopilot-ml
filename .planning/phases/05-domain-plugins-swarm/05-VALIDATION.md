---
phase: 05
slug: domain-plugins-swarm
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 05-01-01 | 01 | 1 | DL-01, DL-02 | unit | `pytest tests/mlforge/test_dl_plugin.py -x -q` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | DL-03, DL-04 | unit | `pytest tests/mlforge/test_dl_plugin.py -x -q` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | DL-05 | unit | `pytest tests/mlforge/test_dl_plugin.py -x -q` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | FT-01, FT-02 | unit | `pytest tests/mlforge/test_ft_plugin.py -x -q` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 1 | FT-03, FT-04 | unit | `pytest tests/mlforge/test_ft_plugin.py -x -q` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 1 | FT-05 | unit | `pytest tests/mlforge/test_ft_plugin.py -x -q` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 2 | SWARM-01, SWARM-02 | unit | `pytest tests/mlforge/test_swarm.py -x -q` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 2 | SWARM-03 | unit | `pytest tests/mlforge/test_swarm.py -x -q` | ❌ W0 | ⬜ pending |
| 05-03-03 | 03 | 2 | SWARM-04 | unit | `pytest tests/mlforge/test_swarm.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_dl_plugin.py` — stubs for DL-01 through DL-05
- [ ] `tests/mlforge/test_ft_plugin.py` — stubs for FT-01 through FT-05
- [ ] `tests/mlforge/test_swarm.py` — stubs for SWARM-01 through SWARM-04

*Existing infrastructure covers test framework and conftest needs.*

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
