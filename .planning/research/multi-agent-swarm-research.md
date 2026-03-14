# Multi-Agent Swarm for Parallel ML Experimentation — Research Report

**Date:** 2026-03-13
**Status:** Research complete, design proposed

---

## 1. Findings from External Repos

### 1.1 autoresearch-at-home (mutable-state-inc)

**Repo:** github.com/mutable-state-inc/autoresearch-at-home
**What it is:** A community fork of Karpathy's autoresearch that adds SETI@home-style distributed coordination via a shared memory service (Ensue).

**Architecture:**
- Each agent runs independently on its own machine/GPU with its own git fork
- Coordination happens through an external shared memory service (Ensue), NOT through git or the filesystem
- Git stays completely local — Ensue is the only shared state
- The network is **gracefully degradable**: if Ensue goes down, agents continue solo

**Agent Spawning:**
- Agents are NOT centrally spawned — each is an independent `claude` process started by a human
- Each agent registers with an API key and picks a codename (e.g., "nova", "phoenix")
- Agents self-organize through the shared workspace

**Work Division (Claiming Protocol):**
1. Generate a human-readable key: `<agent>--<slug>--<short_hash>` (e.g., `nova--increase-lr-to-004--a7f3b2`)
2. Check if a result already exists for that key — skip if so
3. Check if another agent has a fresh claim (< 15 min old) — skip if so
4. Semantic search for similar active claims (> 92% similarity threshold) — skip if so
5. Write the claim, wait 2 seconds, re-read — earliest `created_at` wins the race
6. Claims auto-expire after 15 minutes (CLAIM_TTL = 900 seconds)
7. After 5 failed claim attempts, just run something — rare duplicate beats idling

**Result Sharing:**
- Every experiment publishes full `train.py` source + metrics to `results/<key>`
- Global best tracked at `best/train_py` and `best/metadata`
- Per-VRAM-tier bests at `best/tier/<tier>/` (small/medium/large/xl)
- Per-agent bests at `best/agent/<name>`
- Agents periodically `pull_best_config()` (every 5 runs) and adopt if beaten
- Hypotheses and insights published for cross-agent knowledge sharing

**Key Design Decisions:**
- Sanity checks on global best updates (reject val_bpb <= 0, < 0.5, or single-step improvement > 0.1)
- Read-compare-write pattern to minimize race window on best updates
- Previous best metadata preserved for recovery
- Only "keep" results can update global best

**What's relevant to us:**
- The claiming protocol (semantic dedup + TTL expiry) is clever but requires an external service
- We can simplify this significantly for local multi-process coordination
- The "publish everything including failures" philosophy is valuable
- Per-agent branching with shared results tracking is the right model

### 1.2 Karpathy's AgentHub (PR #92 + agenthub repo)

**Repo:** github.com/karpathy/agenthub (Go binary)
**PR #92:** Integration discussion between autoresearch and AgentHub

**Architecture:**
- One Go binary (`agenthub-server`), one SQLite database, one bare git repo on disk
- **Git layer**: Agents push code via git bundles, server validates and unbundles into a bare repo
- **Message board**: Channels, posts, threaded replies for agent coordination
- **Auth**: API key per agent, rate limiting, bundle size limits
- CLI wrapper (`ah`) for agent use

**Key Design Insight — No Main Branch:**
> "A bare git repo + message board, designed for swarms of AI agents working on the same codebase. There's no main branch, no PRs, no merges — just a sprawling DAG of commits going in every direction."

**How agents coordinate:**
- Push commits as git bundles to a shared bare repo
- Browse the DAG: find children, leaves, lineage, diff between commits
- Message board for coordination notes, results, hypotheses
- Each agent independently explores the commit DAG

**PR Discussion Highlights:**
- Exploration vs exploitation tradeoff (maintaining speculative branches that are temporarily worse)
- Evolutionary analogy: no single "main" branch, multiple tracks going independently like a gene pool
- Proposal for stdio Bus (NDJSON/MCP) as inter-agent routing instead of HTTP polling
- Multi-objective optimization (accuracy, parameters, iteration time)

**What's relevant to us:**
- The "no main branch, sprawling DAG" concept fits our multi-draft phase
- Git bundles are overkill for local multi-process — we can use regular branches
- The message board concept can be replaced by a shared results file
- The key insight: agents should be able to fork from ANY commit, not just HEAD

### 1.3 Karpathy's Original autoresearch (program.md)

