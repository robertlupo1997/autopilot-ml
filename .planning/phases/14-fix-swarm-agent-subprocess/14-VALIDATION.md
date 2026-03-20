---
phase: 14
slug: fix-swarm-agent-subprocess
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python3 -m pytest tests/test_mlforge_swarm.py -x -q` |
| **Full suite command** | `python3 -m pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_mlforge_swarm.py -x -q`
- **After every plan wave:** Run `python3 -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | ALL | unit | `python3 -m pytest tests/test_mlforge_swarm.py -x -q` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | SWARM-01 | unit | `python3 -m pytest tests/test_mlforge_swarm.py::TestBuildAgentCommand::test_includes_skip_permissions -x` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 1 | SWARM-03 | unit | `python3 -m pytest tests/test_mlforge_swarm.py::TestBuildAgentCommand::test_includes_max_budget -x` | ❌ W0 | ⬜ pending |
| 14-01-04 | 01 | 1 | SWARM-02, SWARM-04 | unit | `python3 -m pytest tests/test_mlforge_swarm.py::TestSetup::test_copies_claude_md -x` | ❌ W0 | ⬜ pending |
| 14-01-05 | 01 | 1 | SWARM-02 | unit | `python3 -m pytest tests/test_mlforge_swarm.py::TestBuildAgentCommand::test_template_has_state_json -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mlforge_swarm.py` — new test file for mlforge.swarm module
- [ ] Tests for `_build_agent_command()` flag verification (--dangerously-skip-permissions, --max-budget-usd)
- [ ] Tests for `setup()` CLAUDE.md copy behavior
- [ ] Test for swarm_claude.md.j2 state.json instruction

*Existing test_swarm.py tests automl.swarm (old API) — new file needed for mlforge.swarm.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full swarm E2E with real claude agents | ALL | Requires live claude CLI and API budget | Run `mlforge run --swarm` on a small dataset and verify agents complete |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
