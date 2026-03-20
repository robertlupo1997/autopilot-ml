# Phase 15: Fix FT Simple Mode Metric Mapping - Research

**Researched:** 2026-03-20
**Domain:** Plugin validation / CLI simple mode wiring
**Confidence:** HIGH

## Summary

Phase 15 fixes a P2 integration gap (INT-04) where `--domain finetuning` in simple mode raises a `ValueError` because (1) `_TASK_TYPE_MAP` in `scaffold.py` has no entry for the `finetuning` domain and (2) the profiler sets `metric='accuracy'` (the Config default / profiler output) which is not in FineTuningPlugin's `_VALID_METRICS = {perplexity, rouge1, rougeL, rouge2, loss}`.

The fix is a two-part wiring change in `scaffold.py` and `cli.py` (or `profiler.py`): add a `finetuning` entry to `_TASK_TYPE_MAP` that maps profiler task types to FT-appropriate types, and override the profiler-set metric with an FT-valid default (e.g., `loss`) when the domain is `finetuning`. This is a small, surgical change touching 2-3 source files and their corresponding test files.

**Primary recommendation:** Add `finetuning` domain handling in `_map_task_for_domain()` and override the metric/direction in the same function (or a new sibling function) so FT simple mode passes `validate_config()`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FT-04 | Plugin generates domain-specific CLAUDE.md protocol with fine-tuning rules and anti-patterns | FT simple mode must reach scaffold to render CLAUDE.md; metric fix unblocks this path |
| UX-01 | Simple mode auto-detects task type, selects metrics, and generates protocol from minimal user input | FT domain needs domain-aware metric override so auto-detection works for `--domain finetuning` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mlforge.scaffold | - | `_TASK_TYPE_MAP` + `_map_task_for_domain()` | Where domain-specific task/metric mapping lives |
| mlforge.finetuning | - | `FineTuningPlugin.validate_config()` | Defines `_VALID_METRICS` that must be satisfied |
| mlforge.config | - | `Config` dataclass | Holds `metric`, `direction`, `domain`, `plugin_settings` |
| mlforge.cli | - | `main()` simple mode block | Where profiler output is applied to config |
| mlforge.profiler | - | `profile_dataset()` | Produces generic task/metric (not domain-aware) |

No new dependencies needed. This is purely internal wiring.

## Architecture Patterns

### Existing Pattern: `_map_task_for_domain()` in scaffold.py

The established pattern mutates `config` in-place before `validate_config()` is called. The DL domain already uses this:

```python
# Current code in scaffold.py (lines 90-116)
_TASK_TYPE_MAP: dict[str, dict[str, str]] = {
    "deeplearning": {
        "classification": "image_classification",
        "regression": "custom",
    },
}

def _map_task_for_domain(config: Config) -> None:
    domain_map = _TASK_TYPE_MAP.get(config.domain)
    if domain_map is None:
        return
    current_task = config.plugin_settings.get("task")
    if current_task is not None and current_task in domain_map:
        config.plugin_settings["task"] = domain_map[current_task]
```

**The fix follows this exact pattern** -- add a `finetuning` entry and extend the function to also fix metric/direction when needed.

### Pattern: Domain-Aware Metric Override

The profiler is domain-agnostic -- it outputs `accuracy`, `f1_weighted`, or `r2` based on data analysis. For FT domain, these are all invalid. The metric must be overridden to an FT-valid value.

Two viable approaches (both follow established patterns):

1. **Extend `_map_task_for_domain()` to also map metrics** -- add a `_METRIC_MAP` or handle metric alongside task in the same function. This keeps all domain mapping logic in one place.

2. **Override metric in CLI before scaffold** -- add domain-aware logic in `cli.py`'s simple mode block. This is where profiler output is already applied to config.

**Recommended: Approach 1** -- keep all domain mapping in `scaffold.py` where it already lives. The function already mutates config in-place, adding metric override is consistent.

### Anti-Patterns to Avoid
- **Modifying profiler.py to be domain-aware:** The profiler analyzes data characteristics, not domain semantics. Keep it domain-agnostic.
- **Adding FT metric selection logic in cli.py:** Domain mapping logic belongs in scaffold.py (established by Phase 12 decision).
- **Making validate_config() lenient:** The validation is correct -- `accuracy` IS invalid for FT. Fix the input, not the validator.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FT task type | New FT-specific profiler | `_TASK_TYPE_MAP` entry | Profiler is domain-agnostic by design |
| FT metric selection | Complex metric negotiation | Simple default override (`loss`) | FT metrics are fundamentally different from tabular/DL |
| FT direction | Direction inference logic | Hardcode `minimize` for `loss`/`perplexity` | All FT valid metrics are minimize-direction |

