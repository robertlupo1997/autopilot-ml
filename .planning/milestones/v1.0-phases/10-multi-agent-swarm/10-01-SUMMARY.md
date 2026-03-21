---
phase: 10-multi-agent-swarm
plan: 01
subsystem: infra
tags: [fcntl, file-locking, git-worktrees, swarm, coordination, stdlib]

# Dependency graph
requires:
  - phase: 09-resume-capability
    provides: checkpoint.py -- establishes pattern for stdlib-only coordination files
  - phase: 08-permissions-simplification
    provides: git_ops.py GitManager class that is extended here
provides:
  - SwarmScoreboard class with fcntl.LOCK_EX file-locked TSV publish and lockless read_best
  - swarm_claims TTL-based claim files for iteration-phase experiment dedup
  - GitManager.create_worktree and remove_worktree for agent isolation
affects:
  - 10-02-swarm-manager: imports SwarmScoreboard, swarm_claims, and GitManager worktree methods

# Tech tracking
tech-stack:
  added: [fcntl (stdlib file locking), hashlib (MD5 claim key generation)]
  patterns:
    - fcntl.LOCK_EX on a dedicated .lock file for scoreboard writes; never read from lockfile
    - Lockless reads of append-only TSV (atomic enough for worst-case stale-by-one-row)
    - Read-time TTL expiry check (no background daemon needed)
    - MD5 first-8-hex-chars as claim filename key for collision-resistant dedup

key-files:
  created:
    - src/automl/swarm_scoreboard.py
    - src/automl/swarm_claims.py
    - tests/test_swarm_scoreboard.py
    - tests/test_swarm_claims.py
  modified:
    - src/automl/git_ops.py
    - tests/test_git.py

key-decisions:
  - "fcntl.LOCK_EX on scoreboard.lock (not scoreboard.tsv) -- lock file is write-only, never read"
  - "Lockless read_best: single-line TSV appends are atomic on Linux; worst case stale by one row is acceptable"
  - "CLAIM_TTL=300s (5 min): generous enough for slow experiments, short enough to prevent indefinite blocking"
  - "MD5 first-8-hex-chars for claim key: fast, no collisions in practice for experiment description dedup"
  - "missing_ok=True on release_claim unlink: idempotent, safe to call multiple times"

patterns-established:
  - "Pattern: file-locked coordination via fcntl.LOCK_EX on .lock sidecar file (not main data file)"
  - "Pattern: TDD with RED (failing tests), GREEN (minimal implementation), no REFACTOR needed (code clean)"

requirements-completed: [SWARM-01, SWARM-02, SWARM-03]

# Metrics
duration: 8min
completed: 2026-03-14
---

# Phase 10 Plan 01: Core Swarm Infrastructure Summary

**File-locked TSV scoreboard (fcntl.LOCK_EX), TTL claim files (hashlib+json), and git worktree methods on GitManager -- all stdlib, all tested with 28 new passing tests**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-14T00:00:00Z
- **Completed:** 2026-03-14T00:08:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- SwarmScoreboard with file-locked publish_result and lockless read_best -- concurrent writes from 5 threads produce no corruption
- swarm_claims TTL-based try_claim/release_claim -- active claims block, expired claims allow re-claiming
- GitManager.create_worktree and remove_worktree -- each worktree has .git file (pointer), not directory
- 28 new tests (16 scoreboard, 9 claims, 3 worktree) + full 199-test suite passing

## Task Commits

Each task was committed atomically:

1. **Task 1: SwarmScoreboard and SwarmClaims modules with tests** - `40a1d2e` (feat)
2. **Task 2: GitManager worktree methods with tests** - `acdb5c0` (feat)

## Files Created/Modified
- `src/automl/swarm_scoreboard.py` - SwarmScoreboard class with fcntl.LOCK_EX publish_result and lockless read_best
- `src/automl/swarm_claims.py` - try_claim/release_claim with CLAIM_TTL=300s TTL-based dedup
- `src/automl/git_ops.py` - Added create_worktree() and remove_worktree() methods to GitManager
- `tests/test_swarm_scoreboard.py` - 16 tests: publish, read_best, concurrent writes (5 threads x 10 results)
- `tests/test_swarm_claims.py` - 9 tests: dedup, TTL expiry (monkeypatched time), release
- `tests/test_git.py` - Added TestWorktree class with 3 integration tests

## Decisions Made
- fcntl.LOCK_EX on scoreboard.lock (separate from scoreboard.tsv): lockfile is purely a lock primitive, never read
- Lockless read_best: append-only TSV writes are effectively atomic on Linux; worst-case stale-by-one-row is acceptable
- CLAIM_TTL=300s: generous enough for slow ML experiments, short enough that stale claims clear in 5 minutes
- MD5 first-8-hex-chars for claim key: fast hash, no practical collisions for experiment description strings

## Deviations from Plan

None - plan executed exactly as written. Code from 10-RESEARCH.md Pattern 2 (scoreboard) and Pattern 5 (claims) was used verbatim with minor additions (docstrings, type annotations).

## Issues Encountered

None. All three modules worked correctly on first GREEN run. Concurrent write test passed immediately with 5 threads.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- SwarmScoreboard, swarm_claims, and GitManager worktree methods ready for Plan 10-02 (SwarmManager integration)
- Plan 10-02 will compose these primitives into SwarmManager.setup(), run(), monitor(), teardown()
- No blockers

---
*Phase: 10-multi-agent-swarm*
*Completed: 2026-03-14*
