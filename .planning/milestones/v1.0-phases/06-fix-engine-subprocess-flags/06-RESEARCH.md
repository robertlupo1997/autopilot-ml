# Phase 6: Fix Engine Subprocess Flags - Research

**Researched:** 2026-03-19
**Domain:** Claude CLI subprocess invocation, Python subprocess module
**Confidence:** HIGH

## Summary

Phase 6 fixes two invalid flags in `engine.py` line 122-130 that prevent ALL experiments from running. The `_run_one_experiment` method constructs a `claude -p` command with two flags that do not exist in the Claude CLI:

1. `--append-system-prompt-file` (line 129) -- Does not exist. The valid flag is `--append-system-prompt` which takes an inline string, not a file path.
2. `--max-turns` (line 127) -- Does not exist in the Claude CLI at all. There is no equivalent flag for limiting conversation turns.

These are P0 blockers: every subprocess invocation crashes immediately because the CLI rejects unknown flags. The fix is straightforward -- read CLAUDE.md content inline for `--append-system-prompt`, and remove `--max-turns` entirely (per-experiment budget control is already handled by `--max-budget-usd` which IS valid).

**Primary recommendation:** Replace `--append-system-prompt-file` with `--append-system-prompt` passing file content as a string; remove `--max-turns` entirely; update tests to verify the corrected command construction.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CORE-02 | Agent executes keep/revert experiment loop | Fixing subprocess flags allows the loop to actually run without immediate crash |
| CORE-03 | Protocol prompt system injects CLAUDE.md templates into agent context | `--append-system-prompt` with inline content replaces broken `--append-system-prompt-file` |
| INTL-07 | Experiment time/cost budget with per-experiment timeout and session budget | `--max-budget-usd` already works; removing invalid `--max-turns` eliminates the crash |
| GUARD-03 | Crash recovery saves state before each experiment so sessions can resume | Checkpoint save already works; fixing flags means experiments run long enough to checkpoint |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| subprocess (stdlib) | Python 3.12 | Spawn claude CLI processes | Already in use, no change needed |
| pathlib (stdlib) | Python 3.12 | Read CLAUDE.md file content | Already in use via Path.read_text() |

### Supporting
No new dependencies needed. This is a flag-fix-only change.

## Architecture Patterns

### Current Command Construction (BROKEN)
```python
# engine.py lines 122-130 -- TWO invalid flags
cmd = [
    "claude",
    "-p", prompt,
    "--output-format", "json",
    "--dangerously-skip-permissions",
    "--max-turns", str(self.config.max_turns_per_experiment),      # INVALID
    "--max-budget-usd", str(self.config.per_experiment_budget_usd),
    "--append-system-prompt-file", "CLAUDE.md",                     # INVALID
]
```

### Corrected Command Construction
```python
# Read CLAUDE.md content inline
claude_md_path = self.experiment_dir / "CLAUDE.md"
system_prompt_content = claude_md_path.read_text() if claude_md_path.exists() else ""

cmd = [
    "claude",
    "-p", prompt,
    "--output-format", "json",
    "--dangerously-skip-permissions",
    "--max-budget-usd", str(self.config.per_experiment_budget_usd),
]

if system_prompt_content:
    cmd.extend(["--append-system-prompt", system_prompt_content])
```

### Pattern: CLAUDE.md Content Loading
The CLAUDE.md file is already scaffolded into the experiment directory by `scaffold.py` (line 110). The engine runs with `cwd=str(self.experiment_dir)`, so the file is always at `self.experiment_dir / "CLAUDE.md"`. Reading it inline is safe and deterministic.

### Pattern: Budget Control Without --max-turns
`--max-turns` has no replacement in the CLI. Budget control is already adequately handled by:
- `--max-budget-usd` (per-experiment dollar cap -- already in the command)
- `per_experiment_timeout_sec` (subprocess timeout -- already enforced via `subprocess.run(timeout=...)`)
- `budget_experiments` (total experiment count -- enforced by `ResourceGuardrails.should_stop()`)

The `max_turns_per_experiment` config field becomes unused by the engine. It should be kept in Config for potential future use (the CLI may add turn limits later) but not passed to the subprocess.

### Anti-Patterns to Avoid
- **Shelling out to read files:** Do not use `subprocess` to cat/read CLAUDE.md. Use `Path.read_text()`.
- **Truncating CLAUDE.md content:** The `--append-system-prompt` flag accepts arbitrarily long strings. Do not truncate.
- **Removing max_turns_per_experiment from Config:** Keep the field for forward compatibility. Just stop passing it as a CLI flag.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reading CLAUDE.md | Custom file loader | `Path.read_text()` | One line, already used throughout codebase |
| Turn limiting | Custom turn counter | `--max-budget-usd` | Dollar cap naturally limits turns; no CLI flag exists for turns |

## Common Pitfalls

### Pitfall 1: Argument Length Limits
**What goes wrong:** CLAUDE.md content passed as a command-line argument could exceed OS argument length limits (ARG_MAX ~2MB on Linux).
**Why it happens:** Rendered CLAUDE.md templates can be long, especially with domain rules.
**How to avoid:** This is not a real risk for mlforge -- CLAUDE.md files are typically 2-5KB. ARG_MAX on Linux is ~2MB. No mitigation needed.
**Warning signs:** If someone adds very large templates (>100KB), the subprocess call would fail with E2BIG.

### Pitfall 2: Missing CLAUDE.md File
**What goes wrong:** If CLAUDE.md is somehow not present, `Path.read_text()` raises FileNotFoundError.
**Why it happens:** Could happen on resume if experiment dir was partially cleaned.
**How to avoid:** Guard with `if claude_md_path.exists()` before reading. Only add `--append-system-prompt` flag if content is non-empty.