**The experiment loop (single-agent):**
1. Look at git state (current branch/commit)
2. Modify `train.py` with an experimental idea
3. Git commit
4. Run experiment: `uv run train.py > run.log 2>&1`
5. Read results: `grep "^val_bpb:" run.log`
6. If crashed, read traceback and attempt fix
7. Log results to results.tsv (untracked by git)
8. If improved: keep commit (advance branch)
9. If worse: `git reset --hard` to previous commit
10. LOOP FOREVER — never stop, never ask for confirmation

**Key constraints:**
- Only `train.py` is mutable — `prepare.py` is frozen
- Fixed time budget per experiment (5 min for GPU, 60s for our tabular ML)
- Simplicity criterion: complexity cost vs improvement magnitude
- Results.tsv is untracked (git-ignored) — append-only local log

---

## 2. Our Current Architecture Analysis

### 2.1 What we have

| Module | Role | Multi-agent readiness |
|--------|------|----------------------|
| `loop_helpers.py` | Keep/revert decisions, stagnation detection, strategy shifts | Single-agent only. `LoopState` tracks one agent's state. |
| `runner.py` | Subprocess execution of train.py, metric extraction | Agent-agnostic. Can run in parallel as-is. |
| `drafts.py` | Algorithm family definitions, draft generation, best selection | **Already has parallel exploration concept** — 5 algorithm families evaluated and best selected. |
| `git_ops.py` | Branch creation, commits, reverts | Single-branch model. Would conflict with parallel agents. |
| `experiment_logger.py` | Append-only results.tsv | **Race condition** — multiple processes appending to same file. |
| `scaffold.py` | Creates experiment directory with all files | Single-agent scaffolding. Needs multi-agent extension. |
| `cli.py` | `uv run automl data.csv target metric` | Entry point. Needs `--agents N` flag. |

### 2.2 Natural extension points

1. **`drafts.py` already divides work by algorithm family** — 5 classification families (LogisticRegression, RandomForest, XGBoost, LightGBM, SVM) and 5 regression families. This maps directly to agent assignments.

2. **`git_ops.py` already uses branch-per-run** — `automl/run-{tag}`. Multi-agent extends this to `automl/run-{tag}/agent-{N}`.

3. **`experiment_logger.py` already has append-only TSV** — needs file locking, or switch to per-agent files + merge.

4. **`runner.py` is already isolated** — runs train.py as a subprocess in a specific directory. Multiple runners can operate in parallel on separate working directories.

---

## 3. Proposed Multi-Agent Coordination Architecture

### 3.1 Overview

```
automl swarm data.csv target accuracy --agents 3
    |
    v
+------------------+
|  Swarm Manager   |  (Python process, NOT a Claude agent)
|  swarm.py        |
+------------------+
    |  Spawns N `claude -p` processes
    |  Each gets: own workdir, own branch, assigned algorithm families
    |
    +---> Agent-0 (tree-based: RF, XGB, LGBM)
    |       workdir: .swarm/agent-0/
    |       branch:  automl/run-{tag}/agent-0
    |
    +---> Agent-1 (linear: LogReg, Ridge, ElasticNet, SVM)
    |       workdir: .swarm/agent-1/
    |       branch:  automl/run-{tag}/agent-1
    |
    +---> Agent-2 (ensemble: Stacking, Voting, Blending)
            workdir: .swarm/agent-2/
            branch:  automl/run-{tag}/agent-2
```

### 3.2 Key Design Decisions

**Local-first, no external services.** Unlike autoresearch-at-home (Ensue) or AgentHub (Go server), our coordination uses only the local filesystem and git. This keeps the architecture simple and dependency-free.

**Separate working directories, not separate branches.** Each agent gets a full copy of the experiment directory under `.swarm/agent-N/`. This avoids git lock contention entirely — each agent has its own git repo (or worktree) and operates independently.

**Shared scoreboard file with file locking.** A single `.swarm/scoreboard.tsv` tracks the global best across all agents. Agents read it before each experiment and write to it after. File locking (`fcntl.flock`) prevents corruption.

**Multi-draft becomes multi-agent.** The existing draft phase (evaluate 5 algorithms, pick best) naturally becomes: agent-0 explores tree-based, agent-1 explores linear, etc. After the initial draft phase, agents continue iterating on their best algorithm.

### 3.3 File Layout

```
experiment-iris/
  prepare.py                  # frozen (shared)
  data.csv                    # shared dataset
  program.md                  # agent instructions
  .swarm/
    config.json               # swarm configuration (N agents, assignments, etc.)
    scoreboard.tsv            # global results (file-locked)
    best_train.py             # current global best train.py
    agent-0/
      train.py                # agent's working copy
      run.log                 # agent's last run output
      results.tsv             # agent-local results log
      .git/                   # agent's own git repo (or worktree)
    agent-1/
      ...
    agent-2/
      ...
```

