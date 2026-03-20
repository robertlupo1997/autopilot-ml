# Phase 8: Register Domain Plugins + Swarm CLI - Research

**Researched:** 2026-03-20
**Domain:** Plugin registration, CLI extension, swarm integration
**Confidence:** HIGH

## Summary

Phase 8 is a wiring/integration phase. All the components already exist -- DeepLearningPlugin, FineTuningPlugin, SwarmManager, SwarmScoreboard, and verify_best_result are fully implemented and tested. The gap is that these components are not reachable from the user-facing entry points: scaffold.py only auto-registers the tabular plugin, cli.py has no --swarm/--n-agents flags, and SwarmManager.run() never calls verify_best_result().

The work is straightforward: (1) add auto-registration functions for DL and FT plugins in scaffold.py mirroring the existing `_ensure_tabular_registered()` pattern, (2) add --swarm and --n-agents CLI flags with a swarm code path in main(), (3) wire verify_best_result() into SwarmManager.run() after agents complete, and (4) add tests for each integration point.

**Primary recommendation:** Follow the exact pattern of `_ensure_tabular_registered()` for DL/FT plugins, add a swarm branch in cli.py that bypasses RunEngine and uses SwarmManager directly, and call verify_best_result() at the end of SwarmManager.run() before returning results.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DL-01 | Deep learning plugin handles image/text/custom training with PyTorch | DeepLearningPlugin fully implemented in `src/mlforge/deeplearning/__init__.py` -- needs registration in scaffold.py |
| DL-02 | Plugin manages GPU utilization, memory limits, training time budgets | prepare.py has get_device_info(), train template has TIME_BUDGET_SEC -- needs plugin reachable via get_plugin() |
| DL-03 | Plugin supports LR scheduling, early stopping, gradient clipping as protocol rules | template_context() returns 10 DL rules including all three -- needs plugin registered |
| DL-04 | Plugin generates domain-specific CLAUDE.md protocol | template_context() implemented -- needs registration so scaffold_experiment() can call it |
| DL-05 | Fixed time budget per training run prevents runaway GPU consumption | dl_train.py.j2 has TIME_BUDGET_SEC with wall-clock break -- needs plugin registered |
| FT-01 | Fine-tuning plugin handles LoRA/QLoRA fine-tuning via PEFT/TRL | FineTuningPlugin fully implemented in `src/mlforge/finetuning/__init__.py` -- needs registration |
| FT-02 | Plugin manages VRAM allocation, quantization config, LoRA rank/alpha | prepare.py has get_vram_info(), template renders BitsAndBytesConfig -- needs registration |
| FT-03 | Plugin supports perplexity, ROUGE, task-specific eval | validate_config checks valid metrics, ft_train.py.j2 has eval -- needs registration |
| FT-04 | Plugin generates domain-specific CLAUDE.md protocol | template_context() returns 10 FT rules -- needs registration |
| FT-05 | Plugin handles dataset formatting and train/eval splits | prepare.py has format_dataset() and create_train_eval_split() -- needs registration |
| SWARM-01 | Swarm mode spawns parallel agents in git worktrees | SwarmManager.setup() + run() implemented -- needs CLI entry point (--swarm flag) |
| SWARM-02 | File-locked scoreboard coordinates best result across agents | SwarmScoreboard fully implemented with fcntl.LOCK_EX -- needs CLI wiring |
| SWARM-03 | Budget inheritance prevents spawn explosion | create_child_configs() splits budget evenly, children have no swarm -- needs CLI wiring |
| SWARM-04 | Verification agent checks metric claims against holdout | verify_best_result() implemented -- needs to be called in SwarmManager.run() |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mlforge.plugins | local | Plugin registry (register_plugin, get_plugin) | Existing architecture, DomainPlugin Protocol |
| mlforge.scaffold | local | Experiment directory scaffolding | Existing auto-registration pattern |
| mlforge.cli | local | CLI entry point with argparse | Existing CLI structure |
| mlforge.swarm | local | SwarmManager + SwarmScoreboard | Existing implementation |
| mlforge.swarm.verifier | local | verify_best_result() | Existing implementation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| argparse | stdlib | CLI flag parsing | Adding --swarm and --n-agents flags |
| unittest.mock | stdlib | Test mocking | Testing CLI swarm path without real agents |

## Architecture Patterns

### Pattern 1: Auto-Registration in scaffold.py
**What:** Lazy plugin registration on first use, matching `_ensure_tabular_registered()`
**When to use:** When scaffold_experiment() is called with domain="deeplearning" or domain="finetuning"

**Existing pattern to follow:**
```python
# Source: src/mlforge/scaffold.py lines 54-61
def _ensure_tabular_registered() -> None:
    """Register the tabular plugin if not already registered."""
    try:
        get_plugin("tabular")
    except KeyError:
        from mlforge.tabular import TabularPlugin
        register_plugin(TabularPlugin())
```

