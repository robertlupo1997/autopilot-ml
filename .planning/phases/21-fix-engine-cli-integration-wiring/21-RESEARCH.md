# Phase 21: Fix Engine + CLI Integration Wiring - Research

**Researched:** 2026-03-21
**Domain:** Integration bug fixes in engine.py and cli.py
**Confidence:** HIGH

## Summary

Phase 21 fixes four integration bugs identified in the v1.0 milestone audit (INT-DL-BASELINE, INT-FT-DIAGNOSTICS, INT-DL-DRAFT-FALLBACK, INT-MAX-TURNS). All four bugs are located in exactly two files: `src/mlforge/engine.py` and `src/mlforge/cli.py`. Each bug is a small, well-scoped wiring issue -- a missing key, a missing set member, a wrong fallback, or a missing CLI flag.

The critical finding on INT-MAX-TURNS is that the `claude` CLI has **no `--max-turns` flag**. The only budget-related flag is `--max-budget-usd`. The Phase 6 decision explicitly said "Keep max_turns_per_experiment in Config for forward compatibility, stop passing to CLI." However, the audit identified this as a gap. The resolution must use an alternative mechanism: either include max_turns as a system prompt instruction, or accept that `--max-budget-usd` (already wired) is the effective guardrail. Given the claude CLI's available flags, the best approach is to add `max_turns_per_experiment` as an instruction in the system prompt appended to the claude command.

**Primary recommendation:** Fix all four bugs with targeted edits (3-10 lines each) in engine.py and cli.py, plus corresponding tests.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DL-04 | DL plugin generates domain-specific CLAUDE.md protocol | cli.py must set `dataset_path` for DL domain so baselines fire |
| GUARD-05 | Cost tracking per experiment with budget cap enforcement | max_turns guardrail prevents unbounded experiment duration |
| INTL-04 | Branch-on-stagnation after consecutive reverts | DL baseline gate must be operative for meaningful stagnation detection |
| FT-03 | FT evaluation metrics for generative tasks | `sft` must route to correct diagnostics path |
| INTL-05 | Multi-draft diverse initial solutions | DL expert mode draft must use correct task key fallback |
| DL-01 | DL plugin handles image/text classification | DL draft fallback fix enables correct model class rendering |
| INTL-01 | Baseline establishment before agent experiments | DL baseline gate fix enables baseline computation |
| CORE-08 | Experiment journal accumulates structured knowledge | max_turns ensures experiments terminate to write journal entries |
| GUARD-02 | Resource guardrails enforce caps | max_turns as system prompt instruction adds turn-level guardrail |
</phase_requirements>

## Standard Stack

No new libraries needed. All fixes are within existing code.

### Core Files
| File | Lines to Change | Bug |
|------|----------------|-----|
| `src/mlforge/cli.py` | ~165 | Must set `plugin_settings["dataset_path"]` for DL domain |
| `src/mlforge/engine.py` | ~39 | Add `"sft"` to `_CLASSIFICATION_TASKS` frozenset |
| `src/mlforge/engine.py` | ~320 | Use domain-aware task fallback instead of hardcoded `"classification"` |
| `src/mlforge/engine.py` | ~163-176 | Add max_turns instruction to system prompt or subprocess args |

### Test Files
| File | Purpose |
|------|---------|
| `tests/mlforge/test_cli.py` | CLI integration tests (existing, add DL dataset_path test) |
| `tests/mlforge/test_engine.py` | Engine tests (existing, add sft diagnostics + draft fallback + max_turns tests) |

## Architecture Patterns

### Bug 1: DL Baseline Gate (INT-DL-BASELINE)

**What's wrong:** `cli.py:165` sets `plugin_settings["csv_path"]` in simple mode, but `engine._compute_dl_baselines()` -> `_load_dl_labels()` reads `plugin_settings.get("dataset_path")`. For DL domain, the data source is a directory (image folders) or CSV, accessed via `dataset_path` key. The CLI never sets this key.

**Fix location:** `cli.py` simple mode block (~line 165). After setting `csv_path`, also set `dataset_path` to `dataset_path.name` when domain is `deeplearning`. However, the simple mode profiler only runs for tabular-like CSVs. For DL, the user likely provides a directory path, not a CSV. The fix should set `dataset_path` in `plugin_settings` for **all domains** (or at least DL), pointing to the dataset filename/dirname.

**Precise fix:** After line 165, add:
```python
config.plugin_settings["dataset_path"] = dataset_path.name
```
This ensures `_load_dl_labels()` finds the dataset. Since `csv_path` and `dataset_path` serve different purposes per domain (tabular uses csv_path, DL uses dataset_path), setting both is safe.

For expert mode (when `--metric` is explicitly provided and profiling is skipped), the `dataset_path` should also be set. This means the `dataset_path` setting should happen **outside** the profiling try/except block.

