# Phase 5: Hooks and Enhanced Scaffolding - Research

**Researched:** 2026-03-11
**Domain:** Claude Code hooks API, settings.json schema, CLAUDE.md rules system, Python scaffolding
**Confidence:** HIGH

---

## Summary

Phase 5 upgrades the scaffolded experiment directory from a minimal set of files (prepare.py, train.py, program.md, CLAUDE.md, .gitignore, pyproject.toml) to one that is fully Claude Code-aware. The additions are: `.claude/settings.json` (permissions + hooks), `.claude/hooks/guard-frozen.sh` (mutable zone enforcement), `.claude/rules/` (lean supplemental rules), and an improved CLAUDE.md. The user experience goal is `cd experiment-dir && claude` — no extra flags needed.

Phase 4's baseline test showed CLAUDE.md instructions alone were sufficient for frozen file compliance in the one run observed. This means hooks are a safety net, not the primary mechanism. Hook design should therefore be **non-disruptive**: log violations and warn Claude rather than hard-failing in a way that derails the autonomous loop. The one confirmed issue from Phase 4 that Phase 5 must address is the `stop_reason: tool_use` (mid-action interrupt) — hooks cannot fix this directly, but a cleaner CLAUDE.md with graceful shutdown guidance helps.

**Primary recommendation:** Generate `.claude/settings.json` with `permissions.allow` rules (replaces `--dangerously-skip-permissions` or manual `--allowedTools` flags), a lightweight `PreToolUse` shell hook that warns on writes to frozen files, and a revised CLAUDE.md under ~120 lines with the autonomous loop protocol.

---

## Standard Stack

### Core
| Library/Tool | Version | Purpose | Why Standard |
|---|---|---|---|
| Python `json` stdlib | any | Generate settings.json from scaffold | No dependency; settings.json is pure JSON |
| Python `pathlib` stdlib | any | Create `.claude/` and `.claude/hooks/` directories | Already used throughout scaffold.py |
| Python `textwrap.dedent` stdlib | any | Write hook shell scripts | Already used in scaffold.py for .gitignore |
| `jq` (system) | 1.6+ | Parse hook stdin JSON in shell scripts | Standard; pre-installed on most Linux/macOS |
| bash | any | Hook scripts | Only supported type for command hooks in practice |

### Supporting
| Library/Tool | Version | Purpose | When to Use |
|---|---|---|---|
| Python `stat` stdlib | any | Set executable bit on hook scripts after writing | Required; git doesn't auto-chmod shell scripts |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|---|---|---|
| Shell hook script | Python hook script | Python is heavier; shell + jq is standard hook pattern per official docs |
| `permissions.deny` | `PreToolUse` hook | deny rules are static patterns; hook can log + warn Claude with context |
| Lean CLAUDE.md + rules/ | Single monolithic CLAUDE.md | Rules split by concern; rules/ files load lazily (only when relevant path accessed) |

**Installation:**
```bash
# No new Python deps needed. System requirement: jq (for hook scripts).
# jq is typically pre-installed; add to pyproject.toml optional-deps if needed.
```

---

## Architecture Patterns

### Recommended Scaffolded Project Structure
```
experiment-{name}/
├── prepare.py                # FROZEN - copied from automl package
├── train.py                  # MUTABLE - agent edits this only
├── program.md                # domain context
├── CLAUDE.md                 # autonomous loop protocol (lean, ~100 lines)
├── .gitignore
├── pyproject.toml
├── {dataset}.csv
└── .claude/
    ├── settings.json         # permissions + hooks config
    └── hooks/
        └── guard-frozen.sh   # PreToolUse: warn on frozen file writes
```

No `.claude/rules/` directory is needed for v1. The CLAUDE.md is already short enough to stay single-file. Rules/ files load lazily by path glob — useful when an agent works across many directories. For an experiment dir with one mutable file, CLAUDE.md is sufficient.

### Pattern 1: settings.json permissions block

**What:** `permissions.allow` pre-approves all tools the agent legitimately needs, so `--dangerously-skip-permissions` is not required and no permission prompts interrupt the loop.

**When to use:** Always. This is the correct way to run headless Claude Code in v1.