**New functions to add:**
```python
def _ensure_deeplearning_registered() -> None:
    try:
        get_plugin("deeplearning")
    except KeyError:
        from mlforge.deeplearning import DeepLearningPlugin
        register_plugin(DeepLearningPlugin())

def _ensure_finetuning_registered() -> None:
    try:
        get_plugin("finetuning")
    except KeyError:
        from mlforge.finetuning import FineTuningPlugin
        register_plugin(FineTuningPlugin())
```

**Critical change:** scaffold_experiment() currently hardcodes `_ensure_tabular_registered()` on line 95. This must be replaced with a domain-aware dispatcher that calls the correct registration function based on `config.domain`.

### Pattern 2: CLI Swarm Branch
**What:** New --swarm and --n-agents flags that route to SwarmManager instead of RunEngine
**When to use:** User wants parallel agent exploration

**Implementation approach:**
```python
# In cli.py argparse setup
parser.add_argument("--swarm", action="store_true", help="Enable swarm mode")
parser.add_argument("--n-agents", type=int, default=3, help="Number of swarm agents")

# In main() after scaffold:
if args.swarm:
    from mlforge.swarm import SwarmManager
    sm = SwarmManager(config=config, experiment_dir=target_dir, n_agents=args.n_agents)
    sm.setup()
    try:
        results = sm.run()
        # Print swarm summary
    finally:
        sm.teardown()
    return 0
else:
    # Existing RunEngine path
```

### Pattern 3: Verifier Wiring in SwarmManager.run()
**What:** Call verify_best_result() after all agents complete, before returning results
**When to use:** Always at end of SwarmManager.run()

**Implementation approach:**
```python
# In SwarmManager.run(), after waiting for all processes:
from mlforge.swarm.verifier import verify_best_result

# ... existing code that waits for processes ...
best_score, best_agent = self.scoreboard.read_best()
all_results = self.scoreboard.read_all()

# NEW: Verify best result
verification = verify_best_result(
    self.experiment_dir, self.scoreboard
)

return {
    "agents": self.n_agents,
    "best_score": best_score,
    "best_agent": best_agent,
    "results": all_results,
    "verification": verification,  # NEW
}
```

### Anti-Patterns to Avoid
- **Eager imports of heavy deps:** DL/FT plugins use lazy imports (torch, peft, trl imported inside methods). Registration functions must use lazy `from mlforge.deeplearning import DeepLearningPlugin` inside the function body, not at module level.
- **Hardcoded tabular assumption:** scaffold.py line 95 calls `_ensure_tabular_registered()` unconditionally. Must dispatch based on config.domain.
- **Swarm + Resume conflict:** The CLI swarm path should NOT support --resume (swarm mode is stateless from the CLI perspective). Add validation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Plugin registration | Custom loader | Existing `register_plugin()` + `get_plugin()` | Already handles Protocol validation |
| Budget splitting | Manual division | `SwarmManager.create_child_configs()` | Already handles even splitting via `dataclasses.replace()` |
| Worktree management | Custom git commands | `SwarmManager.setup()` + `teardown()` | Already handles creation, removal, crash recovery |
| Metric verification | Custom eval logic | `verify_best_result()` | Already handles worktree checkout, eval, comparison, cleanup |

## Common Pitfalls

### Pitfall 1: Forgetting to Dispatch Registration by Domain
**What goes wrong:** scaffold_experiment() only calls `_ensure_tabular_registered()`, so `config.domain="deeplearning"` hits KeyError at `get_plugin(config.domain)`.
**Why it happens:** The original code assumed only tabular would ever be used.
**How to avoid:** Replace the hardcoded call with a domain-to-registration-function mapping.
**Warning signs:** KeyError on `get_plugin('deeplearning')` or `get_plugin('finetuning')`.

### Pitfall 2: Module-Level Heavy Imports in Registration
**What goes wrong:** If `from mlforge.deeplearning import DeepLearningPlugin` is at module level in scaffold.py, it transitively imports torch at import time.
**Why it happens:** scaffold.py is imported by cli.py which runs on every invocation.
**How to avoid:** Keep imports inside the `_ensure_*_registered()` functions (lazy pattern already established).
**Warning signs:** ImportError for torch when running `mlforge data.csv "predict price"` without GPU deps installed.

### Pitfall 3: Swarm Mode Without Git Init
**What goes wrong:** SwarmManager.setup() calls `git worktree add` which requires an initialized git repo.
**Why it happens:** CLI swarm path might try to run SwarmManager before git is initialized.
**How to avoid:** Ensure git branch creation happens before SwarmManager.setup(), same as the existing RunEngine path.

### Pitfall 4: verify_best_result() Failure Crashing SwarmManager.run()
**What goes wrong:** If verification fails (eval script errors, no results), SwarmManager.run() could crash.
**Why it happens:** verify_best_result() returns None for empty scoreboards and includes error info for failed evals, but unhandled exceptions could propagate.
**How to avoid:** Wrap verify_best_result() in try/except, set verification to None on failure. The function already handles the empty-scoreboard case (returns None).

