# Phase 1: Core Engine + Plugin Infrastructure - Research

**Researched:** 2026-03-19
**Domain:** Python application architecture -- state management, git operations, config, plugin protocols, template rendering, hook engine
**Confidence:** HIGH

## Summary

Phase 1 builds the foundational engine for mlforge: seven requirements spanning state tracking (CORE-04), git-based state management (CORE-10), checkpoint/resume (CORE-05), config system (CORE-06), protocol templates (CORE-03), experiment journal (CORE-08), and hook engine (CORE-07). This is a fresh rewrite -- no code carried from v1-v3, though old patterns serve as reference.

The standard stack uses GitPython (replacing the old subprocess-based git_ops.py), Jinja2 (replacing the old str.format()-based templates), tomllib (stdlib, for TOML config), and typing.Protocol (for the plugin interface). All are mature, well-documented libraries. The old codebase's patterns for checkpoint atomicity (write-then-rename), LoopState dataclass, and hook-based frozen file enforcement are architecturally sound and should be reimplemented with the upgraded stack.

**Primary recommendation:** Build six focused modules -- `state.py`, `git_ops.py`, `checkpoint.py`, `config.py`, `plugins.py`, `templates.py`, `hooks.py` -- with clean interfaces, JSON state persistence, GitPython for all git operations, Jinja2 for template rendering, and a typing.Protocol-based plugin contract that the planner can validate with a mock plugin.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CORE-03 | Protocol prompt system injects domain-specific CLAUDE.md templates into agent context at session start | Jinja2 Environment + PackageLoader for template rendering; plugin provides template vars |
| CORE-04 | State tracking persists experiment progress (current best, budget remaining, experiment count) across context resets | JSON serialization of a dataclass-based SessionState; atomic write-then-rename pattern |
| CORE-05 | Checkpoint/resume allows crashed sessions to restart from last successful experiment | Checkpoint module saves state + metadata to checkpoint.json; schema versioning for forward compat |
| CORE-06 | Config system (mlforge.config.toml) controls domain, budget, mutable zones, metric, and plugin settings | tomllib (stdlib) for reading; dataclass-based Config with defaults and validation |
| CORE-07 | Hook engine (PreToolUse/PostToolUse) intercepts Claude Code tool calls to enforce frozen file zones | Claude Code hooks API: settings.json with matcher regex, bash/python scripts reading stdin JSON, deny/allow output |
| CORE-08 | Experiment journal accumulates structured knowledge (hypothesis, result, diff, metric delta) that survives context resets | Append-only JSON Lines file (.jsonl) for machine-readable journal; Jinja2-rendered markdown view |
| CORE-10 | Git-based state management: branch per run, commit per kept experiment, reset on revert, tag best model | GitPython 3.1.46: Repo, create_head, index.add/commit, create_tag, head.reset |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| GitPython | 3.1.46 | Programmatic git operations (branch, commit, tag, reset) | Mature, high-level Python API for git; replaces subprocess calls with proper object model |
| Jinja2 | 3.1.x | CLAUDE.md protocol template rendering | Industry standard for Python templating; supports inheritance, filters, conditionals |
| tomllib | stdlib (3.11+) | Read mlforge.config.toml configuration | Zero-dependency; built into Python 3.11+ which is already the project minimum |
| typing.Protocol | stdlib | Plugin interface contract (structural subtyping) | No ABC inheritance needed; plugins just implement the right methods |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tomli-w | 1.1.0 | Write TOML files (config generation) | Only if config writing is needed; tomllib is read-only |
| dataclasses | stdlib | State, config, and checkpoint data structures | All structured data within the engine |
| pathlib | stdlib | File path operations | All file I/O throughout the engine |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| GitPython | subprocess (old approach) | subprocess is simpler but loses type safety, error handling, and object model |
| Jinja2 | str.format() (old approach) | str.format() can't do conditionals, loops, or template inheritance needed for multi-domain protocols |
| TOML | YAML/JSON config | TOML is the Python packaging standard (pyproject.toml); familiar to Python developers |
| typing.Protocol | ABC | ABC requires explicit inheritance; Protocol allows structural subtyping (any class with right methods works) |

