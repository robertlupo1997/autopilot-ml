# Phase 12: Wire Plugin Validation + Task Type Mapping - Research

**Researched:** 2026-03-20
**Domain:** Plugin validation wiring, task type mapping between profiler and DL/FT plugins
**Confidence:** HIGH

## Summary

Phase 12 closes two gaps from the v1.0 milestone audit: GAP-4 (validate_config() is dead code -- defined on all 3 plugins but never called) and GAP-5 (profiler outputs `classification`/`regression` but DL plugin expects `image_classification`/`text_classification`, causing wrong model architecture in simple mode).

The fix is straightforward: (1) call `plugin.validate_config(config)` in `scaffold.py` before `plugin.scaffold()`, raising on errors; (2) add a task-type mapping layer in `scaffold.py` or `cli.py` that translates profiler generic types to DL-specific types before the config reaches the plugin; (3) verify FineTuningPlugin's existing `model_name` validation works end-to-end once validate_config is wired.

**Primary recommendation:** Add validate_config() call in scaffold_experiment() between plugin registration and plugin.scaffold(), plus a _map_task_for_domain() function that translates profiler task types to domain-specific types.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FT-04 | Plugin generates domain-specific CLAUDE.md protocol with fine-tuning rules | validate_config() wiring ensures FT plugin catches missing model_name before scaffold renders invalid template |
| DL-03 | Plugin supports LR scheduling, early stopping, gradient clipping as protocol rules | validate_config() wiring ensures DL plugin catches invalid metrics/tasks before rendering template with these features |
| UX-01 | Simple mode auto-detects task type and works for all domains | Task type mapping translates profiler output to DL/FT expected types so simple mode works beyond tabular |
| TABL-01 | Tabular plugin handles classification/regression | validate_config() wiring provides metric validation for tabular domain too |
| DL-01 | DL plugin handles image_classification, text_classification, custom | Task mapping ensures profiler's `classification` maps to `image_classification` (default) for DL domain |
| FT-01 | FT plugin handles LoRA/QLoRA fine-tuning | validate_config() + model_name requirement enforcement ensures FT scaffold produces valid train.py |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mlforge.plugins | internal | DomainPlugin Protocol with validate_config() | Already defined, just needs wiring |
| mlforge.scaffold | internal | scaffold_experiment() is the single entry point | All domain scaffolding flows through here |
| mlforge.profiler | internal | profile_dataset() produces generic task types | Source of `classification`/`regression` that needs mapping |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mlforge.config | internal | Config.plugin_settings["task"] carries task type | Task mapping mutates this before scaffold |
| mlforge.cli | internal | Simple mode sets plugin_settings from profiler | May need mapping here or in scaffold |

## Architecture Patterns

### Pattern 1: Validation Gate in scaffold_experiment()

**What:** Call `plugin.validate_config(config)` after plugin registration but before `plugin.scaffold()`. If errors are returned, raise `ValueError` with the joined error messages.

**When to use:** Every scaffold call -- this is the universal entry point.

**Example:**
```python
# In scaffold_experiment(), between steps 2 and 3:
_ensure_plugin_registered(config.domain)
plugin = get_plugin(config.domain)

# NEW: Validate config before scaffolding
errors = plugin.validate_config(config)
if errors:
    raise ValueError(
        f"Invalid config for {config.domain} plugin:\n"
        + "\n".join(f"  - {e}" for e in errors)
    )

# Existing step 3:
plugin.scaffold(target_dir, config)
```

### Pattern 2: Task Type Mapping

**What:** A mapping function that translates profiler generic types to domain-specific types. The profiler outputs `"classification"` or `"regression"` -- the DL plugin expects `"image_classification"`, `"text_classification"`, or `"custom"`. The FT plugin does not use task types (it always does causal LM fine-tuning).

**When to use:** Before validate_config() is called, so the mapped task passes validation.

**Where to put it:** In `scaffold.py` as `_map_task_for_domain()`, called at the start of `scaffold_experiment()`. This keeps the mapping centralized and domain-aware.

