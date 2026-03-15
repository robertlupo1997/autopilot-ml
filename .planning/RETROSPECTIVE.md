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

## Milestone: v2.0 — Results-Driven Forecasting

**Shipped:** 2026-03-15
**Phases:** 4 | **Plans:** 6 | **Timeline:** 2 days

### What Was Built
- Walk-forward temporal validation infrastructure (`forecast.py` frozen module)
- Leakage-free forecast template with shift-first features and Optuna hyperparameter search
- 10-rule agent protocol (`claude_forecast.md.tmpl`) for forecasting experiments
- `--date-column` CLI flag wiring forecasting scaffold end-to-end
- E2E validation: Ridge MAPE 0.029 beats seasonal naive 0.061 (52% improvement)
- 80 new tests (250 → 330), 3 new source modules, 1 validation harness script

### What Worked
- **Auto-advance chain:** Phases 12→13→14 planned and executed in a single continuous session with `--auto` flag — zero manual intervention between phases
- **TDD during execution eliminated Wave 0 gaps:** All Nyquist audits found 0 missing tests because TDD RED/GREEN created tests inline with implementation
- **Phase 12 parallel execution:** Plans 12-01 and 12-02 ran simultaneously (no dependency) — total wall time ~12 min instead of ~20 min
- **Research accuracy:** Phase 14 researcher correctly predicted Ridge MAPE ~0.029 and seasonal naive ~0.061 — the actual E2E run matched exactly
- **Reusing v1.0 patterns:** Phase 14 harness reused Phase 7's proven script structure, avoiding rework

### What Was Inefficient
- **STATE.md drift persists:** The gsd-tools phase-complete updates don't propagate to all STATE.md sections (progress bar, current position) — still requires manual correction
- **VALIDATION.md still created as drafts:** Despite lesson from v1.0, VALIDATION.md files were created in planning and only updated during the bulk audit at the end. The TDD approach makes this less problematic (tests exist), but the status tracking is still post-hoc.
- **No milestone audit run:** Went straight from Nyquist validation to milestone completion without `/gsd:audit-milestone`. All 22 requirements were complete, but the audit would have caught any cross-phase integration issues.

### Patterns Established
- **Shift-first pattern:** `.shift(1)` before any `.rolling()` prevents temporal leakage — enforced in template code and CLAUDE.md protocol
- **Protocol rules over code enforcement:** Dual-baseline gate is a CLAUDE.md numbered rule, not a code check in loop_helpers — simpler, more flexible, agent-native
- **Separate renderers for distinct domains:** `_render_forecast_program_md()` separate from `render_program_md()` avoids domain-crossing text ("higher is always better" in a minimize context)

### Key Lessons
1. **Auto-advance is production-ready for autonomous phases** — 3 phases chained without intervention. Only Phase 14's human-action checkpoint (claude -p cannot nest) required a pause.
2. **TDD is the best Nyquist strategy** — writing tests as part of each task means 0 Wave 0 gaps and 0 missing tests at audit time. This should be the default for all future phases.
3. **Forecasting introduces metric direction complexity** — MAPE is minimize, but v1.0 assumed maximize everywhere. Future metrics need explicit direction handling from the start.
4. **Research predictions match reality** — investing in research that does empirical verification (the researcher actually ran the baselines) produces accurate planning estimates.

### Cost Observations
- Model mix: ~15% opus (orchestration), ~85% sonnet (research, planning, execution, verification)
- E2E validation run: $1.90 (well under $4.00 cap)
- Notable: Full pipeline (plan+execute all 4 phases) completed in a single session with auto-advance

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Timeline | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 6 days | 10 | Initial build — research-first, test-fix-test pattern |
| v2.0 | 2 days | 4 | Auto-advance chain, TDD eliminates Nyquist gaps |

### Cumulative Quality

| Milestone | Tests | Test Files | Source LOC | Test LOC |
|-----------|-------|-----------|-----------|---------|
| v1.0 | 250 | 16 | 1,977 | 3,496 |
| v2.0 | 330 | 21 | 2,562 | 4,417 |

### Top Lessons (Verified Across Milestones)

1. Research existing solutions deeply before building — prevents reinventing solved problems (v1.0, v2.0)
2. Test in the actual deployment mode (headless claude -p) — interactive and headless have different behaviors (v1.0, v2.0)
3. TDD during execution is the best validation strategy — 0 Wave 0 gaps in both milestones when tests written inline (v1.0, v2.0)
4. Auto-advance works for autonomous phases but stops correctly at human gates (v2.0)