**Installation:**
```bash
pip install gitpython jinja2
# tomllib and typing.Protocol are stdlib (Python 3.11+)
# tomli-w only if writing TOML is needed
```

## Architecture Patterns

### Recommended Project Structure
```
src/mlforge/
    __init__.py
    state.py           # SessionState dataclass + JSON persistence (CORE-04)
    git_ops.py          # GitManager wrapping GitPython (CORE-10)
    checkpoint.py       # Save/load checkpoint.json with schema versioning (CORE-05)
    config.py           # Load mlforge.config.toml, Config dataclass (CORE-06)
    plugins.py          # DomainPlugin Protocol + registry (CORE-03 partial)
    templates.py        # Jinja2 Environment + rendering helpers (CORE-03 partial)
    hooks.py            # Hook generation for .claude/settings.json (CORE-07)
    journal.py          # Experiment journal JSONL append + markdown view (CORE-08)
    templates/          # Jinja2 template files
        base_claude.md.j2       # Base CLAUDE.md template with blocks
        base_experiments.md.j2  # Base experiments.md journal template
```

### Pattern 1: SessionState as Dataclass with JSON Persistence
**What:** A frozen-field dataclass representing experiment session state, serialized to JSON via dataclasses.asdict().
**When to use:** Any state that must survive context resets (experiment count, best metric, budget remaining).
**Example:**
```python
# Source: Evolved from old LoopState pattern in loop_helpers.py
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path

@dataclass
class SessionState:
    """Mutable state tracked across the experiment session."""
    experiment_count: int = 0
    best_metric: float | None = None
    best_commit: str | None = None
    budget_remaining: float = 0.0
    consecutive_reverts: int = 0
    total_keeps: int = 0
    total_reverts: int = 0
    run_id: str = ""

    def to_json(self, path: Path) -> None:
        """Atomic write: tmp file then rename."""
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2) + "\n")
        tmp.rename(path)

    @classmethod
    def from_json(cls, path: Path) -> "SessionState":
        data = json.loads(path.read_text())
        # Forward-compat: ignore unknown fields
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})
```

### Pattern 2: GitPython GitManager
**What:** A wrapper class around GitPython's Repo providing experiment-specific git operations.
**When to use:** All git operations -- branch creation, commits, reverts, tagging.
**Example:**
```python
# Source: GitPython 3.1.46 official tutorial
from git import Repo, Actor

class GitManager:
    def __init__(self, repo_path: str = "."):
        self.repo = Repo(repo_path)

    def create_run_branch(self, run_id: str) -> str:
        branch_name = f"mlforge/run-{run_id}"
        branch = self.repo.create_head(branch_name)
        branch.checkout()
        return branch_name

    def commit_experiment(self, message: str, files: list[str]) -> str:
        self.repo.index.add(files)
        commit = self.repo.index.commit(message)
        return commit.hexsha[:8]

    def revert_to_last_commit(self) -> None:
        self.repo.head.reset(index=True, working_tree=True)

    def tag_best(self, tag_name: str, message: str = "") -> None:
        self.repo.create_tag(tag_name, message=message)
```

### Pattern 3: typing.Protocol Plugin Contract
**What:** A Protocol class defining the interface that domain plugins must implement. No inheritance required.
**When to use:** Defining what a domain plugin must provide (scaffold files, template vars, frozen files list).
**Example:**
```python
# Source: PEP 544, typing.python.org/en/latest/reference/protocols.html
from typing import Protocol, runtime_checkable

@runtime_checkable
class DomainPlugin(Protocol):
    """Contract for domain-specific ML plugins."""
    name: str
    frozen_files: list[str]

    def scaffold(self, target_dir: Path, config: "Config") -> None:
        """Create domain-specific files in the experiment directory."""
        ...

    def template_context(self, config: "Config") -> dict:
        """Return variables for Jinja2 CLAUDE.md template rendering."""
        ...

    def validate_config(self, config: "Config") -> list[str]:
        """Return list of config validation errors (empty = valid)."""
        ...
```

