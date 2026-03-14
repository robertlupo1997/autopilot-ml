# Phase 9: Resume Capability — Research

**Researched:** 2026-03-13
**Domain:** Python JSON checkpoint persistence, CLI flag extension, CLAUDE.md protocol authoring
**Confidence:** HIGH

## Summary

Phase 9 adds checkpoint persistence so that `claude -p` sessions can pick up where they left off. The core problem: when a `claude -p` invocation hits `--max-turns` (or is interrupted), all of `LoopState` — best score, best commit, iteration count, strategy history — is lost in the process heap. The next invocation starts blind, re-drafts from scratch, and wastes 3-5 experiments rediscovering ground already covered.

The solution is a lightweight `checkpoint.json` file written to the experiment directory. The agent (via CLAUDE.md instructions) reads it on startup to skip the draft phase and resume iterating from the best-known state. The CLI gains a `--resume` flag that signals to the scaffolded CLAUDE.md that a checkpoint exists and should be honored. The Python side gets a `checkpoint.py` module (or extension to `loop_helpers.py`) that handles serialization and deserialization.

The entire feature is purely additive: no existing source module changes behavior when `checkpoint.json` is absent. The resume path is a new code branch in the agent's CLAUDE.md protocol, and a new `--resume` CLI flag is plumbed through `cli.py` → `scaffold.py` (or passed at runtime to `claude -p`).

**Primary recommendation:** Use a single `checkpoint.json` file in the experiment root (git-ignored), with a `checkpoint.py` module for read/write, a `--resume` flag in `cli.py`, and a "Resume Protocol" section added to `claude.md.tmpl`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `json` (stdlib) | 3.11+ | Checkpoint serialization | No external deps; already used in `scaffold.py` settings.json |
| `dataclasses` (stdlib) | 3.11+ | `LoopState` is already a dataclass | `dataclasses.asdict()` gives free dict→JSON path |
| `pathlib` (stdlib) | 3.11+ | File path handling | Already used throughout the codebase |
| `argparse` (stdlib) | 3.11+ | `--resume` CLI flag | Already used in `cli.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tempfile` / atomic write | 3.11+ | Safe checkpoint write (write-then-rename) | Prevents corruption if interrupted mid-write |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain JSON file | SQLite / shelve | JSON is human-readable, zero deps, trivially inspectable; SQLite overkill for one-row state |
| In-experiment-dir checkpoint | Per-run branch metadata | JSON file is simpler; git metadata adds complexity and is harder for the agent to read |
| `dataclasses.asdict()` | Manual dict | `asdict()` is automatic and stays in sync with `LoopState` fields |

**Installation:**
```bash
# No new dependencies — stdlib only
```

## Architecture Patterns

### Recommended Project Structure

New file:
```
src/automl/
├── checkpoint.py        # save_checkpoint(), load_checkpoint(), checkpoint_exists()
└── ... (existing)
```

Modified files:
```
src/automl/
├── cli.py               # add --resume flag
└── templates/
    └── claude.md.tmpl   # add Resume Protocol section
```

New test file:
```
tests/
└── test_checkpoint.py   # unit tests for checkpoint module
```

Gitignore addition:
```
checkpoint.json          # added to _gitignore_content() in scaffold.py
```

### Pattern 1: Checkpoint Data Shape

**What:** A flat JSON object capturing all `LoopState` fields plus metadata needed by the agent to resume without re-reading git history.

**When to use:** Written by the agent after every keep/revert decision (as part of the CLAUDE.md loop protocol). Read on startup when `--resume` is set.

