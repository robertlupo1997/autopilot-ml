---
status: testing
phase: 06-fix-engine-subprocess-flags
source: 06-01-SUMMARY.md
started: 2026-03-20T03:15:00Z
updated: 2026-03-20T03:15:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: No invalid --max-turns flag in subprocess command
expected: |
  Run `grep -n "max.turns" src/mlforge/engine.py` — should NOT find any `--max-turns` flag being passed to the subprocess command. The config field `max_turns_per_experiment` may still exist in Config, but it must not appear as a CLI flag in the subprocess invocation.
awaiting: user response

## Tests

### 1. No invalid --max-turns flag in subprocess command
expected: Run `grep -n "max.turns" src/mlforge/engine.py` — should NOT find any `--max-turns` flag being passed to the subprocess command. The config field `max_turns_per_experiment` may still exist in Config, but it must not appear as a CLI flag in the subprocess invocation.
result: [pending]

### 2. --append-system-prompt used with inline content
expected: Run `grep -n "append-system-prompt" src/mlforge/engine.py` — should find `--append-system-prompt` (NOT `--append-system-prompt-file`) being used. The CLAUDE.md content should be read via `Path.read_text()` and passed inline as a string argument.
result: [pending]

### 3. Graceful handling when CLAUDE.md is missing
expected: The code should check if the CLAUDE.md file exists before reading it. Run `grep -n "exists\|claude_md" src/mlforge/engine.py` — should find an existence check (`if ... .exists()`) that guards the read. When CLAUDE.md is missing, the `--append-system-prompt` flag should be omitted entirely (no empty string passed).
result: [pending]

### 4. All engine tests pass
expected: Run `python -m pytest tests/mlforge/test_engine.py -v` — all tests pass including the new `TestCommandFlags` class with 4 tests verifying corrected flag structure.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Gaps

[none yet]