### Pattern 4: Jinja2 Template Rendering with PackageLoader
**What:** Use Jinja2 Environment with PackageLoader to load templates from the installed package.
**When to use:** Rendering CLAUDE.md, experiments.md, and other protocol files.
**Example:**
```python
# Source: Jinja2 3.1.x official docs
from jinja2 import Environment, PackageLoader

env = Environment(
    loader=PackageLoader("mlforge", "templates"),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

def render_claude_md(plugin: DomainPlugin, config: Config) -> str:
    template = env.get_template("base_claude.md.j2")
    context = plugin.template_context(config)
    return template.render(**context)
```

### Pattern 5: Hook Generation
**What:** Generate .claude/settings.json with PreToolUse hooks that deny writes to frozen files.
**When to use:** During scaffold -- create the hook infrastructure in the experiment directory.
**Example:**
```python
# Source: Claude Code hooks reference (code.claude.com/docs/en/hooks)
import json

def generate_hook_settings(frozen_files: list[str]) -> dict:
    """Generate .claude/settings.json with frozen file guards."""
    return {
        "permissions": {
            "allow": ["Bash(*)", "Edit(*)", "Write(*)", "Read", "Glob", "Grep"],
            "deny": [
                f"{tool}({f})" for f in frozen_files
                for tool in ("Edit", "Write")
            ],
        },
        "hooks": {
            "PreToolUse": [{
                "matcher": "Edit|Write",
                "hooks": [{
                    "type": "command",
                    "command": '"$CLAUDE_PROJECT_DIR"/.claude/hooks/guard-frozen.sh',
                }],
            }],
        },
    }
```

### Anti-Patterns to Avoid
- **Monolithic state file:** Don't put session state, journal, and config in one file. Keep them separate: state.json (machine state), experiments.jsonl (journal), mlforge.config.toml (config).
- **Mutable global state:** Don't use module-level mutable state. Pass SessionState explicitly through function arguments.
- **String concatenation for templates:** Don't build CLAUDE.md with f-strings or str.format(). Use Jinja2 for any template with conditionals or domain-specific sections.
- **subprocess for git:** Don't shell out to git when GitPython provides a proper API. The old code used subprocess; the new code should use GitPython throughout.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Git operations | subprocess calls to git CLI | GitPython Repo API | Error handling, object model, no shell escaping issues |
| Template rendering | str.format() or f-string concatenation | Jinja2 Environment | Need conditionals, loops, inheritance for multi-domain templates |
| TOML parsing | Custom config parser | tomllib (stdlib) | Zero-dependency, handles all TOML edge cases |
| Atomic file writes | Raw open/write | Write-then-rename pattern (already in old checkpoint.py) | Prevents corrupt state on crash |
| Plugin interface | ABC or manual duck typing | typing.Protocol with @runtime_checkable | Static type checking + runtime isinstance() checks |
| JSON schema validation | Manual field checking | dataclass + fields() filtering | Forward-compatible deserialization (ignore unknown fields) |

**Key insight:** The old codebase already solved atomic writes and forward-compatible state deserialization correctly. Carry the patterns (write-then-rename, fields() filtering), not the code.

## Common Pitfalls

### Pitfall 1: GitPython Repo Memory Leaks
**What goes wrong:** GitPython's Repo objects can leak file handles and subprocesses if not properly closed.
**Why it happens:** Repo opens .git/index and spawns git processes that persist.
**How to avoid:** Use `repo.close()` or context manager. In long-running sessions, close and re-open Repo objects.
**Warning signs:** "too many open files" errors during long experiment sessions.