**Example:**
```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash",
      "Edit(train.py)",
      "Write(train.py)",
      "Read",
      "Glob",
      "Grep"
    ]
  }
}
```

Source: https://code.claude.com/docs/en/settings (official docs, fetched 2026-03-11)

### Pattern 2: PreToolUse hook for frozen file protection

**What:** A shell script that fires before every `Edit` or `Write` tool call. It reads the `file_path` from JSON stdin and warns Claude (via `additionalContext`) if the target is `prepare.py`.

**When to use:** Mutable zone enforcement. Non-disruptive design: warn Claude rather than hard-deny, since CLAUDE.md instructions are the primary mechanism and Phase 4 showed they work.

**Configuration in settings.json:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/guard-frozen.sh",
            "timeout": 10,
            "statusMessage": "Checking mutable zone..."
          }
        ]
      }
    ]
  }
}
```

**The hook script `.claude/hooks/guard-frozen.sh`:**
```bash
#!/bin/bash
# Guard: warn Claude if it tries to edit a frozen file.
# Reads PreToolUse JSON from stdin. Exits 0 (allow) always,
# but injects additionalContext when a frozen file is targeted.
# Source: https://code.claude.com/docs/en/hooks (official docs)

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
BASENAME=$(basename "$FILE_PATH" 2>/dev/null)

FROZEN_FILES="prepare.py"

for frozen in $FROZEN_FILES; do
  if [ "$BASENAME" = "$frozen" ]; then
    jq -n '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: "prepare.py is FROZEN. Only train.py is mutable. Do not modify prepare.py."
      }
    }'
    exit 0
  fi
done

exit 0
```

**Design note:** Using `permissionDecision: "deny"` is the appropriate choice per Phase 4's recommendation: "design hooks to be non-disruptive... warn/log rather than hard-fail". A deny with a clear reason tells Claude what happened without stopping the session — Claude receives `permissionDecisionReason` as feedback and can correct course. Hard-failing with exit 2 would interrupt the loop more aggressively.

Source: https://code.claude.com/docs/en/hooks#pretooluse-decision-control

### Pattern 3: Permissions array — what to pre-approve

The goal is zero permission prompts during the autonomous loop. The agent's legitimate operations are:

| Operation | Permission Rule |
|---|---|
| Run train.py, git commands, grep | `"Bash"` |
| Edit train.py | `"Edit(train.py)"` |
| Write train.py | `"Write(train.py)"` |
| Read any file (program.md, results.tsv, run.log) | `"Read"` |
| Glob patterns | `"Glob"` |
| Grep in files | `"Grep"` |

**Do not allow `Write` or `Edit` without path restriction.** Restrict to `train.py` to reinforce the mutable zone at the permissions layer (defense in depth alongside the hook).

### Pattern 4: Lean CLAUDE.md design

**What:** The current CLAUDE.md template (~91 lines) is already good. Phase 5 improvements:
1. Add a graceful shutdown section (addresses Phase 4's `stop_reason: tool_use` issue)
2. Remove any redundancy with program.md (program.md owns dataset context)
3. Keep Rules section explicit: "prepare.py is FROZEN, train.py is MUTABLE"

**Graceful shutdown addition:**
```markdown
## Graceful Shutdown

