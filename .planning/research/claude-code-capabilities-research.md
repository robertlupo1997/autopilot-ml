# Claude Code Capabilities Research — AutoML v1 Expansion

## Research Date: 2026-03-10

## Summary of Findings

### 1. Hooks (21 Events, 4 Types)

**High-value for AutoML:**
- `PreToolUse` — Enforce mutable zone constraints (block edits to frozen files like prepare.py)
- `PostToolUse` — Auto-log experiment commands to audit trail
- `Stop` — Verify tests pass before agent stops (agent-type hook runs pytest)
- `SessionStart(compact)` — Re-inject critical context after auto-compaction

**Hook types:** command (shell), http (webhook), prompt (LLM judgment), agent (multi-turn with tools)

**Key insight:** Hooks provide *hard enforcement* of constraints that CLAUDE.md only advises. For mutable zones, use PreToolUse hooks to deny edits to frozen files.

### 2. CLAUDE.md & .claude/rules/

**Key patterns for AutoML:**
- Root CLAUDE.md: project overview, quick start, code style (~100 lines max)
- `.claude/rules/ml-phases.md`: path-specific rules for src/ (loads only when editing src/)
- `.claude/rules/safety.md`: autonomous loop constraints
- `@path` imports: reference PROJECT.md without duplicating content
- **Sub-agents do NOT inherit parent CLAUDE.md** — must use skills or explicit injection

**Key insight:** The scaffolded project's CLAUDE.md is the primary control mechanism for the autonomous agent. It should contain experiment rules, not just code style.

### 3. Sub-Agents & Agent SDK

**Sub-agent capabilities:**
- Built-in types: Explore (fast, read-only), Plan (research), General-purpose (all tools)
- Custom sub-agents via `.claude/agents/*.md` with tool restrictions, hooks, memory
- Worktree isolation: each sub-agent gets isolated git worktree
- **Cannot nest**: sub-agents can't spawn sub-agents (max 1 level deep)
- Agent Teams: parallel execution with multiple Claude Code sessions

**Agent SDK (Python/TypeScript):**
- Programmatic interface to Claude Code's agentic loop
- `query()` function with streaming, tool restrictions, hooks
- Session management and resumption
- Could replace runner.py for orchestration

**Key insight:** Agent SDK could be the backbone of the autonomous loop. Instead of runner.py shelling out to `claude -p`, use the SDK directly for programmatic control with structured outputs.

### 4. MCP Servers

**Useful for AutoML:**
- Custom MCP server could expose experiment results, metrics history
- DuckDB MCP for querying results.tsv as SQL
- GitHub MCP for PR creation from experiment results
- `.mcp.json` in scaffolded project for team sharing

**Key insight:** MCP servers are more relevant for v2+ (connecting to data sources, APIs). For v1, the CLI/SDK approach is simpler and sufficient.

### 5. Tool Use & Advanced Features

**Critical for autonomous loop:**
- `claude -p` headless mode: non-interactive execution with JSON output
- `--allowedTools`: pre-approve specific commands for safe autonomy
- `--max-turns`: limit iterations per invocation
- `--max-budget-usd`: spending cap per run
- `--output-format json`: structured output for programmatic parsing
- `--json-schema`: validate agent output structure
- Context compaction: automatic at ~80% capacity, customizable
- Sandboxing: OS-level filesystem/network isolation

**Key insight:** The existing runner.py approach (shell out to `claude -p`) is actually well-aligned with how Claude Code is designed to work. Enhance it with `--allowedTools`, `--max-turns`, and `--output-format json`.

## Prioritized Opportunities for v1 Expansion

### P0 — Must Have (Direct value, low effort)
1. **Hooks for mutable zone enforcement** — Replace advisory CLAUDE.md constraints with hard PreToolUse blocks
2. **Enhanced CLAUDE.md template** — Better autonomous loop instructions in scaffolded projects
3. **`--allowedTools` integration** — Safe autonomous execution without `--dangerously-skip-permissions`
4. **`--max-turns` and `--max-budget-usd`** — Resource limits for autonomous runs

### P1 — Should Have (Significant value, moderate effort)
5. **Agent SDK integration** — Replace shell-based runner with programmatic SDK orchestration
6. **Structured JSON output** — Parse agent results programmatically instead of grep/regex
7. **Session resumption** — Continue experiments across context resets
8. **Stop hook for verification** — Agent-type hook runs tests before declaring "done"

### P2 — Nice to Have (Future value, higher effort)
9. **Custom sub-agents** — Specialized agents for different experiment phases
10. **Worktree isolation** — Each draft runs in isolated git worktree
11. **MCP server for results** — Query experiment history via MCP
12. **Agent Teams** — Parallel draft evaluation with multiple Claude instances

## Architecture Recommendations

### Current Flow (v1.0)
```
CLI → scaffold project → user runs `claude -p "NEVER STOP"` manually → agent iterates
```

### Enhanced Flow (v1.1)
```
CLI → scaffold project (with hooks, CLAUDE.md, permissions) →
  runner invokes `claude -p` with --allowedTools, --max-turns, --output-format json →
  hooks enforce mutable zones, log experiments, verify tests →
  structured output parsed for metrics tracking
```

### Future Flow (v2.0 - Agent SDK)
```
CLI → scaffold project →
  Agent SDK orchestrates loop programmatically →
  sub-agents handle drafts in worktrees →
  structured metrics, session resumption, budget controls
```
