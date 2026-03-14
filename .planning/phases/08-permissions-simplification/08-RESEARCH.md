# Phase 8: Permissions Simplification - Research

**Researched:** 2026-03-13
**Domain:** Claude Code headless permissions, settings.json, --allowedTools
**Confidence:** HIGH

## Summary

Phase 8 exists to clean up technical debt introduced during Phase 7 gap closure. The Phase 7 validation run revealed that `settings.json` permissions.allow is silently ignored in headless `claude -p` mode, forcing the Phase 7 fix to rely on `--allowedTools` flags in `scripts/run-validation-test.sh`. The scaffolded experiment directory now contains a settings.json that is effectively a no-op for its core function (governing headless tool access), while the shell script carries the actual permission payload.

Three concrete problems need resolution:

1. **Dead-weight narrow patterns:** The original Phase 5 design used narrow patterns like `Edit(train.py)`, `Write(train.py)` based on the assumption settings.json governed headless mode. These patterns do nothing in headless mode and should either be broadened or removed. The Phase 7 fix already broadened them in settings.json to `Bash(*)`, `Edit(train.py)`, `Write(train.py)`, `Write(results.tsv)`, `Write(run.log)`, but the validation script still passes `Write(*)` and `Edit(*)` via `--allowedTools`, indicating the scaffold and script are out of sync.