### Pitfall 2: Checkpoint Corruption on Crash
**What goes wrong:** Writing state JSON directly to checkpoint.json can leave a partial file if the process crashes mid-write.
**Why it happens:** File writes are not atomic on most filesystems.
**How to avoid:** Always use write-then-rename: write to .tmp file first, then os.rename() (atomic on same filesystem).
**Warning signs:** Corrupt JSON on resume after crash.

### Pitfall 3: GitPython Detached HEAD After Operations
**What goes wrong:** After certain operations (tag checkout, reset), the repo can end up in detached HEAD state.
**Why it happens:** GitPython's head.reset() or checkout operations may detach HEAD.
**How to avoid:** Always work with named branches. After reset, verify `repo.head.is_detached` is False.
**Warning signs:** Subsequent commits create orphan commits not on any branch.

### Pitfall 4: TOML Config Read-Only Limitation
**What goes wrong:** Attempting to write config with tomllib fails -- it's read-only.
**Why it happens:** tomllib (stdlib) only reads TOML. Writing requires tomli-w or tomlkit.
**How to avoid:** Use tomllib for reading config. If config generation is needed (e.g., `mlforge init`), add tomli-w as a dependency.
**Warning signs:** ImportError or AttributeError when trying tomllib.dumps().

### Pitfall 5: Protocol Runtime Checks Incomplete
**What goes wrong:** @runtime_checkable only checks method names exist, not signatures.
**Why it happens:** isinstance(plugin, DomainPlugin) verifies method presence but not argument types or return types.
**How to avoid:** Add explicit validation in the plugin registration function that calls each method with test data, or rely on mypy for static checking.
**Warning signs:** Plugin passes isinstance() check but fails at runtime with wrong argument count.

### Pitfall 6: Hook Script Not Executable
**What goes wrong:** Guard hook script created but not marked executable, so Claude Code skips it silently.
**Why it happens:** File.write_text() doesn't set permissions.
**How to avoid:** Always chmod 0o755 after writing hook scripts. The old scaffold.py does this correctly.
**Warning signs:** Frozen files get modified despite hook being configured.

## Code Examples

### TOML Config Loading
```python
# Source: Python 3.11+ stdlib tomllib docs
import tomllib
from pathlib import Path
from dataclasses import dataclass, field

CONFIG_FILENAME = "mlforge.config.toml"

@dataclass
class Config:
    domain: str = "tabular"
    metric: str = "accuracy"
    direction: str = "maximize"
    budget_minutes: int = 60
    budget_experiments: int = 50
    frozen_files: list[str] = field(default_factory=lambda: ["prepare.py"])
    mutable_files: list[str] = field(default_factory=lambda: ["train.py"])
    plugin_settings: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        config_path = path or Path(CONFIG_FILENAME)
        if not config_path.exists():
            return cls()  # defaults
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        # Flatten nested TOML tables into flat config
        return cls(
            domain=data.get("domain", "tabular"),
            metric=data.get("metric", {}).get("name", "accuracy"),
            direction=data.get("metric", {}).get("direction", "maximize"),
            budget_minutes=data.get("budget", {}).get("minutes", 60),
            budget_experiments=data.get("budget", {}).get("experiments", 50),
            frozen_files=data.get("files", {}).get("frozen", ["prepare.py"]),
            mutable_files=data.get("files", {}).get("mutable", ["train.py"]),
            plugin_settings=data.get("plugin", {}),
        )
```

### Example mlforge.config.toml
```toml
domain = "tabular"

[metric]
name = "accuracy"
direction = "maximize"

[budget]
minutes = 60
experiments = 50

[files]
frozen = ["prepare.py", "evaluate.py"]
mutable = ["train.py"]

[plugin]
model_families = ["sklearn", "xgboost", "lightgbm"]
```