### Pitfall 5: --n-agents Without --swarm
**What goes wrong:** User passes `--n-agents 5` but forgets `--swarm`, so the flag is silently ignored.
**How to avoid:** Either make --n-agents require --swarm, or print a warning if --n-agents is set without --swarm.

## Code Examples

### Example 1: Domain-Aware Registration Dispatcher
```python
# In scaffold.py
_REGISTRATION_FUNCTIONS = {
    "tabular": _ensure_tabular_registered,
    "deeplearning": _ensure_deeplearning_registered,
    "finetuning": _ensure_finetuning_registered,
}

def _ensure_plugin_registered(domain: str) -> None:
    """Register the plugin for the given domain if not already registered."""
    reg_fn = _REGISTRATION_FUNCTIONS.get(domain)
    if reg_fn is not None:
        reg_fn()
```

Then in scaffold_experiment(), replace line 95:
```python
# OLD: _ensure_tabular_registered()
# NEW:
_ensure_plugin_registered(config.domain)
```

### Example 2: CLI Swarm Path
```python
if args.swarm:
    from mlforge.swarm import SwarmManager
    manager = SwarmManager(
        config=config,
        experiment_dir=target_dir,
        n_agents=args.n_agents,
    )
    manager.setup()
    try:
        results = manager.run()
        print(
            f"\nSwarm complete: {results['agents']} agents, "
            f"best={results['best_score']} (agent {results['best_agent']})"
        )
        if results.get("verification"):
            v = results["verification"]
            status = "VERIFIED" if v.get("match") else "MISMATCH"
            print(f"Verification: {status} (claimed={v['claimed_metric']}, "
                  f"verified={v.get('verified_metric', 'N/A')})")
    finally:
        manager.teardown()
    return 0
```

### Example 3: Verifier Wiring in SwarmManager.run()
```python
# At end of SwarmManager.run(), before return:
try:
    verification = verify_best_result(self.experiment_dir, self.scoreboard)
except Exception:
    verification = None

return {
    "agents": self.n_agents,
    "best_score": best_score,
    "best_agent": best_agent,
    "results": all_results,
    "verification": verification,
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Only tabular plugin registered | Domain-aware registration dispatch | Phase 8 | Enables DL and FT plugins |
| No swarm CLI entry point | --swarm / --n-agents flags | Phase 8 | Users can run parallel agents from CLI |
| No metric verification | verify_best_result() in SwarmManager.run() | Phase 8 | Catches metric inflation |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml (existing) |
| Quick run command | `python -m pytest tests/mlforge/ -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DL-01 to DL-05 | `get_plugin('deeplearning')` returns DeepLearningPlugin after scaffold | unit | `python -m pytest tests/mlforge/test_scaffold.py -x -k deeplearning` | Needs new tests |
| FT-01 to FT-05 | `get_plugin('finetuning')` returns FineTuningPlugin after scaffold | unit | `python -m pytest tests/mlforge/test_scaffold.py -x -k finetuning` | Needs new tests |
| SWARM-01 to SWARM-03 | CLI --swarm flag invokes SwarmManager | unit | `python -m pytest tests/mlforge/test_cli.py -x -k swarm` | Needs new tests |
| SWARM-04 | verify_best_result() called in SwarmManager.run() | unit | `python -m pytest tests/mlforge/test_swarm.py -x -k verify` | Needs new tests |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/mlforge/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
None -- existing test infrastructure (pytest, conftest.py fixtures, mock patterns) covers all needs. New test functions will be added to existing test files.

## Open Questions

None -- all components are implemented and well-tested. This is purely a wiring/integration phase.

## Sources

### Primary (HIGH confidence)
- `src/mlforge/plugins.py` -- Plugin registry implementation (register_plugin, get_plugin, DomainPlugin Protocol)
- `src/mlforge/scaffold.py` -- Existing auto-registration pattern (_ensure_tabular_registered)
- `src/mlforge/cli.py` -- Existing CLI structure, argparse setup, main() flow
- `src/mlforge/swarm/__init__.py` -- SwarmManager implementation (setup, run, teardown, _build_agent_command)
- `src/mlforge/swarm/verifier.py` -- verify_best_result() implementation
- `src/mlforge/deeplearning/__init__.py` -- DeepLearningPlugin (name="deeplearning", scaffold, template_context, validate_config)
- `src/mlforge/finetuning/__init__.py` -- FineTuningPlugin (name="finetuning", scaffold, template_context, validate_config)
- `tests/mlforge/` -- Existing test patterns for plugins, scaffold, CLI, swarm

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components exist, just need wiring
- Architecture: HIGH -- patterns established by _ensure_tabular_registered(), CLI argparse, SwarmManager.run()
- Pitfalls: HIGH -- straightforward integration with well-understood edge cases

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable -- internal codebase patterns)
