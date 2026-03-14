---
phase: 10
slug: multi-agent-swarm
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (uv run pytest) |
| **Config file** | none — pytest auto-discovers tests/ |
| **Quick run command** | `uv run pytest tests/test_swarm*.py tests/test_git.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_swarm*.py tests/test_git.py tests/test_cli.py tests/test_scaffold.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | scoreboard publish | unit | `uv run pytest tests/test_swarm_scoreboard.py -x -q` | Wave 0 | ⬜ pending |
| 10-01-02 | 01 | 1 | scoreboard concurrent writes | unit (threading) | `uv run pytest tests/test_swarm_scoreboard.py::TestConcurrentWrites -x -q` | Wave 0 | ⬜ pending |
| 10-01-03 | 01 | 1 | scoreboard read_best | unit | `uv run pytest tests/test_swarm_scoreboard.py::TestReadBest -x -q` | Wave 0 | ⬜ pending |
| 10-01-04 | 01 | 1 | claims try_claim | unit | `uv run pytest tests/test_swarm_claims.py -x -q` | Wave 0 | ⬜ pending |
| 10-01-05 | 01 | 1 | claims TTL expiry | unit | `uv run pytest tests/test_swarm_claims.py::TestTTLExpiry -x -q` | Wave 0 | ⬜ pending |
| 10-01-06 | 01 | 1 | git worktree create | integration | `uv run pytest tests/test_git.py -x -q` | Modify existing | ⬜ pending |
| 10-01-07 | 01 | 1 | git worktree remove | integration | `uv run pytest tests/test_git.py -x -q` | Modify existing | ⬜ pending |
| 10-02-01 | 02 | 2 | family partitioning | unit | `uv run pytest tests/test_swarm.py::TestDivideFamilies -x -q` | Wave 0 | ⬜ pending |
| 10-02-02 | 02 | 2 | CLI --agents flag | unit | `uv run pytest tests/test_cli.py -x -q` | Modify existing | ⬜ pending |
| 10-02-03 | 02 | 2 | scaffold .swarm/ gitignore | unit | `uv run pytest tests/test_scaffold.py -x -q` | Modify existing | ⬜ pending |
| 10-03-01 | 03 | 3 | 2-agent swarm smoke test | manual smoke | `./scripts/run-swarm-test.sh` | Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_swarm_scoreboard.py` — stubs for scoreboard publish, concurrent writes, read_best
- [ ] `tests/test_swarm_claims.py` — stubs for claim TTL, dedup, release
- [ ] `tests/test_swarm.py` — stubs for SwarmManager setup, _divide_families, teardown

*Existing infrastructure covers git_ops, cli, scaffold tests — will be extended in-place.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 2-agent swarm produces results in scoreboard | end-to-end swarm | Requires spawning real `claude -p` processes and git worktrees | Run `./scripts/run-swarm-test.sh`, verify scoreboard.json has entries from both agents |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