### Bug 2: FT Diagnostics Routing (INT-FT-DIAGNOSTICS)

**What's wrong:** `engine.py:39` defines `_CLASSIFICATION_TASKS = frozenset({"classification", "image_classification", "text_classification", "custom"})`. The FT task type `"sft"` is not in this set, so FT diagnostics fall through to the `else` branch (regression diagnostics). For SFT tasks, the diagnostics compute bias/worst-predictions on loss values, which is semantically wrong -- SFT is closer to classification (token prediction).

**Fix:** Add `"sft"` to `_CLASSIFICATION_TASKS`:
```python
_CLASSIFICATION_TASKS: frozenset[str] = frozenset({
    "classification", "image_classification", "text_classification", "custom", "sft",
})
```

### Bug 3: DL Expert Draft Fallback (INT-DL-DRAFT-FALLBACK)

**What's wrong:** `engine.py:320` reads `task = self.config.plugin_settings.get("task", "classification")`. In expert mode (no profiler), `task` defaults to `"classification"`. But DL family entries use keys like `"image_classification"`, `"text_classification"`, `"custom"` -- NOT `"classification"`. So `family_info.get(task, family_name)` falls back to the raw family_name string (e.g., `"resnet"`) instead of the model class (e.g., `"resnet50"`).

**Fix:** Use domain-aware default task. When domain is `deeplearning`, default to `"image_classification"`. When domain is `finetuning`, default to `"sft"`:
```python
_DOMAIN_DEFAULT_TASK = {
    "tabular": "classification",
    "deeplearning": "image_classification",
    "finetuning": "sft",
}
# In _run_draft_phase:
task = self.config.plugin_settings.get(
    "task",
    _DOMAIN_DEFAULT_TASK.get(self.config.domain, "classification"),
)
```

This same pattern should also apply to `_run_diagnostics()` line 437 which has the same hardcoded `"classification"` fallback.

### Bug 4: max_turns Guardrail (INT-MAX-TURNS)

**What's wrong:** `config.max_turns_per_experiment` (default 30) is never passed to the claude subprocess command. The claude CLI has NO `--max-turns` flag (confirmed by `claude --help` output).

**Available options:**
1. Add max_turns instruction to the system prompt appended via `--append-system-prompt` -- tells the agent to stop after N turns
2. Accept `--max-budget-usd` as the effective guardrail (already wired)
3. Use `per_experiment_timeout_sec` as the effective guardrail (already wired)

**Recommended fix:** Inject a max_turns instruction into the system prompt. When `config.max_turns_per_experiment` is set, append to the `system_prompt` string:
```python
if self.config.max_turns_per_experiment:
    system_prompt += f"\n\nIMPORTANT: You MUST complete your work within {self.config.max_turns_per_experiment} tool-use turns. After that limit, wrap up and report your results."
```

