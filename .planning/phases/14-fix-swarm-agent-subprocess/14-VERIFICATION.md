---
phase: 14-fix-swarm-agent-subprocess
verified: 2026-03-20T23:30:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 14: Fix Swarm Agent Subprocess Verification Report

**Phase Goal:** Fix swarm agent subprocess command to include required permission flags, budget enforcement, and CLAUDE.md in worktrees so swarm mode E2E flow works
**Verified:** 2026-03-20T23:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                         | Status     | Evidence                                                                                        |
| --- | --------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------- |
| 1   | Swarm agent subprocess includes --dangerously-skip-permissions flag                           | VERIFIED   | Line 196 in swarm/__init__.py; test_build_command_includes_skip_permissions passes              |
| 2   | Swarm agent subprocess includes --max-budget-usd with child budget value                      | VERIFIED   | Lines 197-198 use `str(child_config.budget_usd)`; test_build_command_includes_max_budget passes |
| 3   | CLAUDE.md is copied into each worktree during setup()                                         | VERIFIED   | Lines 88-91 in swarm/__init__.py; test_setup_copies_claude_md passes                           |
| 4   | .mlforge/ directory is created in each worktree during setup()                                | VERIFIED   | Line 92 in swarm/__init__.py; test_setup_creates_mlforge_dir passes                            |
| 5   | Swarm template instructs agents to write state.json with best_metric, best_commit, experiment_count | VERIFIED   | Lines 30-40 of swarm_claude.md.j2; test_template_has_state_json_instruction passes            |
| 6   | Agent subprocess includes --output-format json and --append-system-prompt flags               | VERIFIED   | Lines 195, 200-201 in swarm/__init__.py; test_build_command_includes_output_format and test_build_command_includes_append_system_prompt pass |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact                                        | Expected                                               | Status     | Details                                                                            |
| ----------------------------------------------- | ------------------------------------------------------ | ---------- | ---------------------------------------------------------------------------------- |
| `src/mlforge/swarm/__init__.py`                 | Fixed _build_agent_command() and setup() with CLAUDE.md copy | VERIFIED | 225 lines, contains `dangerously-skip-permissions`, `shutil.copy2`, `max-budget-usd` |
| `src/mlforge/templates/swarm_claude.md.j2`      | State persistence instruction for agents               | VERIFIED   | 41 lines, contains `state.json`, `best_metric`, `best_commit`, `experiment_count` |
| `tests/mlforge/test_mlforge_swarm.py`           | Unit tests for swarm command flags, setup copy, and template content | VERIFIED | 161 lines (> 50 min), 8 tests in 3 test classes, all pass |

### Key Link Verification

| From                              | To                                      | Via                                                    | Status  | Details                                                                                           |
| --------------------------------- | --------------------------------------- | ------------------------------------------------------ | ------- | ------------------------------------------------------------------------------------------------- |
| `src/mlforge/swarm/__init__.py`   | `src/mlforge/engine.py`                 | Same CLI flag pattern (--dangerously-skip-permissions, --max-budget-usd, --append-system-prompt) | WIRED | Both files use identical flag names; swarm lines 192-201 mirror engine.py lines 158-167  |
| `src/mlforge/swarm/__init__.py`   | `src/mlforge/templates/swarm_claude.md.j2` | Template render in _build_agent_command() via get_template_env() | WIRED | Lines 177-187 call `env.get_template("swarm_claude.md.j2")` and render it as prompt |
| `src/mlforge/templates/swarm_claude.md.j2` | `.mlforge/state.json`          | Template instructs agent to write state.json           | WIRED   | Lines 31-40 of template contain explicit write instruction with JSON schema                       |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                             | Status    | Evidence                                                                                                                 |
| ----------- | ----------- | --------------------------------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------ |
| SWARM-01    | 14-01-PLAN  | Swarm mode spawns parallel agents in git worktrees exploring different model families   | SATISFIED | --dangerously-skip-permissions flag enables agents to write files; setup() creates worktrees and provisions them         |
| SWARM-02    | 14-01-PLAN  | File-locked scoreboard coordinates best result across parallel agents                   | SATISFIED | run() reads state.json from each worktree and calls scoreboard.publish_result() (lines 122-140 of swarm/__init__.py)    |
| SWARM-03    | 14-01-PLAN  | Budget inheritance prevents spawn explosion — child agents inherit parent's remaining budget | SATISFIED | --max-budget-usd str(child_config.budget_usd) enforced at subprocess level; create_child_configs() splits parent budget |
| SWARM-04    | 14-01-PLAN  | Verification agent checks metric improvement claims against actual holdout performance  | SATISFIED | verifier.py exists at src/mlforge/swarm/verifier.py; verify_best_result() called in run() lines 147-153                 |

**Note on SWARM-04:** verifier.py was created in phase 05 and wired into run() in phase 08. Phase 14 does not introduce it but is required for end-to-end functionality since agents could not previously write results (no permissions) — the verification flow was unreachable before this fix.

**Requirement traceability status in REQUIREMENTS.md:** All four SWARM requirements are still marked "Pending" in the traceability table at the time of verification. The implementations are complete and confirmed, but the table has not been updated to "Complete". This is a documentation gap only, not a code gap.

### Anti-Patterns Found

| File                              | Line | Pattern                | Severity | Impact                                                                               |
| --------------------------------- | ---- | ---------------------- | -------- | ------------------------------------------------------------------------------------ |
| `tests/test_cli.py`               | 43   | Pre-existing test failure: `test_cli_valid_args` fails with "string dtypes are not allowed, use 'object' instead" | Warning | Pre-dates phase 14 (last touched in phase 13-01 commit b8f24a5); not introduced by this phase. 523 other tests pass. |

The `test_cli_valid_args` failure is unrelated to swarm subprocess: it is a pandas/sklearn dtype compatibility issue in the CLI integration test, last modified before phase 14 began. All 8 swarm-specific tests pass.

### Human Verification Required

None. All observable truths are verifiable programmatically via grep and test execution.

### Gaps Summary

No gaps. All six must-have truths are verified. All three artifacts exist, are substantive, and are correctly wired. All four SWARM requirements have implementation evidence.

The only outstanding item is a documentation update: the REQUIREMENTS.md traceability table still shows SWARM-01 through SWARM-04 as "Pending" even though the code fully satisfies them. That table update is out of scope for this phase's deliverables.

---

_Verified: 2026-03-20T23:30:00Z_
_Verifier: Claude (gsd-verifier)_
