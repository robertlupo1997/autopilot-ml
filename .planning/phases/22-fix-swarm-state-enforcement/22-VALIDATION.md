---
phase: 22
slug: fix-swarm-state-enforcement
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` [tool.pytest] |
| **Quick run command** | `python3 -m pytest tests/mlforge/test_mlforge_swarm.py tests/mlforge/test_swarm.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/mlforge/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/test_mlforge_swarm.py tests/mlforge/test_swarm.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/mlforge/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | SWARM-02 | unit | `python3 -m pytest tests/mlforge/test_swarm_state_enforcement.py::test_result_collection_from_subprocess_output -x` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 1 | SWARM-02 | unit | `python3 -m pytest tests/mlforge/test_swarm_state_enforcement.py::test_fallback_to_checkpoint -x` | ❌ W0 | ⬜ pending |
| 22-01-03 | 01 | 1 | SWARM-02 | unit | `python3 -m pytest tests/mlforge/test_swarm_state_enforcement.py::test_malformed_state_json -x` | ❌ W0 | ⬜ pending |
| 22-01-04 | 01 | 1 | SWARM-03 | unit | `python3 -m pytest tests/mlforge/test_swarm_state_enforcement.py::test_budget_agents_result_collection -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_swarm_state_enforcement.py` — covers SWARM-02, SWARM-03 with fallback and subprocess capture tests

*Existing test infrastructure (fixtures, conftest) is sufficient — no additional setup needed.*

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