### Pitfall 3: Test Mocking After Fix
**What goes wrong:** Existing tests mock `subprocess.run` and assert on command structure. After changing flags, tests that check for `--max-turns` or `--append-system-prompt-file` will need updating.
**Why it happens:** Tests verify the exact command list structure.
**How to avoid:** Update test assertions to match new command structure. Add new test specifically verifying `--append-system-prompt` includes CLAUDE.md content.

### Pitfall 4: Expert Mode Custom CLAUDE.md
**What goes wrong:** Expert mode uses `config.custom_claude_md_path` to copy a custom CLAUDE.md during scaffold. The engine must still read from `self.experiment_dir / "CLAUDE.md"` regardless of source.
**Why it happens:** Custom CLAUDE.md is already copied to the experiment dir by scaffold.py (line 107).
**How to avoid:** Always read from experiment dir, never from config.custom_claude_md_path directly.

## Code Examples

### Fix 1: Replace Invalid Flags in _run_one_experiment
```python
# Source: claude --help output, verified 2026-03-19
def _run_one_experiment(self, oom_hint: bool = False) -> dict:
    prompt = self._build_prompt()
    if oom_hint:
        prompt = (
            "IMPORTANT: The previous attempt ran out of memory. "
            "Use smaller batch sizes or simpler models.\n\n" + prompt
        )

    # Read CLAUDE.md content for --append-system-prompt
    claude_md_path = self.experiment_dir / "CLAUDE.md"
    system_prompt = claude_md_path.read_text() if claude_md_path.exists() else ""

    cmd = [
        "claude",
        "-p", prompt,
        "--output-format", "json",
        "--dangerously-skip-permissions",
        "--max-budget-usd", str(self.config.per_experiment_budget_usd),
    ]

    if system_prompt:
        cmd.extend(["--append-system-prompt", system_prompt])

    if self.config.model is not None:
        cmd.extend(["--model", self.config.model])

    # ... rest unchanged
```

### Fix 2: Test That Verifies Corrected Flags
```python
def test_command_uses_append_system_prompt_not_file(self, tmp_path):
    """Verify --append-system-prompt with inline content, not --append-system-prompt-file."""
    from mlforge.engine import RunEngine

    _init_git(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("You are an ML agent. Follow protocol.")
    config = Config()
    state = SessionState()
    engine = RunEngine(tmp_path, config, state)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({
        "result": json.dumps({"metric_value": 0.9}),
        "total_cost_usd": 0.1,
    })

    with patch("subprocess.run", return_value=mock_result) as mock_sub:
        engine._run_one_experiment()
        cmd = mock_sub.call_args[0][0]
        assert "--append-system-prompt-file" not in cmd
        assert "--max-turns" not in cmd
        assert "--append-system-prompt" in cmd
        idx = cmd.index("--append-system-prompt")
        assert cmd[idx + 1] == "You are an ML agent. Follow protocol."
    engine.git.close()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `--append-system-prompt-file` (never existed) | `--append-system-prompt` (inline string) | N/A -- was always wrong | P0 fix, enables all experiments |
| `--max-turns` (never existed) | Remove entirely, rely on `--max-budget-usd` | N/A -- was always wrong | P0 fix, enables all experiments |

**Valid Claude CLI flags used by engine.py (verified 2026-03-19):**
- `-p` (print mode) -- valid
- `--output-format json` -- valid
- `--dangerously-skip-permissions` -- valid
- `--max-budget-usd` -- valid
- `--append-system-prompt` -- valid (inline string)
- `--model` -- valid

## Open Questions

1. **Should max_turns_per_experiment be removed from Config?**
   - What we know: The field has no current use after removing `--max-turns`
   - What's unclear: Whether Claude CLI will add a turn limit flag in the future
   - Recommendation: Keep the Config field but don't pass it to subprocess. Add a comment noting it's reserved for future CLI support.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml (assumed) |
| Quick run command | `python3 -m pytest tests/mlforge/test_engine.py -x -q` |
| Full suite command | `python3 -m pytest tests/mlforge/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-02 | Keep/revert loop runs without crash | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestRunLoop -x` | Yes |
| CORE-03 | CLAUDE.md content injected via --append-system-prompt | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestRunOneExperiment -x` | Yes (needs new test) |
| INTL-07 | --max-budget-usd passed correctly | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestRunOneExperiment -x` | Yes (needs new test) |
| GUARD-03 | Checkpoint saved before each experiment | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestRunLoop::test_saves_checkpoint -x` | Yes |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/mlforge/test_engine.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/mlforge/ -x -q`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
- [ ] New test: verify `--append-system-prompt` with inline CLAUDE.md content (not `--append-system-prompt-file`)
- [ ] New test: verify `--max-turns` is NOT in the command
- [ ] New test: verify command works when CLAUDE.md is missing (graceful degradation)
- [ ] Update existing tests that may assert on old flag structure

## Sources

### Primary (HIGH confidence)
- `claude --help` output (verified 2026-03-19) -- authoritative list of all CLI flags
- `src/mlforge/engine.py` lines 122-130 -- the exact broken code
- `src/mlforge/scaffold.py` lines 102-110 -- confirms CLAUDE.md is always in experiment dir
- `tests/mlforge/test_engine.py` -- 26 passing tests, shows current mock patterns

### Secondary (MEDIUM confidence)
- None needed -- this is a pure flag-name fix verified against the actual CLI

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, pure fix
- Architecture: HIGH - straightforward flag replacement with verified CLI output
- Pitfalls: HIGH - limited surface area, well-understood failure modes

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable -- CLI flags rarely change)