```python
# checkpoint.py — canonical checkpoint schema
import json
from dataclasses import asdict
from pathlib import Path

CHECKPOINT_FILE = "checkpoint.json"

def save_checkpoint(loop_state, loop_phase: str, iteration: int, path: str = ".") -> None:
    """Persist LoopState + session metadata to checkpoint.json.

    Uses write-then-rename for atomicity: a partial write never leaves
    a corrupt checkpoint file.

    Parameters
    ----------
    loop_state : LoopState
        Current loop state (dataclass — serialized with asdict).
    loop_phase : str
        "draft" or "iteration" — which phase the agent is in.
    iteration : int
        Total number of experiments run this session.
    path : str
        Directory containing the experiment (default: cwd).
    """
    data = asdict(loop_state)
    data["loop_phase"] = loop_phase
    data["iteration"] = iteration
    data["schema_version"] = 1

    checkpoint_path = Path(path) / CHECKPOINT_FILE
    tmp_path = checkpoint_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(data, indent=2))
    tmp_path.rename(checkpoint_path)


def load_checkpoint(path: str = ".") -> dict | None:
    """Load checkpoint.json if it exists. Returns None if absent."""
    checkpoint_path = Path(path) / CHECKPOINT_FILE
    if not checkpoint_path.exists():
        return None
    return json.loads(checkpoint_path.read_text())


def checkpoint_exists(path: str = ".") -> bool:
    """Return True if checkpoint.json exists in path."""
    return (Path(path) / CHECKPOINT_FILE).exists()
```

**Confidence:** HIGH — stdlib only, matches existing patterns in `scaffold.py` (json.dumps, pathlib).

### Pattern 2: LoopState Deserialization

**What:** `LoopState` is a dataclass. `dataclasses.asdict()` serializes it to a flat dict. Deserialization reconstructs the dataclass from the dict using `**kwargs`.

**When to use:** In `load_checkpoint()` when the caller wants a typed `LoopState` back, not a raw dict.

```python
from dataclasses import asdict
from automl.loop_helpers import LoopState

def load_loop_state(path: str = ".") -> LoopState | None:
    """Load checkpoint and reconstruct LoopState. Returns None if no checkpoint."""
    data = load_checkpoint(path)
    if data is None:
        return None
    # Extract only LoopState fields (ignore loop_phase, iteration, schema_version)
    loop_state_fields = {f.name for f in fields(LoopState)}
    state_dict = {k: v for k, v in data.items() if k in loop_state_fields}
    return LoopState(**state_dict)
```

**Confidence:** HIGH — Python `dataclasses.fields()` is stable since 3.7.

### Pattern 3: CLI --resume Flag

**What:** `argparse` boolean flag that tells the scaffolded project to read `checkpoint.json` on startup.

**When to use:** The flag is added to `cli.py`. It does two things: (1) prints a note to the user that resume mode is active, (2) passes the intent to the `claude -p` invocation via the prompt (or a file). In the simplest form, `--resume` is purely documentational — the real enforcement happens via CLAUDE.md's "Resume Protocol" section, which instructs the agent to check for `checkpoint.json` automatically.

```python
# In cli.py parser setup
parser.add_argument(
    "--resume",
    action="store_true",
    default=False,
    help="Resume from checkpoint.json if present in the experiment directory.",
)
```

**Note on scope:** The `--resume` flag in v1 is a hint, not enforced by Python code at invocation time. The agent's CLAUDE.md Resume Protocol section provides the actual behavior. The flag's primary value is: (a) user communication, (b) a hook point for future automation (Phase 10 swarm orchestrator can pass `--resume` when restarting crashed agents).

**Confidence:** HIGH — `argparse` pattern is already established in `cli.py`.

### Pattern 4: CLAUDE.md Resume Protocol Section

**What:** A new section in `claude.md.tmpl` that instructs the agent to check for `checkpoint.json` on startup, skip the draft phase if a checkpoint exists, and restore its state from the file.

**When to use:** Every new session startup. The check is cheap (file existence test via `ls checkpoint.json`).

```markdown
## Resume Protocol

When starting a new session, check for a previous checkpoint:

1. Run: `ls checkpoint.json 2>/dev/null && echo EXISTS || echo NONE`
2. **If EXISTS:**
   a. Read checkpoint: `cat checkpoint.json`
   b. Restore your state:
      - `best_score` — your current best metric value
      - `best_commit` — git hash of the best train.py; run `git checkout {best_commit}` to restore
      - `loop_phase` — "draft" (still in drafts) or "iteration" (past drafts, iterating)
      - `consecutive_reverts`, `consecutive_crashes` — pick up stagnation/crash tracking
      - `strategy_categories_tried` — avoid re-trying strategies that already failed
      - `total_experiments` — continue the count (for logging)
   c. **Skip Phase 1 (Multi-Draft)** if `loop_phase` is "iteration".
   d. **Go directly to Phase 2** (Iterative Improvement Loop).
   e. Log to results.tsv: `resume: restored from checkpoint, best={best_score}`
3. **If NONE:** Start fresh from Phase 1 (Multi-Draft Initialization).

After every keep/revert decision, update the checkpoint:
- Write current `LoopState` fields + `loop_phase` + `iteration` count to `checkpoint.json`.
- Use the pattern: `python3 -c "import json; ..."`  OR call the helper:
  `python3 -c "from automl.checkpoint import save_checkpoint; from automl.loop_helpers import LoopState; ..."`
```