2. **Missing permissions.deny for frozen files:** The current approach relies entirely on the guard-frozen.sh PreToolUse hook to block writes to prepare.py. A `permissions.deny` rule for `Edit(prepare.py)` and `Write(prepare.py)` would add defense-in-depth — but a known security bug (issue #6699, fixed as of the issue being closed) means deny rules may need verification. The hook remains the primary enforcement mechanism; deny is supplementary.

3. **--allowedTools in run-validation-test.sh:** The current validation script hard-codes `--allowedTools "Bash(*)" "Edit(*)" "Write(*)" "Read" "Glob" "Grep"`. If the scaffolded directory's settings.json were the authoritative source, the script could omit `--allowedTools` entirely and rely on the project settings. But since settings.json allow rules are ignored in headless mode, the script must always pass `--allowedTools`. The goal is to make this situation explicit and documented — not to silently break future validation runs.

**Primary recommendation:** Simplify `_dot_claude_settings` in scaffold.py to generate a clean, minimal settings.json with broad patterns matching what `--allowedTools` passes. Add `permissions.deny` for prepare.py with a code comment noting the hook is primary enforcement. Update `run-validation-test.sh` to use the same broad patterns for consistency and document the "settings.json allow rules don't work in headless mode" finding prominently.

## Standard Stack

### Core (no new dependencies)
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| scaffold.py | existing | Generates .claude/settings.json | All settings.json mutations go here |
| guard-frozen.sh | existing | PreToolUse hook, denies writes to prepare.py | Hook-based deny is the ONLY reliable block mechanism |
| run-validation-test.sh | existing | Passes --allowedTools for headless mode | settings.json allow rules silently ignored in headless -p |
| tests/test_scaffold.py | existing | Asserts settings.json structure | All settings.json changes need test coverage |

### No new packages needed
Phase 8 is a settings/scaffolding change only. Zero new Python dependencies.

## Architecture Patterns

### Pattern 1: Settings.json as Documentation, --allowedTools as Enforcement

**What:** In headless `claude -p` mode, `settings.json` permissions.allow rules are ignored. The `--allowedTools` CLI flag is the sole enforcement mechanism. Settings.json serves as documentation of intent for interactive use and for developers reading the scaffolded project.

**When to use:** Always for headless mode. Settings.json allow rules do apply in interactive `claude` (non-headless) mode.

**Confirmed by:** Phase 7 FINDINGS.md — 8 permission denials with settings.json only, 0 denials after adding `--allowedTools` to the invocation. Also confirmed by GitHub issue #18160 (allow rules in global settings.json ignored, filed 2026-01-14, OPEN with 22+ upvotes).

### Pattern 2: Hook-First Deny (permissions.deny is Secondary)

**What:** permissions.deny rules in settings.json had a known security bug (issue #6699) where all deny rules were non-functional as of v1.0.93. The issue is marked CLOSED/COMPLETED meaning the team acknowledged it and assigned a developer, but exact fix version is unverified. The guard-frozen.sh PreToolUse hook is the ONLY reliable way to block writes to frozen files.

**When to use:** Add `permissions.deny` for defense-in-depth but treat the guard-frozen.sh hook as primary enforcement. Never remove the hook in favor of deny rules alone.

**Warning signs:** If deny rules were the sole mechanism and the bug recurs, prepare.py would be unprotected.

### Pattern 3: Broad Patterns for Headless Autonomous Operation

**What:** Relative path patterns like `Write(results.tsv)` fail in headless `claude -p` mode because the agent uses absolute paths internally and the pattern does not match. `Write(*)` and `Edit(*)` (or equivalently `Write` and `Edit`) are required.

**Confirmed by:** Phase 7 FINDINGS.md — "relative path patterns don't match absolute paths used internally by claude -p."

**Official docs confirm:** The official permissions docs show that `path` (bare, no leading `/`) matches "relative to current working directory" — in headless mode the CWD is the experiment directory, but the tool call uses the absolute path, causing mismatch.

### Recommended Project Structure (no change)
```
experiment-dir/
├── .claude/
│   ├── settings.json       # Broadened allow + deny rules (defense-in-depth)
│   └── hooks/
│       └── guard-frozen.sh # PRIMARY enforcement for frozen files
├── prepare.py              # FROZEN (hook + deny protect this)
├── train.py                # MUTABLE
├── results.tsv
└── run.log
```

### Anti-Patterns to Avoid

- **Narrow path patterns in settings.json:** `Write(results.tsv)` does not match absolute paths in headless mode. Use bare `Write` or `Write(*)`.
- **Removing --allowedTools from scripts:** settings.json allow rules are silently ignored in headless mode. Scripts MUST pass --allowedTools for autonomous operation.
- **Relying solely on permissions.deny for frozen files:** The deny bug (issue #6699) means the hook must remain primary. Never remove guard-frozen.sh.
- **Overly broad --allowedTools without hook protection:** Using `Write(*)` in --allowedTools is safe ONLY because guard-frozen.sh provides the deny layer. Both are needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Blocking writes to frozen files | Custom deny regex in settings.json | guard-frozen.sh PreToolUse hook | Deny rules had a known bug; hooks are reliable |
| Validating settings.json structure | Custom validator | uv run pytest tests/test_scaffold.py | Test assertions already cover this |
| Documenting headless permissions | New docs | Code comment in run-validation-test.sh | The script IS the documentation; comments are co-located |

## Common Pitfalls

### Pitfall 1: Believing settings.json allow Rules Work in Headless Mode

**What goes wrong:** Developer assumes that `permissions.allow` in `.claude/settings.json` governs `claude -p` tool access, removes `--allowedTools` from scripts. The autonomous loop runs and gets permission denials, halting execution.

**Why it happens:** The official docs describe the permission system as applying to all modes. In practice, project-level settings.json allow rules are ignored in headless mode (GitHub issue #18160, filed 2026-01-14, OPEN as of 2026-03-13).

**How to avoid:** Always pass `--allowedTools` in any script that invokes `claude -p`. Keep a prominent comment in the script explaining why.

**Warning signs:** `permission_denials` count > 0 in validation-run-output.json. `stop_reason=tool_use` (agent blocked, not finished). Zero experiments in results.tsv after a run.

### Pitfall 2: Using Relative Path Patterns

**What goes wrong:** `Write(results.tsv)`, `Edit(train.py)` — when claude -p runs, tools use absolute paths like `/home/user/experiment/train.py`. The relative pattern `train.py` or `./train.py` does not match.

**Why it happens:** The permission pattern matching resolves relative paths from CWD. In headless mode, the CWD path resolution during pattern matching does not correctly match the absolute path used in the tool call.

**How to avoid:** Use bare tool names (`Write`, `Edit`) or wildcard patterns (`Write(*)`, `Edit(*)`) for any file the agent needs to write. Use the hook to restrict what can be written to frozen files.

**Warning signs:** Same as Pitfall 1 — denials even for files that should be allowed.

### Pitfall 3: Removing guard-frozen.sh When Adding permissions.deny

**What goes wrong:** Developer adds `permissions.deny ["Edit(prepare.py)", "Write(prepare.py)"]` to settings.json and removes guard-frozen.sh as redundant. Deny rules fail silently (bug or version regression). prepare.py becomes writable.

**Why it happens:** permissions.deny had a confirmed bug (issue #6699). Even after a fix, regressions are possible. Defense-in-depth requires both layers.

**How to avoid:** Keep guard-frozen.sh. Add deny rules as supplementary, not replacement.

## Code Examples

### Current settings.json generated by scaffold.py (Phase 7 state)

```json
{
  "$schema": "https://docs.anthropic.com/en/docs/claude-code/settings",
  "permissions": {
    "allow": [
      "Bash(*)",
      "Edit(train.py)",
      "Write(train.py)",
      "Write(results.tsv)",
      "Write(run.log)",
      "Read",
      "Glob",
      "Grep"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/guard-frozen.sh"
          }
        ]
      }
    ]
  }
}
```

### Target settings.json for Phase 8 (with deny + broader allow)

```json
{
  "$schema": "https://docs.anthropic.com/en/docs/claude-code/settings",
  "permissions": {
    "allow": [
      "Bash(*)",
      "Edit(*)",
      "Write(*)",
      "Read",
      "Glob",
      "Grep"
    ],
    "deny": [
      "Edit(prepare.py)",
      "Write(prepare.py)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/guard-frozen.sh"
          }
        ]
      }
    ]
  }
}
```

Note: `Edit(*)` and `Write(*)` match the broad patterns already used in `--allowedTools`. The deny rules add a defense-in-depth layer. The hook remains primary.

### Official docs: deny rule takes precedence

From official permissions docs (code.claude.com/docs/en/permissions):
> Rules are evaluated in order: deny -> ask -> allow. The first matching rule wins, so deny rules always take precedence.
> If a tool is denied at any level, no other level can allow it.

This means adding `deny: ["Edit(prepare.py)"]` in settings.json will block even if `--allowedTools "Edit(*)"` is passed — but ONLY if the deny bug is fixed. The hook is still required.

### How --allowedTools interacts with settings.json deny

From official docs on settings precedence:
> Command line arguments: temporary session overrides
> Shared project settings (.claude/settings.json)

Deny rules from settings.json override allow rules from --allowedTools. If `deny: ["Edit(prepare.py)"]` is present and functional, passing `--allowedTools "Edit(*)"` will NOT allow editing prepare.py. This is the desired behavior.

### run-validation-test.sh claude invocation (current)

```bash
claude -p "Follow the CLAUDE.md protocol exactly. NEVER STOP until max-turns is reached." \
    --max-turns 50 \
    --max-budget-usd 4.00 \
    --output-format json \
    --allowedTools "Bash(*)" "Edit(*)" "Write(*)" "Read" "Glob" "Grep" \
    2>&1 | tee validation-run-output.json
```

Phase 8 changes: `--allowedTools` stays (settings.json allow is ignored in headless), but the list can be simplified to match the broader patterns in the target settings.json.

## State of the Art

| Old Approach (Phase 5) | Current Approach (Phase 7) | Phase 8 Target |
|------------------------|---------------------------|----------------|
| Narrow `Edit(train.py)`, `Write(train.py)` in settings.json | Broad `Bash(*)`, specific `Write(results.tsv)`, `Write(run.log)` | Broad `Edit(*)`, `Write(*)` matching --allowedTools exactly |
| No permissions.deny | No permissions.deny | Add `Edit(prepare.py)`, `Write(prepare.py)` deny rules |
| --allowedTools in scripts (Phase 4 only) | --allowedTools in run-validation-test.sh | --allowedTools stays; mismatch between settings.json and --allowedTools resolved |

**Deprecated approach:** Narrow path patterns in settings.json permissions.allow (they don't work in headless mode for absolute paths).

**Current known gap:** The scaffolded settings.json allows list (`Bash(*)`, `Edit(train.py)`, `Write(train.py)`, `Write(results.tsv)`, `Write(run.log)`) is narrower than what --allowedTools passes (`Bash(*)`, `Edit(*)`, `Write(*)`). The settings.json version is dead-weight (ignored in headless mode) and misleading to anyone reading it.

## Scope Decision: settings.json Allow in Headless Mode

A critical architectural decision for Phase 8: should Phase 8 attempt to make settings.json allow rules work in headless mode, or just work around the limitation?

**Answer: Work around it.** GitHub issue #18160 (open as of 2026-03-13, 22+ upvotes) confirms allow rules in settings.json are unreliable. There is no workaround at the settings.json level — the --allowedTools flag is the correct mechanism for headless mode. Phase 8 should:

1. Make settings.json allow rules match what --allowedTools passes (for documentation/consistency)
2. Add permissions.deny as defense-in-depth
3. Keep --allowedTools in all scripts that invoke claude -p
4. Add a prominent code comment in scripts explaining why --allowedTools is required

## Open Questions

1. **Is the permissions.deny bug (issue #6699) fixed?**
   - What we know: Issue was opened, marked CLOSED/COMPLETED, a developer (bogini) was assigned
   - What's unclear: The exact Claude Code version where the fix landed; whether the project is on a version post-fix
   - Recommendation: Add permissions.deny rules anyway (they're harmless if not working, beneficial if working). Guard-frozen.sh hook remains primary enforcement regardless.

2. **Should run-validation-test.sh remain in the repo after Phase 8?**
   - What we know: The script is a Phase 7 test harness, not a production artifact
   - What's unclear: Whether Phase 9/10 will use or replace it
   - Recommendation: Keep it as-is with updated comments. Phase 9 may scaffold its own test script.

3. **Should the REQUIREMENTS.md get new requirements for Phase 8?**
   - What we know: Phase 8 requirements are TBD; HOOK-06 says "requires no --allowedTools flags" but that's now known impossible for headless mode
   - What's unclear: Whether HOOK-06 should be updated to reflect the headless reality
   - Recommendation: Add PERM-01 through PERM-03 as new requirements for Phase 8. Update HOOK-06 to clarify it applies to interactive mode only.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (uv run pytest) |
| Config file | pyproject.toml (inferred — no pytest.ini found) |
| Quick run command | `uv run pytest tests/test_scaffold.py -q -x` |
| Full suite command | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` |

### Phase Requirements → Test Map

Phase 8 requirements are TBD, but the changes map to existing test infrastructure:

| Change | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| settings.json allow broadened | `Edit(*)` and `Write(*)` in allow | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude::test_scaffold_settings_permissions -x` | Yes (update needed) |
| settings.json deny added | `Edit(prepare.py)` and `Write(prepare.py)` in deny | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude -x` | Yes (new assertion needed) |
| run-validation-test.sh --allowedTools comment | Script has comment explaining headless limitation | manual | manual review | Yes |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_scaffold.py -q -x`
- **Per wave merge:** `uv run pytest tests/ -q --ignore=tests/test_e2e.py`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_scaffold.py` needs a new assertion: `data["permissions"]["deny"]` contains `"Edit(prepare.py)"` and `"Write(prepare.py)"` — covers the new deny rules
- [ ] `tests/test_scaffold.py` needs updated `test_scaffold_settings_permissions` expected list: `["Bash(*)", "Edit(*)", "Write(*)", "Read", "Glob", "Grep"]` — covers the broadened allow rules

No new test files needed. Existing `TestScaffoldDotClaude` class covers all scaffold settings assertions.

## Sources

### Primary (HIGH confidence)
- [code.claude.com/docs/en/permissions](https://code.claude.com/docs/en/permissions) — Official permissions docs: allow/deny syntax, precedence rules, settings hierarchy, headless behavior
- Phase 7 FINDINGS.md (`.planning/phases/07-e2e-validation-test/FINDINGS.md`) — Empirical evidence from actual validation runs: 8 denials with settings.json only, 0 after --allowedTools; relative path mismatch documented

### Secondary (MEDIUM confidence)
- [GitHub issue #6699](https://github.com/anthropics/claude-code/issues/6699) — deny permissions bug: CLOSED/COMPLETED, but exact fix version unverified
- [GitHub issue #18160](https://github.com/anthropics/claude-code/issues/18160) — allow permissions in settings.json ignored (OPEN, 22+ upvotes, filed 2026-01-14)

### Tertiary (LOW confidence)
- [eesel.ai Claude Code permissions guide](https://www.eesel.ai/blog/claude-code-permissions) — Community guide noting deny rules frequently ignored (corroborates issue #6699)

## Metadata

**Confidence breakdown:**
- Current settings.json state: HIGH — read directly from scaffold.py source
- Headless allow limitation: HIGH — empirical evidence from Phase 7, corroborated by open GitHub issue
- Deny rules bug status: MEDIUM — issue closed but fix version unverified; hook remains primary
- Architecture for Phase 8: HIGH — clear from evidence, no ambiguity

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (permissions bugs are active work; check GitHub issues for updates)