**Example:**
```python
_TASK_TYPE_MAP: dict[str, dict[str, str]] = {
    "deeplearning": {
        "classification": "image_classification",
        "regression": "custom",
    },
    # tabular and finetuning pass through unchanged
}

def _map_task_for_domain(config: Config) -> None:
    """Map profiler task types to domain-specific task types in-place."""
    task_map = _TASK_TYPE_MAP.get(config.domain)
    if task_map is None:
        return
    current_task = config.plugin_settings.get("task")
    if current_task and current_task in task_map:
        config.plugin_settings["task"] = task_map[current_task]
```

**Key decisions:**
- `classification` -> `image_classification` (default DL assumption -- image is most common)
- `regression` -> `custom` (no standard DL regression template; custom lets the agent adapt)
- Tabular passes through unchanged (`classification`/`regression` are native tabular types)
- FT plugin ignores task entirely (always causal LM) so no mapping needed

### Pattern 3: FineTuningPlugin model_name Enforcement

**What:** The FT plugin's `validate_config()` already checks for `model_name` and returns an actionable error. Once validate_config is wired (Pattern 1), this works automatically.

**Example of the existing code (already correct):**
```python
# In FineTuningPlugin.validate_config():
if not config.plugin_settings.get("model_name"):
    errors.append(
        "plugin_settings missing 'model_name' -- required for fine-tuning "
        "(e.g., 'meta-llama/Llama-3.2-1B')"
    )
```

No changes needed to the FT plugin itself -- just wiring the call.

### Anti-Patterns to Avoid
- **Mapping in the profiler:** The profiler should remain domain-agnostic. It outputs generic ML task types. Domain-specific mapping belongs in scaffold.
- **Mapping in the CLI:** The CLI already has too many responsibilities. Scaffold is the right place since it already handles plugin registration.
- **Silent fallback on validation failure:** validate_config errors should be raised, not logged and ignored. The whole point is to prevent invalid scaffolding.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config validation | Custom validation logic in scaffold | `plugin.validate_config()` | Already implemented on all 3 plugins, just needs calling |
| Task type mapping | Complex inference in profiler | Simple dict-based mapping in scaffold | Explicit mapping is clear and testable |

## Common Pitfalls

### Pitfall 1: Validation After Scaffold
**What goes wrong:** Calling validate_config() after scaffold() -- files already written with invalid config.
**Why it happens:** Temptation to validate "as we go."
**How to avoid:** validate_config() MUST run before plugin.scaffold() in scaffold_experiment().

### Pitfall 2: Mutating Config Object Globally
**What goes wrong:** _map_task_for_domain() mutates config.plugin_settings in-place, potentially affecting callers who hold a reference.
**Why it happens:** Config is a mutable dataclass.
**How to avoid:** This is acceptable here because scaffold_experiment() is called once per run. But document that the function mutates config in-place. The CLI already mutates config.plugin_settings directly (line 164), so this pattern is established.

### Pitfall 3: DL Default Task for Expert Mode
**What goes wrong:** Expert mode user specifies `--domain deeplearning` without setting task -- gets the mapped default instead of their intent.
**Why it happens:** Mapping runs unconditionally.
**How to avoid:** Only map when the task value is a profiler output type (`classification`/`regression`). If the user already set `image_classification`/`text_classification`/`custom`, don't remap. The mapping dict only contains profiler types as keys, so DL-native types pass through safely.

### Pitfall 4: FT Simple Mode Without model_name
**What goes wrong:** User runs `mlforge data.json "fine-tune model" --domain finetuning` -- profiler can't detect a model name, validate_config rejects it.
**Why it happens:** Fine-tuning requires model_name but simple mode has no way to auto-detect it.
**How to avoid:** This is correct behavior -- the error message is actionable: "plugin_settings missing 'model_name'". The user should use `--metric perplexity` and set model_name via config. Document this in error message.

## Code Examples

### scaffold.py Changes (Complete)
```python
# At top of scaffold_experiment(), after getting plugin:
_ensure_plugin_registered(config.domain)
plugin = get_plugin(config.domain)

# NEW: Map profiler task types to domain-specific types
_map_task_for_domain(config)

# NEW: Validate config before scaffolding
errors = plugin.validate_config(config)
if errors:
    raise ValueError(
        f"Invalid config for {config.domain} plugin:\n"
        + "\n".join(f"  - {e}" for e in errors)
    )

# Existing: plugin scaffolds domain-specific files
plugin.scaffold(target_dir, config)
```