**Key design decision:** The agent writes its own checkpoint using Python one-liners or by calling `automl.checkpoint`. This avoids needing a running Python process separate from the agent. The agent can use Bash to invoke Python for checkpoint writes.

**Confidence:** MEDIUM — CLAUDE.md protocol enforcement depends on the agent following instructions. Phase 7 validated that CLAUDE.md instructions are followed in headless mode; this is the same mechanism.

### Pattern 5: Atomic Write (Write-Then-Rename)

**What:** Write to `.json.tmp` first, then `rename()` to `checkpoint.json`. On POSIX systems, rename is atomic at the filesystem level.

**Why:** If the agent is interrupted mid-write, the old `checkpoint.json` survives intact. The partial `.json.tmp` is left behind and can be ignored or cleaned up.

```python
tmp_path = checkpoint_path.with_suffix(".json.tmp")
tmp_path.write_text(json.dumps(data, indent=2))
tmp_path.rename(checkpoint_path)  # atomic on POSIX
```

**Confidence:** HIGH — POSIX rename atomicity is guaranteed by the OS kernel. Python's `Path.rename()` maps to `rename(2)` on Linux.

### Anti-Patterns to Avoid

- **Writing checkpoint inside the git commit**: checkpoint.json must be git-ignored (like results.tsv). It's ephemeral session state, not part of the experiment history.
- **Storing checkpoint in a branch commit**: complicates git history, harder for the agent to read back.
- **Overengineering the schema**: `LoopState` fields + 3 metadata fields is all that's needed. Don't add nested objects or versioning complexity for v1.
- **Making `--resume` required for the agent to check checkpoint**: The agent should check for `checkpoint.json` automatically on every startup. `--resume` is optional user-facing documentation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Checkpoint serialization | Custom binary format, pickle, shelve | `json.dumps(dataclasses.asdict(state))` | stdlib, human-readable, trivially debuggable |
| Atomic file writes | Locking daemon, SQLite WAL | Write-then-rename (`Path.rename()`) | POSIX atomic, zero deps |
| State reconstruction | Manual field-by-field copy | `LoopState(**state_dict)` | dataclass `__init__` handles defaults |
| CLI flag parsing | Custom argparse subclass | Standard `add_argument("--resume", action="store_true")` | Already established pattern |

**Key insight:** All of this is stdlib. The complexity of resume is in the CLAUDE.md protocol logic (instructing the agent what to do), not in the Python code.

## Common Pitfalls

### Pitfall 1: Checkpoint Written After Commit, Before Revert Confirmation

**What goes wrong:** The agent writes checkpoint with `best_commit=HEAD` after a revert, but HEAD has already moved back. On resume, the agent checks out a stale commit.

**Why it happens:** The agent's CLAUDE.md says "keep = commit, revert = reset". If checkpoint is written at the wrong point in this sequence, `best_commit` can be wrong.

**How to avoid:** Checkpoint must be written AFTER the keep/revert decision is final:
- Keep path: write checkpoint AFTER `git commit` succeeds (HEAD is the new best).
- Revert path: write checkpoint AFTER `git reset --hard HEAD~1` (HEAD is back to the prior best).

**Warning signs:** On resume, `git checkout {best_commit}` fails with "unknown revision" — the commit hash in the checkpoint doesn't exist on the branch.

### Pitfall 2: Checkpoint Not Git-Ignored

**What goes wrong:** `checkpoint.json` gets committed to the experiment branch. On resume, the agent reads a stale checkpoint from git history instead of the current one.

