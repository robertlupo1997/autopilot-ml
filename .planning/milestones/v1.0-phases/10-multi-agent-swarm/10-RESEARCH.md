# Phase 10: Multi-Agent Swarm - Research

**Researched:** 2026-03-14
**Domain:** Parallel process orchestration, git worktrees, file-locked coordination, Claude Code headless multi-agent
**Confidence:** HIGH

---

## Summary

Phase 10 adds a `--agents N` flag to the CLI that spawns N parallel `claude -p` subprocesses, each exploring different ML algorithm families via git worktrees. Coordination uses only the local filesystem and stdlib (`fcntl`, `subprocess`, `json`) — no external services. The design is fully documented in `.planning/research/multi-agent-swarm-research.md` (2026-03-13), and the implementation plan is concrete enough to be broken directly into tasks.

The prior research analyzed three external systems (autoresearch-at-home, AgentHub, Karpathy's original autoresearch) and designed a simpler local-only architecture that fits AutoML's single-machine, dependency-free constraints. The key finding: git worktrees provide exactly the isolation needed — each agent gets its own HEAD, index, and working tree while sharing the object store. A file-locked `scoreboard.tsv` provides cross-agent metric tracking. Algorithm family partitioning (not semantic claim dedup) eliminates work duplication without any embedding service.

The existing codebase integrates cleanly: `drafts.py` already defines the 5 algorithm families that map directly to agent assignments; `git_ops.py` needs two new methods (`create_worktree`, `remove_worktree`); `cli.py` needs `--agents N`; `scaffold.py` generates the `.swarm/` directory structure. All new code is in three new files: `swarm.py`, `swarm_scoreboard.py`, `swarm_claims.py`.

**Primary recommendation:** Follow the architecture from `.planning/research/multi-agent-swarm-research.md` exactly. It is correct, verified against the codebase, and complete enough to build directly from.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `subprocess` | stdlib | Spawn and monitor `claude -p` processes | Already used throughout for git ops and experiment runner |
| `fcntl` | stdlib | Exclusive file lock on scoreboard writes | POSIX-standard, zero deps, confirmed available on WSL2 |
| `json` | stdlib | Parse/write scoreboard config, agent assignments | Already used for checkpoint.py |
| `pathlib` | stdlib | File path manipulation | Already used throughout |
| `signal` | stdlib | SIGINT handler for graceful swarm shutdown | Already used in train_template.py for timeout enforcement |
| `dataclasses` | stdlib | SwarmConfig, AgentConfig DTOs | Already used for LoopState |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `time` | stdlib | Timestamps for scoreboard entries, claim TTL expiry | During experiment logging |
| `threading` | stdlib | Monitor loop (watch agent processes, print progress) | SwarmManager.run() monitoring thread |
| `shutil` | stdlib | Copy shared files into worktrees if not using git | Fallback if worktree isolation insufficient |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| git worktrees | Separate `git clone .` per agent | Worktrees recommended: shared object store saves disk, branches visible across all worktrees for comparison |
| fcntl file locking | Per-agent files + merge | File locking is simpler; per-agent approach adds merge step |
| Family partitioning | Semantic dedup (embeddings) | Family partitioning requires zero external services and covers 100% of the draft phase collision problem |

**Installation:**
```bash
# No new dependencies — stdlib only
```

---

## Architecture Patterns

### Recommended Project Structure

New files:
```
src/automl/
├── swarm.py              # SwarmManager: orchestrate N claude -p agents
├── swarm_scoreboard.py   # SwarmScoreboard: file-locked cross-agent results TSV
└── swarm_claims.py       # Lightweight TTL claim files for iteration-phase dedup
```

Modified files:
```
src/automl/
├── git_ops.py            # + create_worktree(), remove_worktree()
├── cli.py                # + --agents N flag
└── scaffold.py           # + .swarm/ dir creation when agents > 1
```

New templates:
```
src/automl/templates/
└── swarm_claude.md.tmpl  # Agent-specific CLAUDE.md with coordination rules
```

New scripts:
```
scripts/
└── run-swarm-test.sh     # Manual validation (mirrors run-validation-test.sh)
```

### Pattern 1: Git Worktree Setup

**What:** Each agent gets a separate working directory via `git worktree add`. Verified locally: worktrees inside `.swarm/agent-N/` work correctly. Each worktree has a `.git` file (pointer to main `.git`), not a `.git` directory.

**When to use:** During `SwarmManager.setup()` before agents are spawned.

**Example:**
```python
# src/automl/git_ops.py additions
def create_worktree(self, path: str, branch: str) -> str:
    """Create a git worktree at path with a new branch."""
    self._run("worktree", "add", path, "-b", branch)
    return branch

def remove_worktree(self, path: str) -> None:
    """Remove a git worktree and its metadata."""
    self._run("worktree", "remove", path, "--force")
```

**Caveat:** The experiment directory scaffolded by `scaffold_experiment()` must already have at least one git commit (it does — `_dot_claude_settings` creates it via `init_repo()`). Worktrees require an initialized repo with at least one commit. Verified: `git worktree add .swarm/agent-0 -b automl/run-X/agent-0` works correctly when main repo has initial commit.

### Pattern 2: File-Locked Scoreboard

**What:** A single `scoreboard.tsv` tracks all agent results. Writes use `fcntl.LOCK_EX` on a separate lockfile to prevent corruption. Reads are lockless (single-line append is atomic on Linux, but locking on writes ensures the "new global best" detection is consistent).

**When to use:** After every keep/revert decision across all agents.

**Example (from prior research, verified against stdlib docs):**
```python
# src/automl/swarm_scoreboard.py
import fcntl
from pathlib import Path
import time

HEADER = "agent\tcommit\tmetric_value\telapsed_sec\tstatus\tdescription\ttimestamp\n"

class SwarmScoreboard:
    def __init__(self, swarm_dir: Path):
        self.scoreboard_path = swarm_dir / "scoreboard.tsv"
        self.lock_path = swarm_dir / "scoreboard.lock"
        self.best_train_path = swarm_dir / "best_train.py"

    def read_best(self) -> tuple[float | None, str | None]:
        """Read global best. No lock needed -- worst case reads stale by one row."""
        if not self.scoreboard_path.exists():
            return None, None
        best_score = None
        best_agent = None
        with open(self.scoreboard_path) as f:
            next(f, None)  # skip header
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 5 and parts[4] == "keep":
                    score = float(parts[2])
                    if best_score is None or score > best_score:
                        best_score = score
                        best_agent = parts[0]
        return best_score, best_agent

    def publish_result(self, agent_id: str, commit: str, metric_value: float,
                       elapsed_sec: float, status: str, description: str,
                       train_py_source: str | None = None) -> bool:
        """Append result, update best_train.py if new global best. Returns is_new_best."""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(self.lock_path, "w") as lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            try:
                if not self.scoreboard_path.exists():
                    self.scoreboard_path.write_text(HEADER)
                current_best, _ = self.read_best()
                with open(self.scoreboard_path, "a") as f:
                    f.write(f"{agent_id}\t{commit}\t{metric_value:.6f}\t"
                            f"{elapsed_sec:.1f}\t{status}\t{description}\t{timestamp}\n")
                is_new_best = (
                    status == "keep"
                    and (current_best is None or metric_value > current_best)
                )
                if is_new_best and train_py_source:
                    self.best_train_path.write_text(train_py_source)
                return is_new_best
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
```

### Pattern 3: Agent Spawning via subprocess.Popen

**What:** Each agent is a `claude -p` subprocess with a tailored prompt. The SwarmManager holds all Popen handles for monitoring. Important: the `--allowedTools` flag is REQUIRED for headless mode (per Phase 7/8 findings — `settings.json` allow rules are silently ignored in `claude -p`).

**When to use:** In `SwarmManager.run()`.

**Example:**
```python
# src/automl/swarm.py
import subprocess
from pathlib import Path

def spawn_agent(agent_id: int, workdir: Path, assigned_families: list[dict],
                metric: str, time_budget: int, swarm_dir: Path) -> subprocess.Popen:
    family_names = ", ".join(f["name"] for f in assigned_families)
    prompt = f"""You are Agent-{agent_id} in a multi-agent ML experiment swarm.
Read swarm_claude.md for the full protocol. Key facts:
YOUR ASSIGNED ALGORITHM FAMILIES: {family_names}
SWARM SCOREBOARD: {swarm_dir}/scoreboard.tsv
METRIC TO OPTIMIZE: {metric} (higher is better)
TIME BUDGET PER EXPERIMENT: {time_budget}s
"""
    return subprocess.Popen(
        [
            "claude", "-p", prompt,
            "--allowedTools", "Bash(*)", "Edit(*)", "Write(*)", "Read", "Glob", "Grep",
            "--output-format", "json",
        ],
        cwd=str(workdir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
```

**Critical constraint:** `claude -p` cannot be launched from within an active Claude Code session (documented in `run-validation-test.sh` header). The swarm manager must be invoked from a terminal outside Claude Code, same as existing validation scripts.

### Pattern 4: Family Partitioning

**What:** Round-robin assignment of `ALGORITHM_FAMILIES` from `drafts.py` to agents. Agent-0 gets families [0, N, 2N...], agent-1 gets [1, N+1...]. No claiming needed during draft phase.

**When to use:** In `SwarmManager._divide_families()`.

**Example:**
```python
def _divide_families(self, families: list[dict], n_agents: int) -> list[list[dict]]:
    assignments = [[] for _ in range(n_agents)]
    for i, family in enumerate(families):
        assignments[i % n_agents].append(family)
    return assignments
```

For 3 agents on classification (5 families): agent-0 gets [LogisticRegression, SVM], agent-1 gets [RandomForest, (none if 5%3=2)], actually: agent-0=[0,3]=[LogReg, LightGBM], agent-1=[1,4]=[RF, SVM], agent-2=[2]=[XGBoost]. Each agent always gets at least one family.

### Pattern 5: TTL Claim Files (Iteration Phase)

**What:** Lightweight JSON files in `.swarm/claims/` prevent two agents from running identical iteration experiments. Name includes a description hash for dedup. Claims expire after TTL seconds (default 300 = 5 minutes).

**When to use:** During iteration phase, before starting an experiment idea.

**Example:**
```python
# src/automl/swarm_claims.py
import hashlib, json, time
from pathlib import Path

CLAIM_TTL = 300  # seconds

def try_claim(claims_dir: Path, agent_id: str, description: str) -> bool:
    """Attempt to claim an experiment idea. Returns True if claim succeeded."""
    key = hashlib.md5(description.encode()).hexdigest()[:8]
    claim_path = claims_dir / f"{agent_id}--{key}.json"
    # Check for active claim by any agent
    for existing in claims_dir.glob(f"*--{key}.json"):
        try:
            data = json.loads(existing.read_text())
            age = time.time() - data["claimed_at"]
            if age < CLAIM_TTL:
                return False  # active claim exists
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    claim_path.write_text(json.dumps({
        "agent_id": agent_id,
        "description": description,
        "claimed_at": time.time(),
    }))
    return True

def release_claim(claims_dir: Path, agent_id: str, description: str) -> None:
    key = hashlib.md5(description.encode()).hexdigest()[:8]
    claim_path = claims_dir / f"{agent_id}--{key}.json"
    claim_path.unlink(missing_ok=True)
```

**Note:** In practice, family partitioning prevents most collisions. Claims are a safety net for the iteration phase only, and duplicate experiments are benign (both contribute data to scoreboard).

### Pattern 6: Swarm Agent CLAUDE.md

**What:** Each agent worktree gets a `swarm_claude.md` (or the standard `CLAUDE.md` + agent-specific context injected into the prompt). The swarm-specific instructions add:
- Read `scoreboard.tsv` before each experiment
- Append to `scoreboard.tsv` after each experiment (with fcntl locking)
- If another agent has better score, read `best_train.py` and consider adopting
- Only explore assigned algorithm families during draft phase

**Design choice:** Inject agent-specific context in the spawn prompt (assigned families, scoreboard path), keep the rest in a shared `swarm_claude.md.tmpl` template in the worktree. This avoids per-agent template generation.

### Anti-Patterns to Avoid

- **Shared results.tsv across agents:** Race condition without locking. Use per-agent `results.tsv` (each worktree has its own) plus `scoreboard.tsv` for cross-agent tracking.
- **Shared train.py across agents:** Agents MUST work in isolated worktrees — never share a working train.py.
- **git clone instead of worktrees:** Creates separate `.git` directories, branches invisible across agents, more disk usage.
- **Blocking monitor loop:** SwarmManager monitor loop must be non-blocking (use short poll intervals, not blocking `Popen.wait()`).
- **Spawning agents from inside Claude Code:** Will fail. Must run from external terminal.
- **Using .git lockfile:** git creates `.git/index.lock` during operations. Worktrees each have their own index, so concurrent git operations in different worktrees are safe (no shared lock).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File locking | Custom lock protocol | `fcntl.flock(LOCK_EX)` | POSIX standard, handles crash recovery automatically (lock released on process exit) |
| Process monitoring | Custom signal polling | `proc.poll()` + `proc.returncode` | subprocess.Popen already provides non-blocking process status |
| Git isolation | Manual file copying per agent | `git worktree add` | Worktrees are purpose-built; shared object store, independent HEAD/index/working-tree |
| Claim TTL expiry | Daemon process to clean stale claims | Age check at read time | Read-time expiry is simpler, no background process needed |
| Agent load balancing | Complex scheduling | Round-robin family assignment | Simple assignment covers 100% of the draft phase; iteration phase is unconstrained |

**Key insight:** Local filesystem + git worktrees + fcntl covers all coordination needs. No message queue, no database, no network service.

---

## Common Pitfalls

### Pitfall 1: git worktree requires at least one commit

**What goes wrong:** `git worktree add` fails with "fatal: not a git repository" or "fatal: HEAD" error if the main repo has no commits yet.
**Why it happens:** Worktrees need a valid HEAD to base the new branch on.
**How to avoid:** `scaffold_experiment()` already calls `init_repo()` which creates an initial commit. Worktree setup must happen AFTER scaffold (not before). Verify with `git log --oneline` before calling `create_worktree`.
**Warning signs:** `subprocess.CalledProcessError` on `git worktree add`.

### Pitfall 2: `claude -p` cannot be spawned inside Claude Code

**What goes wrong:** Running the swarm manager from within an active Claude Code session fails — the inner `claude -p` processes cannot acquire the necessary resources.
**Why it happens:** Documented in `run-validation-test.sh`: "Claude Code cannot launch `claude -p` inside another Claude Code session."
**How to avoid:** The `--agents N` flag must invoke a script that users run from an external terminal, same as `run-validation-test.sh`. The `cli.py` help text must state this explicitly.
**Warning signs:** claude subprocess immediately exits with error or produces no output.

### Pitfall 3: `settings.json` allow rules ignored in headless mode

**What goes wrong:** Agent processes fail with permission denials even though `settings.json` has broad allow rules.
**Why it happens:** Confirmed in Phase 7/8 — `settings.json` permissions.allow is silently ignored for headless `claude -p`. `--allowedTools` flag is required.
**How to avoid:** Always pass `--allowedTools "Bash(*)" "Edit(*)" "Write(*)" "Read" "Glob" "Grep"` when spawning agent subprocesses. This is already the pattern in `run-validation-test.sh`.
**Warning signs:** `stop_reason: tool_use` in agent output JSON, 0 experiments run.

### Pitfall 4: scoreboard.lock write semantics

**What goes wrong:** Using `open(lock_path, "w")` truncates the file on each call, which is fine for the lock itself but could cause issues if accidentally reading from it.
**Why it happens:** The lock file is purely a lock primitive — it exists only to give `fcntl.flock` something to lock on.
**How to avoid:** Never read from `scoreboard.lock`. The scoreboard data is in `scoreboard.tsv`. Lock file is always opened with `"w"` mode (creates or truncates, then immediately locked).

### Pitfall 5: git worktree branches conflict on re-run

**What goes wrong:** Running `--agents 3` twice with the same run tag fails because branches `automl/run-{tag}/agent-{N}` already exist.
**Why it happens:** `git worktree add -b branch` fails if branch already exists.
**How to avoid:** Include a timestamp or UUID in the run tag (same as existing `runner.py` pattern). OR check for existing branches and use `--detach` or `git worktree add path branch` (without -b) if branch exists.

### Pitfall 6: Disk space from worktrees

**What goes wrong:** Worktrees appear to duplicate all files; users panic about disk usage.
**Why it happens:** Each worktree has its own working tree (actual files) but shares the git object store. For a tabular ML experiment with a small CSV, each worktree is ~1-5 MB working tree only.
**How to avoid:** Document that worktrees share `.git` object store. Cleanup worktrees after the swarm completes via `git worktree remove --force` + `git worktree prune`.

### Pitfall 7: agents write to scoreboard without locking

**What goes wrong:** Two agents simultaneously append to `scoreboard.tsv`, corrupting a line.
**Why it happens:** Append-only writes are not atomic for multi-byte writes.
**How to avoid:** The CLAUDE.md agent instructions must include the exact locking code for scoreboard updates. Don't rely on agents to figure out `fcntl` — give them the exact Python snippet to run.

---

## Code Examples

### SwarmManager Skeleton

```python
# src/automl/swarm.py
import signal
import subprocess
import time
from pathlib import Path
from automl.drafts import ALGORITHM_FAMILIES
from automl.git_ops import GitManager
from automl.swarm_scoreboard import SwarmScoreboard

class SwarmManager:
    def __init__(self, experiment_dir: Path, n_agents: int, task_type: str,
                 metric: str, time_budget: int):
        self.experiment_dir = experiment_dir
        self.n_agents = n_agents
        self.task_type = task_type
        self.metric = metric
        self.time_budget = time_budget
        self.swarm_dir = experiment_dir / ".swarm"
        self.scoreboard = SwarmScoreboard(self.swarm_dir)
        self.git = GitManager(repo_dir=str(experiment_dir))
        self.agents: list[subprocess.Popen] = []
        self._shutdown = False

    def setup(self) -> list[list[dict]]:
        """Create .swarm/ structure, worktrees, divide families."""
        self.swarm_dir.mkdir(exist_ok=True)
        (self.swarm_dir / "claims").mkdir(exist_ok=True)
        families = ALGORITHM_FAMILIES[self.task_type]
        assignments = self._divide_families(families, self.n_agents)
        import json
        run_tag = time.strftime("%Y%m%d-%H%M%S")
        for i in range(self.n_agents):
            agent_dir = self.swarm_dir / f"agent-{i}"
            branch = f"automl/run-{run_tag}/agent-{i}"
            self.git.create_worktree(str(agent_dir), branch)
        (self.swarm_dir / "config.json").write_text(json.dumps({
            "n_agents": self.n_agents,
            "task_type": self.task_type,
            "metric": self.metric,
            "run_tag": run_tag,
            "assignments": [[f["name"] for f in a] for a in assignments],
        }, indent=2))
        return assignments

    def run(self, assignments: list[list[dict]]) -> None:
        """Spawn agents and monitor until all complete or SIGINT."""
        signal.signal(signal.SIGINT, self._handle_sigint)
        for i, assigned in enumerate(assignments):
            workdir = self.swarm_dir / f"agent-{i}"
            proc = spawn_agent(i, workdir, assigned, self.metric,
                               self.time_budget, self.swarm_dir)
            self.agents.append(proc)
        self._monitor_loop()

    def _monitor_loop(self) -> None:
        while not self._shutdown:
            alive = [p for p in self.agents if p.poll() is None]
            if not alive:
                break
            best_score, best_agent = self.scoreboard.read_best()
            print(f"[swarm] {len(alive)}/{self.n_agents} agents running | "
                  f"global best: {best_score} ({best_agent})")
            time.sleep(10)

    def _handle_sigint(self, sig, frame):
        print("\n[swarm] Shutdown signal received. Terminating agents...")
        self._shutdown = True
        for proc in self.agents:
            proc.terminate()

    def _divide_families(self, families, n_agents):
        assignments = [[] for _ in range(n_agents)]
        for i, family in enumerate(families):
            assignments[i % n_agents].append(family)
        return assignments

    def teardown(self) -> None:
        """Remove worktrees after swarm completes."""
        for i in range(self.n_agents):
            agent_dir = self.swarm_dir / f"agent-{i}"
            if agent_dir.exists():
                try:
                    self.git.remove_worktree(str(agent_dir))
                except Exception:
                    pass
        self.git._run("worktree", "prune")
```

### CLI Integration

```python
# cli.py addition -- --agents flag
parser.add_argument(
    "--agents",
    type=int,
    default=1,
    metavar="N",
    help=(
        "Number of parallel claude -p agents to spawn (default: 1). "
        "When N > 1, spawns a multi-agent swarm. "
        "IMPORTANT: Must be run from a terminal outside of Claude Code."
    ),
)
```

### Agent CLAUDE.md Coordination Block

```markdown
## Swarm Coordination Protocol

You are one of {n_agents} parallel agents. Your assigned algorithm families are:
{family_names}

### Before Every Experiment
Read the global scoreboard:
```bash
cat {swarm_dir}/scoreboard.tsv | tail -20
```
If another agent has a better score than your current best, read their best solution:
```bash
cat {swarm_dir}/best_train.py
```
Consider adopting it as your new starting point.

### After Every Keep/Revert Decision
Publish your result to the scoreboard:
```python
import fcntl, time
line = f"agent-{agent_id}\t{commit}\t{metric:.6f}\t{elapsed:.1f}\t{status}\t{desc}\t{timestamp}\n"
with open("{swarm_dir}/scoreboard.lock", "w") as lf:
    fcntl.flock(lf, fcntl.LOCK_EX)
    try:
        with open("{swarm_dir}/scoreboard.tsv", "a") as f:
            f.write(line)
        # If this is your new best AND global best, copy train.py
        if status == "keep":
            import shutil
            shutil.copy("train.py", "{swarm_dir}/best_train.py")
    finally:
        fcntl.flock(lf, fcntl.LOCK_UN)
```
```

---

## Implementation Plan Breakdown

The prior research proposes 4 implementation phases. For planning purposes, this maps to 3 plans:

### Plan 10-01: Core Infrastructure (new files)
- `src/automl/swarm_scoreboard.py` — SwarmScoreboard with file locking
- `src/automl/swarm_claims.py` — TTL claim files
- `src/automl/swarm.py` — SwarmManager (setup, spawn, monitor, teardown)
- Unit tests for all three modules
- Estimated: ~350 lines new code + ~200 lines tests

### Plan 10-02: Integration (modify existing + new template)
- `src/automl/git_ops.py` — add `create_worktree()`, `remove_worktree()`
- `src/automl/cli.py` — add `--agents N` flag
- `src/automl/scaffold.py` — add `.swarm/` gitignore entries
- `src/automl/templates/swarm_claude.md.tmpl` — agent swarm coordination template
- Unit tests for git_ops additions and CLI flag
- Estimated: ~120 lines modifications + ~80 lines tests

### Plan 10-03: Swarm Validation Script
- `scripts/run-swarm-test.sh` — 2-agent validation (mirrors run-validation-test.sh)
- Manual: run, verify both agents produce results, scoreboard populated correctly
- Estimated: ~80 lines script

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Single `claude -p` agent, sequential drafts | N parallel `claude -p` agents, each owning a family | N× draft coverage in same wall-clock time |
| Sequential experiment loop | N independent experiment loops with shared global best | Explores N diverse approaches simultaneously |
| No coordination | File-locked scoreboard + family partitioning | Agents aware of each other's discoveries |
| Single branch per run | N worktree branches per run | Full git history per agent, comparable across agents |

**No deprecated patterns** — this is net-new functionality.

---

## Open Questions

1. **`--max-budget-usd` per agent vs total**
   - What we know: each `claude -p` invocation accepts `--max-budget-usd`
   - What's unclear: should the budget cap be per-agent or divided across agents?
   - Recommendation: per-agent budget (e.g., `--max-budget-usd 2.0` each for 3 agents = $6 total). Simpler to reason about. Document in CLI help.

2. **Whether global best adoption improves outcomes**
   - What we know: autoresearch-at-home adopts global best every 5 runs
   - What's unclear: for tabular ML (fast experiments, 5 families), does cross-adoption matter?
   - Recommendation: include adoption logic in CLAUDE.md but make it conditional ("if global best > your best, consider adopting"). Don't force it.

3. **What to do if `n_agents > len(ALGORITHM_FAMILIES)`**
   - What we know: 5 families per task type; typical use is 2-4 agents
   - Recommendation: cap at `len(ALGORITHM_FAMILIES)` and warn if user requests more. Or allow it — extra agents just get empty draft assignments and proceed directly to iteration on global best.

4. **git worktree behavior when `.swarm/` is in `.gitignore`**
   - What we know: scaffold.py `.gitignore` does not currently include `.swarm/`
   - What's unclear: should `.swarm/` be git-ignored? It contains worktrees which are git-managed, plus `scoreboard.tsv`
   - Recommendation: Add `.swarm/scoreboard.tsv`, `.swarm/scoreboard.lock`, `.swarm/claims/` to `.gitignore`. Do NOT ignore `.swarm/` itself — git worktrees registered there are tracked in `.git/worktrees/`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (uv run pytest) |
| Config file | none — pytest auto-discovers tests/ |
| Quick run command | `cd /home/tlupo/AutoML && uv run pytest tests/test_swarm*.py tests/test_git.py -x -q` |
| Full suite command | `cd /home/tlupo/AutoML && uv run pytest -x -q` |

### Phase Requirements → Test Map

No formal requirement IDs provided for Phase 10. Behaviors to test:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| SwarmScoreboard.publish_result appends correctly | unit | `uv run pytest tests/test_swarm_scoreboard.py -x -q` | Wave 0 |
| SwarmScoreboard concurrent writes don't corrupt | unit (threading) | `uv run pytest tests/test_swarm_scoreboard.py::TestConcurrentWrites -x -q` | Wave 0 |
| SwarmScoreboard.read_best returns highest "keep" | unit | `uv run pytest tests/test_swarm_scoreboard.py::TestReadBest -x -q` | Wave 0 |
| swarm_claims.try_claim returns False for active claims | unit | `uv run pytest tests/test_swarm_claims.py -x -q` | Wave 0 |
| swarm_claims TTL expiry allows re-claiming | unit | `uv run pytest tests/test_swarm_claims.py::TestTTLExpiry -x -q` | Wave 0 |
| git_ops.create_worktree creates worktree + branch | integration | `uv run pytest tests/test_git.py -x -q` | Modify existing |
| git_ops.remove_worktree removes worktree cleanly | integration | `uv run pytest tests/test_git.py -x -q` | Modify existing |
| SwarmManager._divide_families round-robin assignment | unit | `uv run pytest tests/test_swarm.py::TestDivideFamilies -x -q` | Wave 0 |
| CLI --agents flag accepted and passed through | unit | `uv run pytest tests/test_cli.py -x -q` | Modify existing |
| scaffold .gitignore includes .swarm/ entries | unit | `uv run pytest tests/test_scaffold.py -x -q` | Modify existing |
| 2-agent swarm produces results in scoreboard | manual smoke | `./scripts/run-swarm-test.sh` | Wave 0 (Plan 10-03) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_swarm*.py tests/test_git.py tests/test_cli.py tests/test_scaffold.py -x -q`
- **Per wave merge:** `uv run pytest -x -q` (full 171+ test suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_swarm_scoreboard.py` — covers SwarmScoreboard behaviors including concurrent writes
- [ ] `tests/test_swarm_claims.py` — covers claim TTL, dedup, release
- [ ] `tests/test_swarm.py` — covers SwarmManager.setup, _divide_families, teardown (mocked claude subprocess)
- [ ] `scripts/run-swarm-test.sh` — manual validation script

*(Existing test infrastructure covers all other behaviors: git_ops, cli, scaffold tests already exist and will be extended)*

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `src/automl/git_ops.py`, `cli.py`, `scaffold.py`, `drafts.py`, `loop_helpers.py`, `checkpoint.py` — verified all integration points
- Local verification: `git worktree add .swarm/agent-0 -b branch` — confirmed working on this machine (WSL2 Linux)
- Local verification: `python3 -c "import fcntl; print('ok')"` — confirmed fcntl available on WSL2
- `.planning/research/multi-agent-swarm-research.md` — comprehensive prior research with code examples

### Secondary (MEDIUM confidence)
- `scripts/run-validation-test.sh` — confirmed `--allowedTools` required, `claude -p` cannot run inside Claude Code session
- Test suite baseline: 171 tests, all passing — integration baseline confirmed

### Tertiary (LOW confidence)
- autoresearch-at-home claiming protocol (from prior research, not re-verified in this session)
- AgentHub architecture (from prior research, not re-verified in this session)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, all imports verified available
- Architecture: HIGH — based on verified prior research + direct code inspection
- Pitfalls: HIGH — most pitfalls derived from actual Phase 7/8 findings documented in STATE.md
- Git worktrees: HIGH — locally verified working on this machine
- File locking: HIGH — fcntl confirmed available, POSIX standard

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable — stdlib, git, and Claude Code headless API unlikely to change)