### 3.4 Scoreboard Protocol (File Locking Strategy)

```python
# swarm_coordinator.py

import fcntl
import os
from pathlib import Path

SCOREBOARD = ".swarm/scoreboard.tsv"
LOCKFILE = ".swarm/scoreboard.lock"
HEADER = "agent\tcommit\tmetric_value\telapsed_sec\tstatus\tdescription\ttimestamp\n"

class SwarmScoreboard:
    """Thread-safe, file-locked scoreboard for multi-agent coordination."""

    def __init__(self, swarm_dir: Path):
        self.scoreboard_path = swarm_dir / "scoreboard.tsv"
        self.lock_path = swarm_dir / "scoreboard.lock"
        self.best_train_path = swarm_dir / "best_train.py"

    def read_best(self) -> tuple[float | None, str | None]:
        """Read the current global best score and agent. No lock needed (atomic read)."""
        if not self.scoreboard_path.exists():
            return None, None
        best_score = None
        best_agent = None
        with open(self.scoreboard_path) as f:
            next(f)  # skip header
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
        """Append result to scoreboard. Returns True if this is a new global best."""
        import time
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        with open(self.lock_path, "w") as lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            try:
                # Initialize if needed
                if not self.scoreboard_path.exists():
                    with open(self.scoreboard_path, "w") as f:
                        f.write(HEADER)

                # Read current best
                current_best, _ = self.read_best()

                # Append result
                with open(self.scoreboard_path, "a") as f:
                    f.write(f"{agent_id}\t{commit}\t{metric_value:.6f}\t"
                            f"{elapsed_sec:.1f}\t{status}\t{description}\t{timestamp}\n")

                # Update global best train.py if this is a new best
                is_new_best = False
                if status == "keep" and (current_best is None or metric_value > current_best):
                    is_new_best = True
                    if train_py_source:
                        with open(self.best_train_path, "w") as f:
                            f.write(train_py_source)

                return is_new_best
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
```

### 3.5 Experiment Claiming (Lightweight)

Unlike autoresearch-at-home's semantic dedup (which requires an embedding service), we use a simpler **family-based partitioning** strategy:

1. **Static partitioning during draft phase:** Each agent is assigned non-overlapping algorithm families at spawn time. No claiming needed — work is pre-divided.

2. **Dynamic claiming during iteration phase:** After drafts, agents iterate freely. A lightweight claim file prevents duplicates:

```python
# .swarm/claims/{agent_id}--{description_hash}.json
{
    "agent_id": "agent-0",
    "description": "XGBoost: tune learning_rate from 0.1 to 0.01",
    "claimed_at": "2026-03-13T10:30:00",
    "ttl_seconds": 300
}
```

Claims are checked by scanning `.swarm/claims/` — if a claim exists and is fresher than TTL, skip. This is simple, requires no external service, and handles crash recovery (stale claims expire).

In practice, since each agent works on different algorithm families, collisions are rare. The claiming mechanism is a safety net, not the primary coordination mechanism.

### 3.6 Git Branching Model

**Option A: Git worktrees (recommended)**
```bash
# Main repo stays at experiment root
# Each agent gets a worktree
git worktree add .swarm/agent-0 -b automl/run-{tag}/agent-0
git worktree add .swarm/agent-1 -b automl/run-{tag}/agent-1
git worktree add .swarm/agent-2 -b automl/run-{tag}/agent-2
```

Advantages:
- Single `.git` directory, shared object store
- Each worktree has independent HEAD, index, working tree
- No git lock contention (worktrees are designed for this)
- Branches are visible from any worktree (`git log --all --graph`)
- Easy to compare agent histories

**Option B: Separate clones (fallback)**
```bash
# Clone the repo for each agent
git clone . .swarm/agent-0
git clone . .swarm/agent-1
```

Advantages: Complete isolation, zero lock risk.
Disadvantages: Disk duplication, harder to compare.

**Recommendation:** Use git worktrees. They're purpose-built for this exact use case.

### 3.7 Agent Spawning

Each agent is a `claude -p` process with a tailored prompt:

```python
import subprocess

def spawn_agent(agent_id: int, workdir: Path, families: list[dict],
                dataset_info: str, metric: str, time_budget: int) -> subprocess.Popen:
    """Spawn a Claude Code agent for parallel experimentation."""

    family_names = ", ".join(f["name"] for f in families)

    prompt = f"""You are Agent-{agent_id} in a multi-agent ML experiment swarm.

YOUR ASSIGNED ALGORITHM FAMILIES: {family_names}
YOUR WORKING DIRECTORY: {workdir}
METRIC TO OPTIMIZE: {metric} (higher is better)
TIME BUDGET PER EXPERIMENT: {time_budget} seconds

COORDINATION RULES:
1. Only explore your assigned algorithm families during the draft phase.
2. After drafts, you may iterate freely on your best-performing algorithm.
3. Before each experiment, read .swarm/scoreboard.tsv to see the global best.
4. After each experiment, append your result to .swarm/scoreboard.tsv.
5. If another agent has a better score, read .swarm/best_train.py and consider
   adopting their approach as a starting point.
6. Write your agent-local results to results.tsv in your working directory.

EXPERIMENT LOOP:
1. Read prepare.py and train.py for context.
2. Evaluate each assigned algorithm family (draft phase).
3. Pick the best-performing family.
4. Iterate: modify train.py, commit, run, keep/revert based on metric.
5. Publish results to scoreboard after every experiment.
6. NEVER STOP. Run until interrupted.

Read program.md for full experiment protocol details.
"""

    proc = subprocess.Popen(
        ["claude", "-p", prompt, "--allowedTools",
         "Bash(*)", "Edit(train.py)", "Write(train.py)",
         "Write(results.tsv)", "Read", "Glob", "Grep"],
        cwd=str(workdir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc
```

### 3.8 Swarm Manager

The swarm manager is a simple Python script (not a Claude agent) that:

1. Parses CLI args (`--agents N`)
2. Creates `.swarm/` directory structure
3. Sets up git worktrees for each agent
4. Copies `prepare.py`, `data.csv`, `program.md` into each worktree
5. Generates `train.py` from template for each agent
6. Divides algorithm families across agents
7. Spawns N `claude -p` processes
8. Monitors agent processes (restart on crash, log output)
9. Periodically prints a swarm summary (best score per agent, global best)
10. Handles SIGINT for graceful shutdown

```python
# Rough structure of swarm manager
class SwarmManager:
    def __init__(self, experiment_dir: Path, n_agents: int, task_type: str):
        self.experiment_dir = experiment_dir
        self.n_agents = n_agents
        self.swarm_dir = experiment_dir / ".swarm"
        self.scoreboard = SwarmScoreboard(self.swarm_dir)
        self.agents: list[subprocess.Popen] = []

    def setup(self):
        """Create swarm directory, worktrees, divide work."""
        self.swarm_dir.mkdir(exist_ok=True)
        families = ALGORITHM_FAMILIES[self.task_type]
        assignments = self._divide_families(families, self.n_agents)
        for i in range(self.n_agents):
            agent_dir = self.swarm_dir / f"agent-{i}"
            self._setup_worktree(i, agent_dir)
            self._copy_shared_files(agent_dir)

    def run(self):
        """Spawn all agents and monitor."""
        for i in range(self.n_agents):
            proc = spawn_agent(i, ...)
            self.agents.append(proc)
        self._monitor_loop()

    def _divide_families(self, families, n_agents):
        """Round-robin assignment of algorithm families to agents."""
        assignments = [[] for _ in range(n_agents)]
        for i, family in enumerate(families):
            assignments[i % n_agents].append(family)
        return assignments
```

---

## 4. Integration with Existing Codebase

### 4.1 Multi-draft becomes multi-agent

Current flow (single agent):
```
draft phase:    evaluate 5 families sequentially -> pick best -> iterate
```

Proposed flow (multi-agent):
```
draft phase:    agent-0 evaluates families 0,1  \
                agent-1 evaluates families 2,3   > all parallel -> global best wins
                agent-2 evaluates family 4      /

iteration phase: all agents iterate on global best algorithm
                 (or optionally continue exploring their own best)
```

The `drafts.py` module stays mostly unchanged — each agent just gets a subset of `ALGORITHM_FAMILIES` to evaluate.

### 4.2 LoopState becomes per-agent

`LoopState` already tracks one agent's state. For multi-agent, each agent maintains its own `LoopState` instance. The `SwarmScoreboard` provides the cross-agent coordination that `LoopState` doesn't need to know about.

### 4.3 ExperimentLogger gets file locking

Two options:
1. **Per-agent results.tsv** (recommended): Each agent writes to its own `results.tsv`. The scoreboard handles cross-agent tracking. Simple, no locks needed on the per-agent file.
2. **Shared results.tsv with locking**: Single file, `fcntl.flock` on writes. More complex, less benefit.

### 4.4 GitManager gets worktree support