**Why it happens:** `scaffold.py`'s `_gitignore_content()` doesn't include `checkpoint.json`.

**How to avoid:** Add `checkpoint.json` and `checkpoint.json.tmp` to `_gitignore_content()` in `scaffold.py`. Also add `checkpoint.json` to the existing `.gitignore` in `scaffold.py`.

**Warning signs:** `git status` shows `checkpoint.json` as a tracked/modified file.

### Pitfall 3: Resume Skips Draft Phase When Checkpoint Is From Draft Phase

**What goes wrong:** Agent interrupted mid-draft (loop_phase="draft"). On resume, it sees `loop_phase="draft"` and wrongly skips to iteration phase.

**Why it happens:** The Resume Protocol section only checks for "iteration" to skip drafts, but if the checkpoint says "draft", the agent needs to resume drafting from where it left off.

**How to avoid:** The Resume Protocol must clearly distinguish:
- `loop_phase="draft"`: resume draft generation at the next undrafted family (or restart draft phase safely — all draft results are in results.tsv).
- `loop_phase="iteration"`: skip draft phase entirely, go to iteration.

In practice, re-running the draft phase on resume is acceptable (it just re-evaluates algorithms already evaluated). Simplest correct behavior: if `loop_phase="draft"`, treat as fresh start (run all drafts again). This avoids complex draft-resumption logic. Document this in CLAUDE.md.

### Pitfall 4: `LoopState` Field Mismatch on Deserialization

**What goes wrong:** A future version of `LoopState` adds a new field. Old checkpoints don't have that field. Deserialization crashes with `TypeError: __init__() got an unexpected keyword argument`.

**Why it happens:** `LoopState(**state_dict)` requires exact field match.

**How to avoid:** In `load_loop_state()`, filter `state_dict` to only known `LoopState` fields using `dataclasses.fields(LoopState)`. This is already shown in Pattern 2. Also use `schema_version` in the checkpoint for future-proofing.

### Pitfall 5: `best_commit` Is a Short Hash That Becomes Ambiguous

**What goes wrong:** Short git hashes (7 chars) are non-unique in repos with enough commits. `git checkout {short_hash}` resolves to the wrong commit.

**Why it happens:** `git_ops.py`'s `get_current_commit()` uses `rev-parse --short HEAD` (7 chars). With 10,000+ experiments (plausible for long runs), short hash collisions become possible.

**How to avoid:** Store the full hash in `checkpoint.json`. Change the checkpoint save to call `git rev-parse HEAD` (full 40-char hash) rather than `--short`. The existing `get_current_commit()` uses `--short` for display; add a `get_current_commit_full()` method for checkpoint use.

**Warning signs:** `git checkout` resolves to a different commit than expected (rare, but silent data corruption).

## Code Examples

Verified patterns from this codebase:

### Full checkpoint.py Module
```python
# src/automl/checkpoint.py
"""Checkpoint persistence for session resume.

Writes LoopState + session metadata to checkpoint.json after each experiment.
Allows claude -p sessions to resume from where the last session left off.
"""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from pathlib import Path

CHECKPOINT_FILE = "checkpoint.json"
SCHEMA_VERSION = 1


def save_checkpoint(
    loop_state,
    loop_phase: str,
    iteration: int,
    path: str = ".",
) -> None:
    """Persist LoopState + session metadata to checkpoint.json atomically."""
    data = asdict(loop_state)
    data["loop_phase"] = loop_phase
    data["iteration"] = iteration
    data["schema_version"] = SCHEMA_VERSION

    checkpoint_path = Path(path) / CHECKPOINT_FILE
    tmp_path = checkpoint_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(data, indent=2) + "\n")
    tmp_path.rename(checkpoint_path)


def load_checkpoint(path: str = ".") -> dict | None:
    """Load checkpoint.json if it exists. Returns None if absent or corrupt."""
    checkpoint_path = Path(path) / CHECKPOINT_FILE
    if not checkpoint_path.exists():
        return None
    try:
        return json.loads(checkpoint_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def load_loop_state(path: str = "."):
    """Load checkpoint and reconstruct LoopState. Returns None if no checkpoint."""
    from automl.loop_helpers import LoopState

    data = load_checkpoint(path)
    if data is None:
        return None
    known_fields = {f.name for f in fields(LoopState)}
    state_dict = {k: v for k, v in data.items() if k in known_fields}
    return LoopState(**state_dict)


def checkpoint_exists(path: str = ".") -> bool:
    """Return True if checkpoint.json exists in path."""
    return (Path(path) / CHECKPOINT_FILE).exists()
```