### Experiment Journal (JSONL)
```python
# Source: Standard JSONL pattern for append-only logs
import json
from datetime import datetime, timezone
from pathlib import Path

JOURNAL_FILE = "experiments.jsonl"

def append_journal_entry(
    path: Path,
    experiment_id: int,
    hypothesis: str,
    result: str,
    metric_value: float | None,
    metric_delta: float | None,
    commit_hash: str | None,
    status: str,  # "keep" | "revert" | "crash"
) -> None:
    entry = {
        "experiment_id": experiment_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis": hypothesis,
        "result": result,
        "metric_value": metric_value,
        "metric_delta": metric_delta,
        "commit_hash": commit_hash,
        "status": status,
    }
    with open(path / JOURNAL_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def load_journal(path: Path) -> list[dict]:
    journal_path = path / JOURNAL_FILE
    if not journal_path.exists():
        return []
    entries = []
    for line in journal_path.read_text().splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries
```

### Guard Hook Script (Bash)
```bash
#!/bin/bash
# .claude/hooks/guard-frozen.sh
# Reads PreToolUse JSON from stdin, denies writes to frozen files.
INPUT=$(cat)

# Extract file_path from tool_input
if command -v jq >/dev/null 2>&1; then
  FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
else
  FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('file_path', ''))
")
fi

BASENAME=$(basename "$FILE_PATH" 2>/dev/null)

# Read frozen files from config (or use defaults)
# In production, this reads from mlforge.config.toml
FROZEN_FILES="prepare.py evaluate.py forecast.py"

for frozen in $FROZEN_FILES; do
  if [ "$BASENAME" = "$frozen" ]; then
    cat <<'DENY'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"This file is FROZEN by mlforge config. Only mutable files can be modified."}}
DENY
    exit 0
  fi
done
exit 0
```

## State of the Art

| Old Approach (autopilot-ml v1-v3) | New Approach (mlforge) | Why Changed |
|-----------------------------------|------------------------|-------------|
| subprocess git calls | GitPython Repo API | Type safety, object model, better error handling |
| str.format() templates | Jinja2 with PackageLoader | Need conditionals, inheritance for multi-domain templates |
| LoopState in loop_helpers.py | SessionState in state.py with JSON persistence | Cleaner separation, explicit persistence API |
| Hardcoded frozen files in hook script | Config-driven frozen files from mlforge.config.toml | Plugin architecture needs per-domain frozen files |
| No config file (everything in code) | mlforge.config.toml with tomllib | User-facing config for budget, domain, metrics |
| No plugin interface | typing.Protocol DomainPlugin | Multi-domain support requires formal plugin contract |
| Markdown experiments.md journal | JSONL machine-readable journal + Jinja2 markdown view | Machine-readable for analysis; markdown for human reading |

**Deprecated/outdated:**
- subprocess-based git_ops.py: Replace with GitPython entirely
- str.format() template rendering: Replace with Jinja2
- Hardcoded `automl` package name: New package is `mlforge`

## Open Questions

1. **PyPI name "mlforge" availability confirmation**
   - What we know: PROJECT.md says "mlforge is available on PyPI"
   - What's unclear: Whether it's been registered yet
   - Recommendation: Verify with `pip index versions mlforge` before writing pyproject.toml; have fallback name ready

2. **Hook script: config-driven vs hardcoded frozen files**
   - What we know: Old approach hardcodes frozen files in the bash script
   - What's unclear: Whether the hook script should read mlforge.config.toml at runtime or be generated with frozen files baked in
   - Recommendation: Generate the hook script during scaffold with frozen files baked in (simpler, no TOML parsing in bash)

