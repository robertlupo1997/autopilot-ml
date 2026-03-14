# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — AutoML MVP + Swarm

**Shipped:** 2026-03-14
**Phases:** 10 | **Plans:** 22 | **Timeline:** 6 days

### What Was Built
- Complete autonomous ML experimentation framework (14 Python modules, 1,977 LOC)
- CLI scaffolding: `uv run automl data.csv target metric` generates runnable experiment project
- Autonomous experiment loop: multi-draft start, keep/revert, crash recovery, stagnation detection
- PreToolUse hooks enforcing frozen file boundaries
- Checkpoint persistence for session resume
- Multi-agent swarm: parallel claude -p agents in git worktrees with file-locked scoreboard
- 250 tests across 16 test files (3,496 LOC tests)

### What Worked
- Test-first development: writing tests alongside implementation caught issues early (250 tests, zero gaps in final validation)
- Phase 4/7 test-fix-test pattern: running the loop first to discover problems, then fixing, then re-validating was highly effective
- Research-first approach: deep analysis of 6 existing frameworks (autoresearch, AIDE, SELA, AutoKaggle, ML-Agent, AI Scientist) before building prevented wasted effort
- Agent-driven architecture: letting CLAUDE.md instruct the agent rather than complex Python import chains kept the codebase simple
- Parallel execution: phases 8-10 planned and executed efficiently with wave-based parallelization

### What Was Inefficient
- VALIDATION.md files created as drafts during planning but never updated during execution — required a bulk auditing pass at the end
- STATE.md got stale — showed phase 5 at 60% even after all 10 phases completed
- REQUIREMENTS.md traceability table statuses lagged behind actual completion (25 entries still "Planned" despite being done)
- Some library modules (ExperimentRunner, ExperimentLogger, loop_helpers) were built but the agent-driven architecture made them unused in production — discovered during integration check

### Patterns Established
- **Agent-driven architecture:** Library modules provide utility functions; the agent follows CLAUDE.md protocol to invoke them via inline Python/bash, not traditional module imports
- **Broad allow + specific deny:** `Edit(*)/Write(*)` with `deny: [Edit(prepare.py), Write(prepare.py)]` — narrow patterns are silently ignored in headless claude -p mode
- **File-locked coordination:** fcntl.LOCK_EX on sidecar files for cross-process writes; lockless reads are acceptable (stale-by-one-row is fine)
- **Stdlib-only modules:** All new modules (checkpoint, swarm, scoreboard, claims) use only Python standard library

### Key Lessons
1. **Headless claude -p has different permission semantics** — settings.json permissions.allow works but requires broad glob patterns; narrow path patterns are silently ignored (GitHub issue #18160). Always test with headless mode, not just interactive.
2. **Validation should be continuous, not batched** — updating VALIDATION.md during execution instead of after would have saved the bulk auditing pass.
3. **Integration checking reveals architectural assumptions** — the integration checker found that the template rendering pipeline for swarm_claude.md was completely broken despite all unit tests passing. Cross-module wiring checks are essential.
4. **The agent IS the orchestrator** — in an agent-driven system, Python module imports matter less than CLAUDE.md instructions. The agent reads the protocol and acts; the library provides tools it calls ad-hoc.

### Cost Observations
- Model mix: ~20% opus (orchestration, planning), ~80% sonnet (execution, verification)
- Sessions: ~8 development sessions over 6 days
- Notable: 10 parallel Nyquist auditor agents completed in ~3 minutes vs ~30 minutes sequential

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Timeline | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 6 days | 10 | Initial build — research-first, test-fix-test pattern |

### Cumulative Quality

| Milestone | Tests | Test Files | Source LOC | Test LOC |
|-----------|-------|-----------|-----------|---------|
| v1.0 | 250 | 16 | 1,977 | 3,496 |

### Top Lessons (Verified Across Milestones)

1. Research existing solutions deeply before building — prevents reinventing solved problems
2. Test in the actual deployment mode (headless claude -p) — interactive and headless have different behaviors
3. Cross-phase integration checks catch wiring bugs that unit tests miss