## Common Pitfalls

### Pitfall 1: Forgetting to set `direction` alongside `metric`
**What goes wrong:** Metric is set to `loss` but direction stays `maximize` (Config default), causing the engine to optimize in the wrong direction.
**Why it happens:** `Config.direction` defaults to `"maximize"`, and profiler sets direction for tabular metrics but FT override might skip it.
**How to avoid:** Always set both `config.metric` and `config.direction` together in the mapping function.
**Warning signs:** Test passes validation but engine maximizes loss instead of minimizing.

### Pitfall 2: Breaking existing FT expert mode
**What goes wrong:** Expert mode user passes `--metric perplexity --domain finetuning` and the mapping function overwrites their metric choice.
**Why it happens:** Mapping runs unconditionally without checking if the user explicitly set the metric.
**How to avoid:** Only override metric when it came from the profiler (i.e., when the current metric is NOT already in FT's valid set). Check `config.metric not in FineTuningPlugin._VALID_METRICS` before overriding.
**Warning signs:** `test_scaffold_finetuning_domain` (existing test) breaks because it sets `metric="perplexity"` explicitly.

### Pitfall 3: Not setting `model_name` default for simple mode
**What goes wrong:** FT `validate_config()` also requires `model_name` in `plugin_settings`. Simple mode won't set this.
**Why it happens:** Simple mode only sets `task`, `csv_path`, `target_column` from profiler -- no `model_name`.
**How to avoid:** Either set a default `model_name` in the mapping function, or accept that FT simple mode needs `--domain finetuning` to work but `model_name` validation will still fail. The roadmap success criteria say "reaches scaffold without ValueError from validate_config()" -- this means `model_name` must also be handled.
**Warning signs:** Fix metric but still get ValueError for missing model_name.

### Pitfall 4: FT task type mapping semantics
**What goes wrong:** Mapping `classification` to some FT task type that doesn't exist.
**Why it happens:** FT plugin doesn't have `_VALID_TASKS` like DL plugin does -- it doesn't validate task at all.
**How to avoid:** Map profiler tasks to a generic FT type like `"sft"` (supervised fine-tuning) or simply leave task as-is since FT plugin ignores it. Check if task mapping is even needed -- the success criteria only mention metric mapping.

## Code Examples

### Fix 1: Add finetuning to `_TASK_TYPE_MAP` and metric/direction override

```python
# In scaffold.py -- extend _TASK_TYPE_MAP
_TASK_TYPE_MAP: dict[str, dict[str, str]] = {
    "deeplearning": {
        "classification": "image_classification",
        "regression": "custom",
    },
    "finetuning": {
        "classification": "sft",
        "regression": "sft",
    },
}

# New: domain-aware metric defaults
_METRIC_DEFAULTS: dict[str, tuple[str, str]] = {
    "finetuning": ("loss", "minimize"),
}

def _map_task_for_domain(config: Config) -> None:
    """Map profiler task types and metrics to domain-specific values."""
    # Task type mapping (existing logic)
    domain_map = _TASK_TYPE_MAP.get(config.domain)
    if domain_map is not None:
        current_task = config.plugin_settings.get("task")
        if current_task is not None and current_task in domain_map:
            config.plugin_settings["task"] = domain_map[current_task]

    # Metric override for domains where profiler defaults are invalid
    metric_default = _METRIC_DEFAULTS.get(config.domain)
    if metric_default is not None:
        valid_metric, valid_direction = metric_default
        # Only override if current metric is not already valid for this domain
        # (preserves expert mode where user explicitly sets --metric perplexity)
        from mlforge.finetuning import FineTuningPlugin
        if config.metric not in FineTuningPlugin._VALID_METRICS:
            config.metric = valid_metric
            config.direction = valid_direction
```

### Fix 2: Set default model_name for FT simple mode

```python
# In the same _map_task_for_domain or a new helper
if config.domain == "finetuning" and not config.plugin_settings.get("model_name"):
    config.plugin_settings["model_name"] = "meta-llama/Llama-3.2-1B"
```

### Test: FT simple mode reaches scaffold

```python
def test_ft_simple_mode_metric_override(self, dataset, target_dir):
    """Simple mode with finetuning domain overrides profiler metric to FT-valid."""
    cfg = Config(
        domain="finetuning",
        metric="accuracy",  # profiler default -- invalid for FT
        plugin_settings={"task": "classification", "model_name": "test/model"},
    )
    scaffold_experiment(config=cfg, dataset_path=dataset, target_dir=target_dir, run_id="run-ft")
    assert cfg.metric in {"loss", "perplexity", "rouge1", "rougeL", "rouge2"}

def test_ft_expert_mode_metric_preserved(self, dataset, target_dir):
    """Expert mode with explicit FT metric is not overridden."""
    cfg = Config(
        domain="finetuning",
        metric="perplexity",  # user-specified, valid
        plugin_settings={"model_name": "test/model"},
    )
    scaffold_experiment(config=cfg, dataset_path=dataset, target_dir=target_dir, run_id="run-ft")
    assert cfg.metric == "perplexity"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No FT task mapping | `_TASK_TYPE_MAP` entry for finetuning | Phase 15 | FT simple mode unblocked |
| Profiler metric used as-is for all domains | Domain-aware metric override | Phase 15 | FT validation passes |

## Open Questions

1. **Should FT simple mode set a default `model_name`?**
   - What we know: `validate_config()` requires `model_name`. Simple mode doesn't set it.
   - What's unclear: Is it acceptable to set a default like `meta-llama/Llama-3.2-1B`, or should FT require explicit `model_name`?
   - Recommendation: Set a sensible default. The success criteria say "reaches scaffold without ValueError" -- this requires solving model_name too. A small default model is safe (1B params).

2. **What FT task type should profiler tasks map to?**
   - What we know: FT plugin doesn't validate task type (no `_VALID_TASKS` check). It's ignored in scaffold.
   - What's unclear: Whether we even need a mapping or can just leave task as-is.
   - Recommendation: Map to `"sft"` for clarity, but it's functionally optional since FT plugin doesn't check task.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml |
| Quick run command | `python3 -m pytest tests/mlforge/test_scaffold.py tests/mlforge/test_ft_plugin.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FT-04 | FT simple mode metric overridden to valid FT metric | unit | `python3 -m pytest tests/mlforge/test_scaffold.py::TestTaskTypeMapping -x` | Partial (class exists, FT metric test missing) |
| FT-04 | FT expert mode metric preserved | unit | `python3 -m pytest tests/mlforge/test_scaffold.py::TestTaskTypeMapping -x` | Partial |
| UX-01 | `--domain finetuning` reaches scaffold without ValueError | unit | `python3 -m pytest tests/mlforge/test_scaffold.py::TestScaffoldValidation -x` | Partial (FT validation test exists but only for missing model_name) |
| UX-01 | FT direction set correctly (minimize for loss) | unit | `python3 -m pytest tests/mlforge/test_scaffold.py -x` | No |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/mlforge/test_scaffold.py tests/mlforge/test_ft_plugin.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/mlforge/test_scaffold.py::TestTaskTypeMapping::test_ft_simple_mode_metric_override` -- covers FT-04 metric fix
- [ ] `tests/mlforge/test_scaffold.py::TestTaskTypeMapping::test_ft_expert_mode_metric_preserved` -- covers expert mode safety
- [ ] `tests/mlforge/test_scaffold.py::TestTaskTypeMapping::test_ft_direction_set_to_minimize` -- covers direction fix
- [ ] `tests/mlforge/test_scaffold.py::TestScaffoldValidation::test_ft_simple_mode_reaches_scaffold` -- covers UX-01 E2E

## Sources

### Primary (HIGH confidence)
- Source code: `src/mlforge/scaffold.py` lines 90-116 -- `_TASK_TYPE_MAP` and `_map_task_for_domain()`
- Source code: `src/mlforge/finetuning/__init__.py` lines 27-29, 94-117 -- `_VALID_METRICS` and `validate_config()`
- Source code: `src/mlforge/profiler.py` lines 119-137 -- metric selection logic (domain-agnostic)
- Source code: `src/mlforge/cli.py` lines 152-178 -- simple mode profiling block
- `.planning/v1.0-MILESTONE-AUDIT.md` line 40 -- INT-04 gap definition

### Secondary (MEDIUM confidence)
- None needed -- all findings from direct source code analysis

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - direct source code reading, no external deps
- Architecture: HIGH - follows established `_map_task_for_domain()` pattern from Phase 12
- Pitfalls: HIGH - identified from code paths and existing test coverage

**Research date:** 2026-03-20
**Valid until:** Indefinite (internal codebase analysis, no external dependencies)