When you approach your turn limit or are interrupted:
1. Finish writing any in-progress results.tsv row.
2. Run `git status` to confirm train.py state.
3. If in mid-experiment, run `git reset --hard HEAD` to restore a clean state.
4. Do NOT leave train.py in a partially-edited state.
```

### Anti-Patterns to Avoid

- **Writing hook scripts with hardcoded absolute paths:** use `$CLAUDE_PROJECT_DIR` env var. Hook scripts run from variable cwd.
- **Using `exit 2` for frozen file violations:** this is a blocking error that interrupts the loop. Use `permissionDecision: "deny"` with a clear reason — Claude receives it as feedback, not a crash.
- **Putting `settings.json` in project root:** it must be at `.claude/settings.json` (project scope) or `~/.claude/settings.json` (user scope). Root-level `settings.json` is ignored.
- **Forgetting to chmod +x the hook script:** Python `Path.write_text()` does not set executable bit. Must follow with `os.chmod(path, 0o755)` or `path.chmod(0o755)`.
- **Relying solely on hooks for security:** hooks can be disabled. CLAUDE.md instructions + permissions.deny is defense in depth.
- **Using the old `allowedTools` key:** the current schema uses `permissions.allow` (array). The old `allowedTools` key is not in the official schema as of 2026.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| JSON schema validation | custom validator | let Claude Code parse settings.json | Claude Code ignores unknown keys; valid JSON is sufficient |
| Hook input parsing | custom stdin reader | `jq` in shell scripts | jq is the standard; Claude Code docs use it in all examples |
| Permission prompts suppression | `--dangerously-skip-permissions` flag | `permissions.allow` in settings.json | Scoped allow is safer; `--dangerously-skip-permissions` suppresses everything |
| Frozen file list management | runtime config | hardcode `prepare.py` in hook script | Only one frozen file in v1; over-engineering a config system adds complexity |

---

## Common Pitfalls

### Pitfall 1: Hook script not executable
**What goes wrong:** Claude Code silently skips hook or logs a non-blocking error. The hook never fires.
**Why it happens:** `Path.write_text()` creates files with 0o644 (no execute bit).
**How to avoid:** After writing `.claude/hooks/guard-frozen.sh`, call `hook_path.chmod(0o755)`.
**Warning signs:** Hook listed in settings.json but never fires; no "Checking mutable zone..." status message.

### Pitfall 2: jq not available in hook environment
**What goes wrong:** Hook script fails silently with non-blocking error (exit code ≠ 0, ≠ 2).
**Why it happens:** Some minimal container environments don't have jq.
**How to avoid:** Use `python3 -c "import json,sys; ..."` as a fallback parser if jq is unavailable, or add a jq availability check at the top of the hook.
**Warning signs:** Hook listed but frozen files are editable without any warning.

### Pitfall 3: settings.json created in wrong location
**What goes wrong:** Claude Code doesn't load settings from a `settings.json` in the project root.
**Why it happens:** Settings must be at `.claude/settings.json` (not `settings.json`).
**How to avoid:** scaffold creates `out / ".claude" / "settings.json"`, not `out / "settings.json"`.
**Warning signs:** `/status` in Claude Code shows no project settings loaded.

### Pitfall 4: Hook fires mid-loop and hard-stops the session
**What goes wrong:** An overly aggressive hook (exit 2 on frozen file write) surfaces as an error that confuses the agent or halts the session.
**Why it happens:** Phase 4 confirmed the loop works fine with CLAUDE.md alone. A hard-failing hook adds disruption without benefit.
**How to avoid:** Use `permissionDecision: "deny"` with a clear reason message. Claude receives the reason and can continue.
**Warning signs:** Agent stops iterating after a hook fires; stop_reason shows hook-related interrupt.

### Pitfall 5: permissions.allow too broad (allow "Write" without path)
**What goes wrong:** Agent can write any file, defeating the purpose of the mutable zone.
**Why it happens:** `"Write"` with no path qualifier allows writes to any file.
**How to avoid:** Use `"Write(train.py)"` and `"Edit(train.py)"` to restrict to the mutable file.
**Warning signs:** Hook needed to block frozen file writes — if permissions are scoped correctly, the hook is a last resort, not first line of defense.

### Pitfall 6: .claude directory needs its own .gitignore handling
**What goes wrong:** `.claude/settings.json` (project-shared) is fine to commit, but `.claude/settings.local.json` (personal overrides) should be gitignored.
**Why it happens:** Claude Code's hierarchy distinguishes settings.json (shareable) from settings.local.json (personal).
**How to avoid:** The experiment's `.gitignore` should include `.claude/settings.local.json`. The scaffolded `.gitignore` should add this line.

---

## Code Examples

Verified patterns from official sources:

### PreToolUse input schema (Bash tool)
```json
{
  "session_id": "abc123",
  "transcript_path": "/home/user/.claude/projects/.../transcript.jsonl",
  "cwd": "/home/user/my-project",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "uv run python train.py > run.log 2>&1"
  }
}
```
Source: https://code.claude.com/docs/en/hooks#pretooluse-input

### PreToolUse input schema (Edit/Write tools)
```json
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/abs/path/to/prepare.py",
    "old_string": "...",
    "new_string": "..."
  }
}
```
Source: https://code.claude.com/docs/en/hooks#edit

### PreToolUse deny response (guard-frozen.sh output)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "prepare.py is FROZEN. Only train.py is mutable."
  }
}
```
Source: https://code.claude.com/docs/en/hooks#pretooluse-decision-control

