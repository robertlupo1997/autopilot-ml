---
phase: 06-fix-engine-subprocess-flags
verified: 2026-03-19T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 6: Fix Engine Subprocess Flags — Verification Report

**Phase Goal:** Fix invalid claude CLI flags in engine.py subprocess invocation so experiments can actually run
**Verified:** 2026-03-19
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `--append-system-prompt` with inline CLAUDE.md content is in subprocess command | VERIFIED | Line 134 of engine.py: `cmd.extend(["--append-system-prompt", system_prompt])` where `system_prompt = claude_md_path.read_text()` |
| 2 | `--max-turns` is NOT in the subprocess command | VERIFIED | `grep "max-turns" src/mlforge/engine.py` returns nothing; no reference anywhere in engine.py |
| 3 | `--append-system-prompt-file` is NOT in the subprocess command | VERIFIED | `grep "append-system-prompt-file" src/mlforge/engine.py` returns nothing |
| 4 | Engine gracefully handles missing CLAUDE.md (no crash) | VERIFIED | Line 123: `system_prompt = claude_md_path.read_text() if claude_md_path.exists() else ""`; flag omitted when empty (line 133: `if system_prompt:`) |
| 5 | Existing engine tests still pass after flag changes | VERIFIED | 30/30 engine tests pass; 421/421 total mlforge tests pass |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mlforge/engine.py` | Fixed `_run_one_experiment` with valid CLI flags; contains `--append-system-prompt` | VERIFIED | Lines 122-134: reads CLAUDE.md via `Path.read_text()`, builds cmd list without `--max-turns` or `--append-system-prompt-file`, conditionally extends with `--append-system-prompt` |
| `tests/mlforge/test_engine.py` | Tests verifying corrected flag structure; contains `append-system-prompt` assertions | VERIFIED | `TestCommandFlags` class at line 580: 4 tests cover inline content, no max-turns, graceful missing file, and budget regression guard |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/mlforge/engine.py` | `claude CLI` | subprocess.run command list with `--append-system-prompt` | WIRED | Line 134: `cmd.extend(["--append-system-prompt", system_prompt])`; subprocess.run called at line 140 with this cmd |
| `src/mlforge/engine.py` | `experiment_dir/CLAUDE.md` | `Path.read_text()` for inline content | WIRED | Line 122: `claude_md_path = self.experiment_dir / "CLAUDE.md"`; line 123: `system_prompt = claude_md_path.read_text() if claude_md_path.exists() else ""` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CORE-02 | 06-01-PLAN.md | Agent executes keep/revert experiment loop — modifies code, evaluates, commits on improvement, resets on failure | SATISFIED | Subprocess invocation now uses valid flags; keep/revert loop in `_process_result` is unchanged and functional. Engine can now actually spawn `claude -p` without flag-crash. |
| CORE-03 | 06-01-PLAN.md | Protocol prompt system injects domain-specific CLAUDE.md templates into agent context at session start | SATISFIED | `--append-system-prompt` with inline CLAUDE.md content injected per experiment via subprocess cmd (lines 122-134). Replaces the invalid `--append-system-prompt-file` flag. |
| INTL-07 | 06-01-PLAN.md | Experiment time/cost budget with per-experiment timeout and total session budget | SATISFIED | `--max-budget-usd` retained in cmd (line 130); `per_experiment_timeout_sec` passed to `subprocess.run` (line 144); `max_turns_per_experiment` kept in Config (config.py line 28) but not passed as invalid CLI flag. |
| GUARD-03 | 06-01-PLAN.md | Crash recovery automatically saves state before each experiment so sessions can resume | SATISFIED | `save_checkpoint(self.state, self._checkpoint_dir)` called before each `_run_one_experiment()` call in `run()` (line 77). With valid flags, the subprocess now actually runs, making checkpoint coverage meaningful. |

No orphaned requirements — all 4 declared requirement IDs (CORE-02, CORE-03, INTL-07, GUARD-03) are accounted for.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | None found |

No TODOs, FIXMEs, placeholder patterns, empty implementations, or stub handlers found in modified files.

### Human Verification Required

None. All truths are programmatically verifiable via code inspection and test execution.

### Gaps Summary

No gaps. All 5 must-have truths verified, both artifacts substantive and wired, both key links confirmed active, all 4 requirements satisfied. The P0 blocker (invalid subprocess flags preventing all experiments from running) is closed.

**Commit verification:**
- `be3b4c7` — TDD RED phase: added 4 failing `TestCommandFlags` tests (confirmed in git log)
- `0ee624b` — TDD GREEN phase: fixed engine.py flags, all 30 engine tests pass (confirmed in git log)

---

_Verified: 2026-03-19_
_Verifier: Claude (gsd-verifier)_
