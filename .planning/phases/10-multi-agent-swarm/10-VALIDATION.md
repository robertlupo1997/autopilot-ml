---
phase: 10
slug: multi-agent-swarm
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-14
audited: 2026-03-14
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Test Functions | Status |
|---------|------|------|-------------|-----------|-------------------|----------------|--------|
| 10-01-01 | 01 | 1 | scoreboard publish | unit | `uv run pytest tests/test_swarm_scoreboard.py::TestPublishResult -x -q` | `TestPublishResult` (8 tests) | green |
| 10-01-02 | 01 | 1 | scoreboard concurrent writes | unit (threading) | `uv run pytest tests/test_swarm_scoreboard.py::TestConcurrentWrites -x -q` | `TestConcurrentWrites::test_concurrent_writes_no_corruption` | green |
| 10-01-03 | 01 | 1 | scoreboard read_best | unit | `uv run pytest tests/test_swarm_scoreboard.py::TestReadBest -x -q` | `TestReadBest` (6 tests) | green |
| 10-01-04 | 01 | 1 | claims try_claim | unit | `uv run pytest tests/test_swarm_claims.py::TestTryClaim -x -q` | `TestTryClaim` (5 tests), `TestReleaseClaim` (3 tests) | green |
| 10-01-05 | 01 | 1 | claims TTL expiry | unit | `uv run pytest tests/test_swarm_claims.py::TestTTLExpiry -x -q` | `TestTTLExpiry::test_expired_claim_allows_reclaim`, `test_active_claim_blocks` | green |
| 10-01-06 | 01 | 1 | git worktree create | integration | `uv run pytest tests/test_git.py::TestWorktree::test_create_worktree tests/test_git.py::TestWorktree::test_worktree_has_git_file_not_dir -x -q` | `TestWorktree::test_create_worktree`, `test_worktree_has_git_file_not_dir` | green |
| 10-01-07 | 01 | 1 | git worktree remove | integration | `uv run pytest tests/test_git.py::TestWorktree::test_remove_worktree -x -q` | `TestWorktree::test_remove_worktree` | green |
| 10-02-01 | 02 | 2 | family partitioning | unit | `uv run pytest tests/test_swarm.py::TestDivideFamilies -x -q` | `TestDivideFamilies` (5 tests including round-robin order) | green |
| 10-02-02 | 02 | 2 | CLI --agents flag | unit | `uv run pytest tests/test_cli.py::TestCliAgentsFlag -x -q` | `TestCliAgentsFlag` (5 tests: default, accepted, zero-error, help, help-mentions-terminal) | green |
| 10-02-03 | 02 | 2 | scaffold .swarm/ gitignore | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldGitignoreSwarm -x -q` | `TestScaffoldGitignoreSwarm` (4 tests: tsv, lock, config, best_train entries) | green |
| 10-03-01 | 03 | 3 | 2-agent swarm smoke test | manual smoke | `bash -n scripts/run-swarm-test.sh && test -x scripts/run-swarm-test.sh` | Script exists, syntax-valid, executable | green |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [x] `tests/test_swarm_scoreboard.py` — 16 tests: TestPublishResult (8), TestReadBest (6), TestConcurrentWrites (1 threading test for 5 threads x 10 results)
- [x] `tests/test_swarm_claims.py` — 9 tests: TestTryClaim (5), TestTTLExpiry (2), TestReleaseClaim (3)
- [x] `tests/test_swarm.py` — 25 tests: TestDivideFamilies (5), TestSetup (7), TestTeardown (4), TestSpawnAgent (9)

*Existing infrastructure covers git_ops, cli, scaffold tests — extended in-place.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 2-agent swarm produces results in scoreboard | end-to-end swarm | Requires spawning real `claude -p` processes and git worktrees | Run `./scripts/run-swarm-test.sh`, verify scoreboard.json has entries from both agents |

---

## Audit Summary (2026-03-14)

Cross-referenced all 11 task rows against actual test functions. Findings:

- All test files existed with full implementations (not stubs)
- 100/100 tests passed on first run (`uv run pytest tests/test_swarm_scoreboard.py tests/test_swarm_claims.py tests/test_swarm.py tests/test_git.py tests/test_cli.py tests/test_scaffold.py -v`)
- `scripts/run-swarm-test.sh` exists, passes `bash -n` syntax check, and is executable
- No missing tests identified — all VALIDATION.md rows have corresponding passing test functions

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** nyquist_compliant (audited 2026-03-14)