### .gitignore Addition (in scaffold.py)
```python
def _gitignore_content() -> str:
    return textwrap.dedent("""\
        results.tsv
        run.log
        checkpoint.json
        checkpoint.json.tmp
        __pycache__/
        *.pyc
        .venv/
        .claude/settings.local.json
    """)
```

### CLI --resume Flag Addition
```python
# In cli.py, after existing --time-budget argument:
parser.add_argument(
    "--resume",
    action="store_true",
    default=False,
    help=(
        "Resume from checkpoint.json if present in the experiment directory. "
        "Skips the multi-draft phase and restores best score, commit, "
        "and strategy state from the last session."
    ),
)
```

### CLAUDE.md Resume Protocol Section (insertion point)
Insert between "## Phase 1: Multi-Draft Initialization" heading and before the numbered list — or better, add as a preamble section "## Session Resume Check" that appears BEFORE Phase 1.

```markdown
## Session Resume Check

Before starting Phase 1, check for a previous checkpoint:

```bash
ls checkpoint.json 2>/dev/null && echo EXISTS || echo NONE
```

**If EXISTS:**
1. Read: `cat checkpoint.json`
2. Parse the JSON and restore your state:
   - `best_score` and `best_commit`: run `git checkout <best_commit>` to restore
     the best known train.py
   - `loop_phase`: if "iteration", skip Phase 1 entirely and go to Phase 2
   - `consecutive_reverts`, `consecutive_crashes`: resume stagnation/crash tracking
   - `strategy_categories_tried`: do not repeat strategies already exhausted
   - `iteration`: continue the experiment count for results.tsv
3. Log the resume: append a row to results.tsv with status "resume" and a
   description like "resume: best_score=0.8512, iteration=47"
4. **If loop_phase is "draft":** restart Phase 1 from scratch (safe to re-evaluate
   all algorithm families; prior results are already in results.tsv).
5. **If loop_phase is "iteration":** skip to Phase 2.

**If NONE:** proceed normally with Phase 1.

After every keep/revert decision, update the checkpoint:
```bash
python3 -c "
from automl.checkpoint import save_checkpoint
from automl.loop_helpers import LoopState
import json
# rebuild state from your tracked variables and call save_checkpoint(...)
"
```
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Session dies, restart from scratch | checkpoint.json persists state across sessions | Phase 9 | Eliminates wasted draft experiments on resume |
| Agent has no awareness of prior sessions | Agent reads checkpoint.json on startup | Phase 9 | Enables multi-session autonomous runs |
| `--max-turns` ends a run permanently | `--max-turns` ends a session, `--resume` continues | Phase 9 | Long runs decompose into resumable sessions |

**Deprecated/outdated after Phase 9:**
- "Each `claude -p` invocation is a fresh start": no longer true when `checkpoint.json` exists.

## Open Questions

1. **Should the agent write checkpoints or should the runner.py Python process write them?**
   - What we know: The agent (Claude Code) executes the experiment loop. `runner.py` is used by the human to invoke `claude -p`. In the current architecture, `runner.py` doesn't observe the loop mid-run — it only sees the final JSON output.
   - What's unclear: Can the agent reliably call `python3 -c "from automl.checkpoint import ..."` after each decision without it becoming a distraction?
   - Recommendation: Agent writes checkpoints via Bash tool calls to `python3 -c`. This is consistent with how the agent writes `results.tsv`. Keep it simple for v1.

2. **Should `--resume` be passed to `claude -p` (runner invocation) or used at scaffold time?**
   - What we know: The flag is on the `automl` CLI. But `automl` only scaffolds — it doesn't invoke `claude -p`. The user runs `claude -p` manually or via `run-validation-test.sh`.
   - Recommendation: `--resume` in `cli.py` is purely informational for v1 — it prints a hint. The actual resume behavior comes from CLAUDE.md's "Session Resume Check" section, which fires on every startup regardless of flags. The flag's value is as a hook point for Phase 10 (swarm manager can pass `--resume` when restarting an agent).

3. **What is the expected write frequency of checkpoints?**
   - Recommendation: Write after every keep/revert (not every experiment attempt). This matches how results.tsv is written — one entry per completed experiment. For a 60-second experiment, this means one checkpoint write per ~60 seconds. Negligible overhead.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already installed, `tests/` directory exists) |
| Config file | none — pytest auto-discovers `tests/test_*.py` |
| Quick run command | `uv run pytest tests/test_checkpoint.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