3. **Journal format: JSONL vs structured markdown**
   - What we know: CORE-08 says "structured knowledge that survives context resets"; old code used markdown experiments.md
   - What's unclear: Whether the agent reads JSONL or needs markdown
   - Recommendation: JSONL for machine state, render to markdown for agent context injection via Jinja2 template

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured in pyproject.toml) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/ -x --ignore=tests/fixtures -q` |
| Full suite command | `python -m pytest tests/ --ignore=tests/fixtures -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-03 | Plugin renders CLAUDE.md via Jinja2 | unit | `pytest tests/test_templates.py -x` | Wave 0 (new) |
| CORE-04 | State persists to JSON and restores across resets | unit | `pytest tests/test_state.py -x` | Wave 0 (new) |
| CORE-05 | Checkpoint save/load with resume from crash | unit | `pytest tests/test_checkpoint.py -x` | Wave 0 (new) |
| CORE-06 | Config loads from TOML with defaults | unit | `pytest tests/test_config.py -x` | Wave 0 (new) |
| CORE-07 | Hook engine blocks writes to frozen files | unit | `pytest tests/test_hooks.py -x` | Wave 0 (new) |
| CORE-08 | Journal appends entries and survives resets | unit | `pytest tests/test_journal.py -x` | Wave 0 (new) |
| CORE-10 | Git ops: branch, commit, revert, tag | integration | `pytest tests/test_git_ops.py -x` | Wave 0 (new) |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x --ignore=tests/fixtures -q`
- **Per wave merge:** `python -m pytest tests/ --ignore=tests/fixtures -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_state.py` -- covers CORE-04 (SessionState JSON round-trip)
- [ ] `tests/test_checkpoint.py` -- covers CORE-05 (new file for new mlforge checkpoint module)
- [ ] `tests/test_config.py` -- covers CORE-06 (TOML loading, defaults, validation)
- [ ] `tests/test_hooks.py` -- covers CORE-07 (hook settings generation, frozen file guard)
- [ ] `tests/test_journal.py` -- covers CORE-08 (JSONL append/load)
- [ ] `tests/test_git_ops.py` -- covers CORE-10 (new file for GitPython-based git manager)
- [ ] `tests/test_templates.py` -- covers CORE-03 (new file for Jinja2 template rendering)
- [ ] `tests/test_plugins.py` -- covers CORE-03 (plugin protocol conformance)
- [ ] New `src/mlforge/` package structure (replacing old `src/automl/`)
- [ ] Updated `pyproject.toml` for mlforge package name and new dependencies (gitpython, jinja2)

## Sources

### Primary (HIGH confidence)
- [GitPython 3.1.46 Tutorial](https://gitpython.readthedocs.io/en/stable/tutorial.html) -- branch, commit, tag, reset API patterns
- [Jinja2 3.1.x Template Designer Docs](https://jinja.palletsprojects.com/en/stable/templates/) -- Environment, loaders, template syntax
- [Python tomllib stdlib docs](https://docs.python.org/3/library/tomllib.html) -- TOML reading API
- [PEP 544 -- Protocols](https://peps.python.org/pep-0544/) -- typing.Protocol specification
- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks) -- PreToolUse JSON format, settings.json config, deny/allow decisions
- [typing.python.org Protocols](https://typing.python.org/en/latest/reference/protocols.html) -- Protocol usage patterns

### Secondary (MEDIUM confidence)
- Old autopilot-ml codebase (`src/automl/`) -- reference patterns for checkpoint, git_ops, scaffold, templates
- [mypy Protocol docs](https://mypy.readthedocs.io/en/stable/protocols.html) -- static type checking with protocols

### Tertiary (LOW confidence)
- None -- all findings verified with primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries are mature, well-documented, and verified against official docs
- Architecture: HIGH -- patterns derived from old codebase (proven) upgraded with better libraries (verified)
- Pitfalls: HIGH -- GitPython memory leaks, atomic writes, hook permissions all documented in official sources
- Hook engine: HIGH -- Claude Code hooks API verified against official reference at code.claude.com

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable libraries, unlikely to change)