Add methods to `GitManager`:
```python
def create_worktree(self, path: str, branch: str) -> str:
    """Create a git worktree at path with a new branch."""
    self._run("worktree", "add", path, "-b", branch)
    return branch

def remove_worktree(self, path: str) -> None:
    """Remove a git worktree."""
    self._run("worktree", "remove", path, "--force")
```

---

## 5. Race Conditions and Edge Cases

### 5.1 Scoreboard write contention
**Risk:** Two agents finish experiments at the same time and both append to scoreboard.tsv.
**Mitigation:** `fcntl.flock(LOCK_EX)` on a separate lockfile. Writes are fast (single line append), so lock contention is negligible.

### 5.2 Global best adoption race
**Risk:** Agent-0 reads global best, Agent-1 updates it, Agent-0 adopts stale best.
**Mitigation:** Acceptable. The "stale" best is still a valid starting point. The agent will discover the newer best on its next scoreboard read. This is the same pattern autoresearch-at-home uses.

### 5.3 Git worktree conflicts
**Risk:** Multiple worktrees sharing the same `.git` directory.
**Mitigation:** Git worktrees are designed for this. Each worktree has independent HEAD, index, and working tree. The only shared resource is the object store (which is read-safe for concurrent access).

### 5.4 Agent crash recovery
**Risk:** An agent's `claude -p` process dies mid-experiment.
**Mitigation:** The swarm manager monitors process status. On crash: log the failure, optionally restart the agent from its last committed state. Stale claims auto-expire.

### 5.5 Disk space
**Risk:** N agents x full experiment directory = disk bloat.
**Mitigation:** Git worktrees share the object store, so only working tree files are duplicated. For a typical tabular ML experiment, each working directory is < 10 MB. Even 10 agents = < 100 MB overhead.

---

## 6. Implementation Plan

### Phase 1: Core Infrastructure (new files)
1. **`src/automl/swarm.py`** — SwarmManager class
   - Worktree setup/teardown
   - Algorithm family partitioning
   - Agent process spawning and monitoring
   - Graceful shutdown (SIGINT handler)

2. **`src/automl/swarm_scoreboard.py`** — SwarmScoreboard class
   - File-locked append to scoreboard.tsv
   - Read global best
   - Update best_train.py on new best

3. **`src/automl/swarm_claims.py`** — Lightweight claim files
   - Write/check/expire claim files in `.swarm/claims/`
   - TTL-based expiry

### Phase 2: Integration (modify existing files)
4. **`src/automl/git_ops.py`** — Add `create_worktree()`, `remove_worktree()`
5. **`src/automl/cli.py`** — Add `--agents N` flag, `swarm` subcommand
6. **`src/automl/scaffold.py`** — Add `.swarm/` directory creation when `--agents` > 1
7. **`src/automl/templates/`** — Add swarm-specific program.md variant with coordination instructions

### Phase 3: Agent Protocol
8. **`src/automl/templates/swarm_program.md`** — Agent instructions including:
   - Assigned algorithm families
   - Scoreboard read/write protocol
   - Global best adoption rules
   - Claim protocol for iteration phase

### Phase 4: Testing
9. **Unit tests** for SwarmScoreboard (concurrent writes, locking)
10. **Unit tests** for SwarmManager (family partitioning, worktree setup)
11. **Integration test** — 2-agent swarm on a small dataset, verify both produce results

### Estimated Effort
- Phase 1: ~3 new files, ~300 lines
- Phase 2: ~100 lines of modifications across 4 files
- Phase 3: ~1 template file
- Phase 4: ~200 lines of tests
- **Total: ~600 lines of code + tests**

---

## 7. Summary of Key Differences from Prior Art

| Aspect | autoresearch-at-home | AgentHub | Our Design |
|--------|---------------------|----------|------------|
| Coordination | External service (Ensue) | Go server + SQLite | Local filesystem + fcntl |
| Git model | Separate forks per agent | Shared bare repo, git bundles | Git worktrees (shared .git) |
| Claiming | Semantic dedup via embeddings | Message board | Family partitioning + TTL claim files |
| Result sharing | JSON-RPC to shared memory | Push git bundles + post messages | File-locked scoreboard.tsv |
| Scope | Distributed across internet | Distributed across internet | Local machine, N parallel processes |
| Dependencies | requests, Ensue API | Go binary, SQLite | None (stdlib only: fcntl, subprocess) |
| Complexity | ~600 lines (coordinator.py) | ~1000 lines (Go server) | ~300 lines (swarm.py + scoreboard) |

Our design is deliberately simpler because we operate on a single machine. The multi-machine distributed case (autoresearch-at-home's territory) is a future extension — and if we ever need it, the scoreboard protocol can be swapped from file-locked TSV to a network service without changing the agent protocol.