Phase 9 requirements are TBD, but based on the goal they map to:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| `save_checkpoint()` writes valid JSON | unit | `uv run pytest tests/test_checkpoint.py::TestSaveCheckpoint -x` | Wave 0 |
| `load_checkpoint()` returns None when no file | unit | `uv run pytest tests/test_checkpoint.py::TestLoadCheckpoint -x` | Wave 0 |
| `load_loop_state()` reconstructs LoopState correctly | unit | `uv run pytest tests/test_checkpoint.py::TestLoadLoopState -x` | Wave 0 |
| Atomic write: corrupt .tmp doesn't affect .json | unit | `uv run pytest tests/test_checkpoint.py::TestAtomicWrite -x` | Wave 0 |
| `checkpoint_exists()` returns True/False correctly | unit | `uv run pytest tests/test_checkpoint.py::TestCheckpointExists -x` | Wave 0 |
| scaffold generates checkpoint.json in .gitignore | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldGitignore -x` | exists (extend) |
| cli.py --resume flag is accepted | unit | `uv run pytest tests/test_cli.py::TestCliResumeFlag -x` | Wave 0 |
| CLAUDE.md contains "Session Resume Check" section | unit | `uv run pytest tests/test_templates.py::TestClaudeMdResumeSection -x` | Wave 0 |
| LoopState fields survive round-trip serialization | unit | `uv run pytest tests/test_checkpoint.py::TestRoundTrip -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_checkpoint.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_checkpoint.py` — covers all checkpoint module behaviors
- [ ] Extend `tests/test_scaffold.py` — test `checkpoint.json` and `checkpoint.json.tmp` in .gitignore
- [ ] Extend `tests/test_cli.py` — test `--resume` flag accepted without error
- [ ] Extend `tests/test_templates.py` — test "Session Resume Check" section in CLAUDE.md

*(No framework install needed — pytest already present)*

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `/home/tlupo/AutoML/src/automl/loop_helpers.py` — LoopState fields, dataclass pattern
- Direct code inspection of `/home/tlupo/AutoML/src/automl/scaffold.py` — gitignore pattern, settings.json pattern
- Direct code inspection of `/home/tlupo/AutoML/src/automl/cli.py` — argparse pattern
- Direct code inspection of `/home/tlupo/AutoML/src/automl/templates/claude.md.tmpl` — CLAUDE.md structure and insertion point
- Direct code inspection of `/home/tlupo/AutoML/src/automl/git_ops.py` — git operations available

### Secondary (MEDIUM confidence)
- `.planning/research/claude-code-capabilities-research.md` (2026-03-10) — session resumption noted as P1 priority
- `.planning/STATE.md` key decisions — confirms project patterns (subprocess for git, no GitPython, dataclass-based LoopState)

### Tertiary (LOW confidence)
- General knowledge of POSIX rename atomicity — standard behavior on Linux, matches this WSL2 environment

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, no external dependencies, patterns confirmed in codebase
- Architecture: HIGH — directly extends existing dataclass and JSON patterns in the codebase
- Pitfalls: HIGH — derived from direct analysis of `loop_helpers.py` field structure and `git_ops.py` short-hash usage
- CLAUDE.md protocol: MEDIUM — behavior depends on agent following instructions; Phase 7 validated this mechanism works

**Research date:** 2026-03-13
**Valid until:** 2026-06-13 (stable stdlib patterns; no expiry risk)