This is a protocol-level enforcement (consistent with the project's "protocol-first" philosophy from v3.0), backed by the hard `--max-budget-usd` financial guardrail.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Domain-aware defaults | Switch/if chains in every method | Module-level `_DOMAIN_DEFAULT_TASK` dict | Single source of truth, reusable |
| Turn limiting | Custom subprocess wrapper | System prompt instruction + existing budget guard | Claude CLI has no --max-turns flag |

## Common Pitfalls

### Pitfall 1: Setting dataset_path Only in Simple Mode
**What goes wrong:** Expert mode (explicit `--metric`) skips profiling entirely, so no `plugin_settings` keys get set. DL runs in expert mode would still lack `dataset_path`.
**How to avoid:** Set `dataset_path` unconditionally for all domains, outside the profiling try/except block. It should be `dataset_path.name` (filename only, since scaffold copies the dataset).

### Pitfall 2: Breaking Existing test_no_max_turns_flag Test
**What goes wrong:** `tests/mlforge/test_engine.py:609` has `test_no_max_turns_flag` that asserts `--max-turns` is NOT in the subprocess command. If we add max_turns to the system prompt, this test still passes (since we're not adding a `--max-turns` flag). But we need to ensure the system prompt approach doesn't break the assertion.
**How to avoid:** The fix adds to the system prompt string, not to the CLI command args. Existing test remains valid.

### Pitfall 3: _run_diagnostics Has Same Fallback Bug
**What goes wrong:** `engine.py:437` has `task = self.config.plugin_settings.get("task", "classification")`. This is the same hardcoded fallback as the draft bug. For DL expert mode, diagnostics would route to classification path (which happens to be correct for DL), but using the domain-aware default is more robust.
**How to avoid:** Apply the same `_DOMAIN_DEFAULT_TASK` fix to `_run_diagnostics()` as well.

## Code Examples

### Fix 1: DL dataset_path in CLI (cli.py)

```python
# After line 128 (config = Config(domain=args.domain)), add dataset_path
# for all domains unconditionally:
config.plugin_settings["dataset_path"] = dataset_path.name

# This goes BEFORE the profiling block so both simple and expert modes get it.
```

### Fix 2: Add sft to _CLASSIFICATION_TASKS (engine.py)

```python
_CLASSIFICATION_TASKS: frozenset[str] = frozenset({
    "classification", "image_classification", "text_classification", "custom", "sft",
})
```

### Fix 3: Domain-aware task fallback (engine.py)

```python
_DOMAIN_DEFAULT_TASK: dict[str, str] = {
    "tabular": "classification",
    "deeplearning": "image_classification",
    "finetuning": "sft",
}

# In _run_draft_phase (line 320):
task = self.config.plugin_settings.get(
    "task",
    _DOMAIN_DEFAULT_TASK.get(self.config.domain, "classification"),
)

# In _run_diagnostics (line 437):
task = self.config.plugin_settings.get(
    "task",
    _DOMAIN_DEFAULT_TASK.get(self.config.domain, "classification"),
)
```

### Fix 4: max_turns system prompt instruction (engine.py)

```python
# In _run_one_experiment, after reading system_prompt from CLAUDE.md:
if self.config.max_turns_per_experiment:
    turns_instruction = (
        f"\n\nIMPORTANT: Complete your work within "
        f"{self.config.max_turns_per_experiment} tool-use turns. "
        f"After that limit, wrap up and report your metric value."
    )
    if system_prompt:
        system_prompt += turns_instruction
    else:
        system_prompt = turns_instruction.strip()
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `python3 -m pytest tests/mlforge/test_engine.py tests/mlforge/test_cli.py -x -q` |
| Full suite command | `python3 -m pytest tests/mlforge/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DL-04 / INTL-01 | CLI sets dataset_path for DL domain | unit | `python3 -m pytest tests/mlforge/test_cli.py -x -k dataset_path_dl` | No - Wave 0 |
| FT-03 / INTL-05 | sft routes to classification diagnostics | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k sft_diagnostics` | No - Wave 0 |
| DL-01 / INTL-05 | DL expert draft uses domain-aware fallback | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k draft_dl_fallback` | No - Wave 0 |
| GUARD-02 / CORE-08 | max_turns instruction in system prompt | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k max_turns_prompt` | No - Wave 0 |
| GUARD-05 | dataset_path set in expert mode too | unit | `python3 -m pytest tests/mlforge/test_cli.py -x -k dataset_path_expert` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/mlforge/test_engine.py tests/mlforge/test_cli.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/mlforge/ -x -q`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
- [ ] `tests/mlforge/test_engine.py` -- add tests for sft diagnostics routing, DL draft fallback, max_turns system prompt
- [ ] `tests/mlforge/test_cli.py` -- add test for dataset_path in plugin_settings for DL domain (simple and expert modes)
- No framework install needed (pytest already configured, 572 tests passing)

## Open Questions

1. **dataset_path for expert mode DL**
   - What we know: Simple mode runs profiling for tabular CSVs. Expert mode skips profiling. DL datasets may be directories.
   - What's unclear: Should `dataset_path` be set from `args.dataset` name for ALL domains unconditionally?
   - Recommendation: Yes, set unconditionally. `dataset_path.name` gives just the filename/dirname, which is what `_load_dl_labels()` expects (it joins with `experiment_dir`).

2. **max_turns enforcement strength**
   - What we know: Protocol instructions are "soft" -- the agent might not comply perfectly. Budget guard (`--max-budget-usd`) is "hard."
   - What's unclear: Is protocol-level max_turns enforcement sufficient?
   - Recommendation: Yes, consistent with project's "protocol-first" philosophy. The hard budget guard provides a financial backstop.

## Sources

### Primary (HIGH confidence)
- `src/mlforge/engine.py` -- direct code inspection of all four bugs
- `src/mlforge/cli.py` -- direct code inspection of dataset_path gap
- `src/mlforge/intelligence/drafts.py` -- ALGORITHM_FAMILIES structure confirms DL task keys
- `claude --help` output -- confirms no `--max-turns` flag exists
- `.planning/v1.0-MILESTONE-AUDIT.md` -- all four integration gaps documented with line numbers

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` Phase 6 decision -- "Keep max_turns_per_experiment in Config for forward compatibility, stop passing to CLI"

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new deps, all edits in existing files with clear bug descriptions
- Architecture: HIGH - each fix is 3-10 lines, patterns well-established
- Pitfalls: HIGH - expert mode gap and diagnostics fallback both identified from code inspection

**Research date:** 2026-03-21
**Valid until:** Indefinite (internal codebase fixes, no external dependencies)
