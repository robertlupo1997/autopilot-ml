# Swarm Mode Guide

Run N parallel Claude Code agents, each in its own git worktree, coordinating via a file-locked scoreboard.

## Usage

```bash
# 5 agents, default budget
mlforge data.csv "predict price" --swarm --n-agents 5

# 3 agents with explicit budget and multi-draft starts
mlforge data.csv "predict price" --swarm --n-agents 3 --budget-usd 15 --enable-drafts
```

## How It Works

1. **Worktree creation.** mlforge creates N git worktrees under `.swarm/agent-{0,1,...}`. Each worktree is a full copy of the workspace where one agent operates independently.

2. **Budget splitting.** The total budget is divided evenly across agents. `--budget-usd 15 --n-agents 3` gives each agent $5.

3. **Parallel execution.** mlforge spawns N `claude -p` subprocesses, one per worktree. All agents run concurrently.

4. **Independent work.** Each agent follows the same `CLAUDE.md` protocol but makes its own modeling decisions. Agents do not communicate during a run.

5. **Scoreboard publishing.** When an agent achieves a result, it writes a row to `.swarm/scoreboard.tsv`. Writes are atomic -- the file is locked with `fcntl` to prevent corruption.

6. **Winner selection.** After all agents complete, mlforge reads the scoreboard, verifies the best result, and promotes it.

## Scoreboard Format

TSV file at `.swarm/scoreboard.tsv`:

| Column | Description |
|---|---|
| `agent` | Agent index (0, 1, 2, ...) |
| `commit` | Git commit hash of the result |
| `metric_value` | Numeric score on the target metric |
| `elapsed_sec` | Wall-clock seconds since the agent started |
| `status` | `running`, `completed`, or `failed` |
| `description` | Short text describing the approach |
| `timestamp` | ISO 8601 timestamp |

File locking uses `fcntl.flock` (LOCK_EX) for atomic writes.

## Budget Inheritance

Each agent receives `total_budget / n_agents`. If one agent finishes early, its unused budget is not redistributed.

## Combining with Multi-Draft

```bash
mlforge data.csv "predict price" --swarm --n-agents 3 --enable-drafts
```

Each agent independently runs the multi-draft strategy (3-5 diverse initial solutions, pick best, iterate). This means broad exploration across both starting points and iteration paths.

## When to Use Swarm

- **Large budget** -- explore multiple strategies simultaneously
- **Faster wall-clock convergence** -- N agents in parallel finish sooner than one agent running N times longer
- **Diversity** -- different agents may find different optima; the scoreboard picks the global best

## When NOT to Use Swarm

- **Small budgets** (under ~$5) -- overhead of N agents isn't worth it
- **Simple datasets** -- single agent converges in a few iterations
- **Disk-constrained environments** -- each worktree is a near-full copy of the workspace

## Resource Requirements

| Resource | Requirement |
|---|---|
| Disk space | ~N times the workspace size (for worktrees) |
| API budget | Total budget split across N agents |
| CPU / RAM | N concurrent `claude` processes plus model training |

## Output

After all agents finish:

1. Best row in `scoreboard.tsv` is identified
2. Winning agent's commit is verified by re-running evaluation
3. Winning result is promoted to `artifacts/`
4. Worktrees under `.swarm/` are cleaned up

```
artifacts/
  best_model.joblib     # or best_model.pt, best_adapter/, depending on domain
  metadata.json         # includes which agent won and scoreboard summary
  predictions.csv
```