### Test: validate_config Wired
```python
def test_scaffold_rejects_invalid_metric(dataset, target_dir):
    config = Config(domain="tabular", metric="nonexistent_metric")
    with pytest.raises(ValueError, match="Invalid config.*tabular"):
        scaffold_experiment(config=config, dataset_path=dataset,
                          target_dir=target_dir, run_id="run-1")

def test_scaffold_rejects_ft_without_model_name(dataset, target_dir):
    config = Config(domain="finetuning", metric="perplexity")
    # plugin_settings has no model_name
    with pytest.raises(ValueError, match="model_name"):
        scaffold_experiment(config=config, dataset_path=dataset,
                          target_dir=target_dir, run_id="run-1")
```

### Test: Task Type Mapping
```python
def test_dl_classification_mapped_to_image_classification(dataset, target_dir):
    config = Config(domain="deeplearning", metric="accuracy")
    config.plugin_settings["task"] = "classification"
    scaffold_experiment(config=config, dataset_path=dataset,
                       target_dir=target_dir, run_id="run-dl")
    train_py = (target_dir / "train.py").read_text()
    assert "image_classification" in train_py or "timm" in train_py

def test_dl_native_task_not_remapped(dataset, target_dir):
    config = Config(domain="deeplearning", metric="accuracy")
    config.plugin_settings["task"] = "text_classification"
    scaffold_experiment(config=config, dataset_path=dataset,
                       target_dir=target_dir, run_id="run-dl")
    train_py = (target_dir / "train.py").read_text()
    assert "AutoModelForSequenceClassification" in train_py
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| validate_config defined but never called | validate_config called in scaffold_experiment | Phase 12 | Invalid configs caught before scaffolding |
| Profiler types passed directly to all plugins | Domain-aware mapping in scaffold | Phase 12 | DL simple mode gets correct model architecture |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/mlforge/test_scaffold.py tests/mlforge/test_plugins.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FT-04 | FT validate_config rejects missing model_name via scaffold | unit | `pytest tests/mlforge/test_scaffold.py::TestScaffoldValidation -x` | Needs new tests |
| DL-03 | DL validate_config rejects invalid metric/task via scaffold | unit | `pytest tests/mlforge/test_scaffold.py::TestScaffoldValidation -x` | Needs new tests |
| UX-01 | classification maps to image_classification for DL domain | unit | `pytest tests/mlforge/test_scaffold.py::TestTaskTypeMapping -x` | Needs new tests |
| TABL-01 | Tabular validate_config catches invalid metric | unit | `pytest tests/mlforge/test_scaffold.py::TestScaffoldValidation -x` | Needs new tests |
| DL-01 | DL simple mode renders correct train.py for mapped task | unit | `pytest tests/mlforge/test_scaffold.py::TestScaffoldDomainDispatch -x` | Partially exists |
| FT-01 | FT scaffold produces valid train.py with model_name | unit | `pytest tests/mlforge/test_scaffold.py::TestScaffoldDomainDispatch -x` | Partially exists |

### Sampling Rate
- **Per task commit:** `pytest tests/mlforge/test_scaffold.py tests/mlforge/test_plugins.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
- [ ] `tests/mlforge/test_scaffold.py::TestScaffoldValidation` -- new tests for validate_config wiring (invalid metric, missing model_name)
- [ ] `tests/mlforge/test_scaffold.py::TestTaskTypeMapping` -- new test class for task mapping logic

## Sources

### Primary (HIGH confidence)
- Source code inspection of `scaffold.py`, `plugins.py`, `profiler.py`, `deeplearning/__init__.py`, `finetuning/__init__.py`, `tabular/__init__.py`, `cli.py`, `config.py`
- v1.0 Milestone Audit (`.planning/v1.0-MILESTONE-AUDIT.md`) -- GAP-4 and GAP-5 definitions
- Existing test files: `tests/mlforge/test_scaffold.py`, `tests/mlforge/test_plugins.py`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All code is internal, fully inspected
- Architecture: HIGH - Simple wiring changes to existing patterns, no new dependencies
- Pitfalls: HIGH - Edge cases identified from actual code inspection

**Research date:** 2026-03-20
**Valid until:** Indefinite -- internal codebase, no external dependency concerns
