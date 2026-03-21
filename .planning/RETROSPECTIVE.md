# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: mlforge v1.0 — Multi-Domain Autonomous ML Framework

**Shipped:** 2026-03-21
**Phases:** 24 | **Plans:** 34 | **Timeline:** 3 days

### What Was Built
- Ground-up rewrite of autopilot-ml into a plugin-based multi-domain framework (src/mlforge/)
- Three domain plugins: tabular ML, deep learning, LLM fine-tuning
- Core engine with experiment loop, git state management, checkpoint/resume, guardrails
- Intelligence layer: diagnostics, multi-draft, branch-on-stagnation, experiment journal
- Swarm mode: parallel agents in git worktrees with file-locked scoreboard
- CLI with simple mode (auto-detect) and expert mode (full control)
- Full documentation: README, CONTRIBUTING, 7 guides in docs/
- 583 tests, 48/48 requirements satisfied

### What Worked
- **Parallel agent execution for docs:** 6 agents launched in parallel to write README, guides, CONTRIBUTING, fix tests — completed in ~90 seconds total wall time
- **GSD framework for phased delivery:** 24 phases with clear success criteria kept scope tight
- **Milestone audit caught integration gaps:** Initial 5-phase build had all features passing unit tests but many weren't wired at runtime. The audit process identified 18 additional phases needed for full integration.
- **Protocol-first design validated:** All agent behaviors are CLAUDE.md text rules, not code enforcement. Simpler, more flexible, and proven to work in E2E runs.
- **Plugin architecture scales:** Adding DL and FT domains was straightforward once the tabular plugin validated the architecture.

### What Was Inefficient
- **Integration wiring dominated (phases 6-22):** 18 of 24 phases were fixing wiring gaps, not building features. Building integration tests earlier would have caught these during initial development.
- **Legacy code lingered:** src/automl/ and 24 legacy test files sat around until manual cleanup at the end. Should have been removed when the rewrite was confirmed working.
- **Agent file write permissions:** Background agents (claude -p) couldn't write files due to permission restrictions, requiring manual re-execution of their output. Need to pass --allowedTools correctly.
- **STATE.md drift:** GSD state tracking got stale repeatedly across milestones.

### Patterns Established
- **Plugin protocol via typing.Protocol:** Structural subtyping — plugins just implement the interface, no inheritance needed
- **Domain-keyed dispatch:** _TASK_TYPE_MAP, _DOMAIN_DEFAULT_TASK, get_families_for_domain() for domain-aware behavior
- **Fallback chains:** Result collection tries state.json -> checkpoint.json -> explicit error
- **Lazy imports:** Heavy ML dependencies (torch, peft, sklearn) imported inside methods, not at module level
- **Template variables as Python constants:** Rendered train.py uses LORA_R, LORA_ALPHA etc. for readability

### Key Lessons
1. **Build integration tests alongside unit tests** — unit tests passing doesn't mean features are wired together. 18 phases of wiring fixes could have been 2-3 if integration tests existed from the start.
2. **Parallel doc writing with agents is fast** — 8 doc files written in parallel in ~90s. Use this pattern for any bulk content generation.
3. **Clean up legacy code immediately** — don't leave old packages around "for reference." They accumulate stale tests and confuse tooling.
4. **Audit milestones before shipping** — the GSD audit process found real gaps that would have been bugs in production.

### Cost Observations
- Model mix: ~20% opus (orchestration, planning), ~80% sonnet (execution, verification)
- 24 phases completed across ~5 sessions
- Doc generation: ~$2 for 6 parallel agents writing 8 files

---

## Prior Milestones (autopilot-ml, archived)

The following milestones were from the old autopilot-ml codebase (src/automl/, now deleted). Lessons carried forward into mlforge design.

### v3.0 Intelligent Iteration (Shipped: 2026-03-15)

**Phases:** 4 | **Plans:** 6 | **Timeline:** 1 day

Key lessons carried forward:
- Protocol-first design (CLAUDE.md text rules) is more flexible than code enforcement
- Branch-on-stagnation prevents agents getting stuck in local optima
- Plan checker revision loop catches real dependency issues before execution

### v2.0 Results-Driven Forecasting (Shipped: 2026-03-15)

**Phases:** 4 | **Plans:** 6 | **Timeline:** 2 days

Key lessons carried forward:
- Shift-first pattern (.shift(1) before .rolling()) prevents temporal leakage
- Auto-advance chains work for autonomous phase execution
- TDD during execution eliminates Nyquist validation gaps

### v1.0 AutoML MVP + Swarm (Shipped: 2026-03-14)

**Phases:** 10 | **Plans:** 22 | **Timeline:** 6 days

Key lessons carried forward:
- Agent-driven architecture: CLAUDE.md instructs, library provides tools
- File-locked coordination (fcntl.LOCK_EX) for cross-process writes
- Headless claude -p has different permission semantics than interactive mode
- Integration checking reveals architectural assumptions that unit tests miss

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Timeline | Phases | Key Change |
|-----------|----------|--------|------------|
| autopilot-ml v1.0 | 6 days | 10 | Initial build, research-first |
| autopilot-ml v2.0 | 2 days | 4 | Auto-advance, TDD |
| autopilot-ml v3.0 | 1 day | 4 | Full auto-advance, plan checker |
| mlforge v1.0 | 3 days | 24 | Ground-up rewrite, 3 domains, audit-driven integration |

### Top Lessons (Verified Across Milestones)

1. Research existing solutions deeply before building (all milestones)
2. Test in the actual deployment mode (headless claude -p) (all milestones)
3. TDD during execution is the best validation strategy (v2.0, v3.0, mlforge)
4. Auto-advance works for autonomous phases but stops at human gates (v2.0, v3.0)
5. Integration tests are as important as unit tests (mlforge v1.0)
6. Parallel agent execution dramatically speeds up bulk work (mlforge v1.0)