### Complete settings.json for scaffolded project
```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash",
      "Edit(train.py)",
      "Write(train.py)",
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
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/guard-frozen.sh",
            "timeout": 10,
            "statusMessage": "Checking mutable zone..."
          }
        ]
      }
    ]
  }
}
```

### scaffold.py additions (Python generation code)
```python
import json
import os

def _dot_claude_settings(out: Path) -> None:
    """Write .claude/settings.json and .claude/hooks/guard-frozen.sh."""
    dot_claude = out / ".claude"
    dot_claude.mkdir(exist_ok=True)
    hooks_dir = dot_claude / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    settings = {
        "$schema": "https://json.schemastore.org/claude-code-settings.json",
        "permissions": {
            "allow": [
                "Bash",
                "Edit(train.py)",
                "Write(train.py)",
                "Read",
                "Glob",
                "Grep",
            ]
        },
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": '"$CLAUDE_PROJECT_DIR"/.claude/hooks/guard-frozen.sh',
                            "timeout": 10,
                            "statusMessage": "Checking mutable zone...",
                        }
                    ],
                }
            ]
        },
    }
    (dot_claude / "settings.json").write_text(
        json.dumps(settings, indent=2) + "\n"
    )

    hook_script = _guard_frozen_hook_content()
    hook_path = hooks_dir / "guard-frozen.sh"
    hook_path.write_text(hook_script)
    hook_path.chmod(0o755)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `--dangerously-skip-permissions` flag | `permissions.allow` in settings.json | Recent (2025-2026) | Scoped allow is safer; avoids bypassing all permission checks |
| `allowedTools` key | `permissions.allow` array | Recent (2025-2026) | Old key not in official schema; use `permissions` object |
| Top-level `decision`/`reason` for PreToolUse | `hookSpecificOutput.permissionDecision` | Mid-2025 | Old format deprecated; still maps to new format but use new format |

**Deprecated/outdated:**
- `allowedTools` at top level of settings.json: replaced by `permissions.allow`
- PreToolUse `decision: "approve"` / `decision: "block"`: replaced by `hookSpecificOutput.permissionDecision: "allow"` / `"deny"`. Old values still mapped but use new format.

---

## Open Questions

1. **Does `permissions.allow: ["Edit(train.py)"]` match absolute paths?**
   - What we know: The permission pattern `Edit(train.py)` uses the same syntax as `Edit(./src/**)`. Docs show both relative and absolute path examples.
   - What's unclear: Whether the matcher applies to the basename or the full absolute path. Agent uses absolute paths in tool calls (e.g. `/home/user/experiment/train.py`).
   - Recommendation: Use `"Edit(train.py)"` (basename match) in settings.json. The hook provides defense in depth regardless. In testing, verify by attempting `Edit(prepare.py)` — it should prompt or deny.

2. **Will the venv warning in run.log be suppressed by Phase 5?**
   - What we know: Phase 4 saw `VIRTUAL_ENV does not match project environment path` warning on every `uv` invocation. Cosmetic only.
   - What's unclear: Whether `uv run --active python train.py` suppresses it, or if setting `VIRTUAL_ENV` in `settings.json` `env` block would help.
   - Recommendation: Add `"env": {}` section to settings.json with `UV_PROJECT_ENVIRONMENT` if needed. Test with `uv run --active` in train.py first (simplest fix).

3. **Does the hook script need `jq` or can it use Python?**
   - What we know: jq is standard in all official examples. Python 3 is guaranteed available (it's in pyproject.toml).
   - What's unclear: jq availability in all target environments (WSL, minimal containers).
   - Recommendation: Write hook in Python (`python3 -c "..."`) for portability, or check for jq with `command -v jq` and fall back to Python.

---

## Validation Architecture

Config: `nyquist_validation: true` — validation architecture section is required.

### Test Framework
| Property | Value |
|---|---|
| Framework | pytest (already in use, 111 tests passing) |
| Config file | `pyproject.toml` (project root has no pytest.ini; config likely in pyproject.toml) |
| Quick run command | `uv run pytest tests/test_scaffold.py -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements → Test Map

Phase 5 has no explicit requirement IDs, but the deliverables map to testable behaviors:

| Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|
| scaffold creates `.claude/settings.json` | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude -x` | ❌ Wave 0 |
| `.claude/settings.json` contains `permissions.allow` with correct rules | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldSettings -x` | ❌ Wave 0 |
| `.claude/hooks/guard-frozen.sh` exists and is executable | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldHookScript -x` | ❌ Wave 0 |
| hook script outputs deny JSON for `prepare.py` writes | unit | `uv run pytest tests/test_scaffold.py::TestGuardFrozenHook -x` | ❌ Wave 0 |
| hook script allows writes to `train.py` | unit | same test class | ❌ Wave 0 |
| CLAUDE.md includes graceful shutdown section | unit | `uv run pytest tests/test_templates.py::TestClaudeMd -x` | ❌ Wave 0 |
| scaffold creates 9 files (was 7, now +.claude/settings.json +hook) | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldCreatesAllFiles -x` | existing — needs update |
| `.gitignore` includes `.claude/settings.local.json` | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldGitignore -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_scaffold.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_scaffold.py::TestScaffoldDotClaude` — new test class for `.claude/` dir creation
- [ ] `tests/test_scaffold.py::TestScaffoldSettings` — assert settings.json content
- [ ] `tests/test_scaffold.py::TestScaffoldHookScript` — assert hook file exists + executable
- [ ] `tests/test_scaffold.py::TestGuardFrozenHook` — unit test the hook shell script behavior (invoke it directly with mock stdin JSON)
- [ ] `tests/test_templates.py::TestClaudeMd` — assert CLAUDE.md contains graceful shutdown section
- [ ] Update `TestScaffoldCreatesAllFiles` — file count increases from 7 to 9 (add `.claude/settings.json` and `.claude/hooks/guard-frozen.sh`)
- [ ] Update `_gitignore_content()` — add `.claude/settings.local.json` line

---

## Sources

### Primary (HIGH confidence)
- https://code.claude.com/docs/en/hooks — Full hooks reference, PreToolUse input/output schema, exit code behavior, guard-frozen example pattern. Fetched 2026-03-11.
- https://code.claude.com/docs/en/settings — Complete settings.json schema, permissions.allow/deny syntax, hooks configuration, settings hierarchy. Fetched 2026-03-11.
- `/home/tlupo/AutoML/.planning/phases/04-e2e-baseline-test/FINDINGS.md` — Phase 4 baseline test results: frozen file compliance confirmed, `stop_reason: tool_use` documented, hook design recommendations stated explicitly.
- `/home/tlupo/AutoML/src/automl/scaffold.py` — Current scaffold implementation reviewed; extension points identified.
- `/home/tlupo/AutoML/.planning/research/claude-code-capabilities-research.md` — Prior research on hooks, CLAUDE.md patterns, allowedTools.

### Secondary (MEDIUM confidence)
- Web search results confirming `permissions.allow` as current format (multiple sources agree), and that `allowedTools` is the deprecated form.

### Tertiary (LOW confidence)
- None — all critical claims verified against official docs.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only (json, pathlib, stat); verified against official settings schema
- Hook API / settings.json schema: HIGH — directly fetched from code.claude.com/docs official docs
- Architecture / file structure: HIGH — derived from official docs + existing scaffold code
- Hook script behavior: HIGH — PreToolUse deny pattern verified in official docs
- Permissions.allow path matching (basename vs absolute): LOW — behavior not explicitly documented for basename patterns; flagged as open question

**Research date:** 2026-03-11
**Valid until:** 2026-04-10 (stable API; settings schema version changes infrequently)
