# Phase 9: Wire Simple Mode Task Propagation - Research

**Researched:** 2026-03-20
**Domain:** CLI data flow, plugin settings propagation, Jinja2 template rendering
**Confidence:** HIGH

## Summary

The gap is a straightforward data flow break: `profile_dataset()` correctly detects `task`, `csv_path`, and `target_column`, but `cli.py` only propagates `metric`, `direction`, and `date_column` into `config.plugin_settings`. The `TabularPlugin.scaffold()` method and `template_context()` method both read `config.plugin_settings.get("task")` but silently fall back to defaults ("classification" for template_context, "regression" hardcoded in the train.py.j2 template). This means simple mode always generates mismatched train.py files and incorrect CLAUDE.md CV strategy rules.

The fix involves three specific wiring points: (1) CLI propagates `profile.task`, dataset filename, and target column into `config.plugin_settings`, (2) the `tabular_train.py.j2` template accepts a `task` variable and renders the correct model families and evaluate call, and (3) TABL-03 leakage prevention is addressed by ensuring date columns trigger temporal features awareness in the rendered train.py.

**Primary recommendation:** Wire three missing fields (`task`, `csv_path`, `target_column`) from profiler result into `config.plugin_settings` in `cli.py`, and make `tabular_train.py.j2` task-aware.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UX-01 | Simple mode auto-detects task type, selects metrics, and generates protocol from minimal user input | Profiler already detects correctly; gap is propagation from CLI to plugin_settings to scaffold. Three fields need wiring. |
| TABL-03 | Leakage prevention enforces shift-first temporal features and walk-forward CV for time-series data | Date column already detected and stored in plugin_settings; template needs conditional temporal CV section when date_column present. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | (existing) | Template rendering for train.py | Already used by TabularPlugin.scaffold() |
| dataclasses | stdlib | Config, DatasetProfile | Already used throughout |

### Supporting
No new libraries needed. This phase is pure wiring of existing infrastructure.

## Architecture Patterns

### Current Data Flow (BROKEN)
```
User CLI args
    |
    v
profile_dataset(df, target_col)
    |
    v
DatasetProfile { task, metric, direction, date_columns, ... }
    |
    v  (cli.py -- ONLY metric, direction, date_column propagated)
Config { metric, direction, plugin_settings: { date_column? } }
    |
    v
TabularPlugin.scaffold(target_dir, config)
    |
    v  (reads plugin_settings.get("task", "classification") -- WRONG default)
tabular_train.py.j2  (hardcodes task="regression" in evaluate call -- ALWAYS WRONG for classification)
```

### Required Data Flow (FIXED)
```
User CLI args
    |
    v
profile_dataset(df, target_col)
    |
    v
DatasetProfile { task, metric, direction, date_columns, ... }
    |
    v  (cli.py -- propagate ALL: task, csv_path, target_column, date_column)
Config { metric, direction, plugin_settings: { task, csv_path, target_column, date_column? } }
    |
    v
TabularPlugin.scaffold(target_dir, config)
    |
    v  (reads plugin_settings["task"] -- correct value)
tabular_train.py.j2  (renders task-appropriate models + evaluate call)
```

### Wiring Points (3 changes)

**1. cli.py (simple mode block, ~line 155-159)**
Currently sets only `date_column`. Must also set:
- `config.plugin_settings["task"] = profile.task`
- `config.plugin_settings["csv_path"] = dataset_path.name`
- `config.plugin_settings["target_column"] = target_column`

**2. tabular_train.py.j2 (template)**
Currently hardcodes `task="regression"` on line 65. Must:
- Accept `task` as a template variable
- Render classification models (LogisticRegression, RandomForestClassifier) for classification
- Render regression models (Ridge, RandomForestRegressor) for regression
- Pass correct `task=` value to `evaluate()` call

**3. TabularPlugin.scaffold() (tabular/__init__.py, ~line 52)**
Currently passes `csv_path`, `target_column`, `metric`, `time_budget` to template. Must also pass:
- `task` from `config.plugin_settings.get("task", "classification")`

### Pattern: template_context() already works
`TabularPlugin.template_context()` already reads `config.plugin_settings.get("task", "classification")` and renders the correct CV strategy rule (StratifiedKFold vs KFold). Once CLI propagates `task`, CLAUDE.md rendering will automatically be correct.

### Anti-Patterns to Avoid
- **Hardcoding task in template:** The current template hardcodes `task="regression"`. Use the Jinja2 variable instead.
- **Defaulting to wrong task:** Default should be "classification" (more conservative -- StratifiedKFold works for both, classification models fail loudly on regression data).
- **Splitting the fix across too many files:** Keep changes minimal -- 3 files, 3 changes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Task detection | Custom heuristic | `profile_dataset()` | Already exists and is well-tested (119 tests pass) |
| Template rendering | String concatenation | Jinja2 `{% if %}` blocks | Already used, handles escaping and formatting |
| Config propagation | New config fields | `plugin_settings` dict | Already the designed mechanism for plugin-specific data |

**Key insight:** All the infrastructure exists. This is purely a wiring fix, not new feature development.

## Common Pitfalls

### Pitfall 1: Forgetting csv_path uses dataset filename, not full path
**What goes wrong:** Setting `csv_path` to the absolute path when the dataset is copied to target_dir by scaffold.
**Why it happens:** The profiler doesn't know the scaffold layout.
**How to avoid:** Use `dataset_path.name` (filename only) since scaffold copies dataset to target_dir root.
**Warning signs:** train.py has absolute path to dataset instead of relative `data.csv`.

### Pitfall 2: Template default mismatch with template_context default
**What goes wrong:** template_context defaults to "classification" but template hardcodes "regression".
**Why it happens:** Two places have independent defaults.
**How to avoid:** After fix, both use the same `plugin_settings["task"]` value. Default in template rendering should match template_context default ("classification").

### Pitfall 3: Expert mode should not be broken
**What goes wrong:** When `--metric` is specified (expert mode), profiling is skipped, so plugin_settings may be empty.
**Why it happens:** Expert mode path doesn't call profile_dataset().
**How to avoid:** TabularPlugin.scaffold() must continue to have safe defaults for all plugin_settings fields. The `.get("task", "classification")` pattern already handles this.

### Pitfall 4: TABL-03 temporal awareness
**What goes wrong:** Date column is detected but train.py doesn't know to use walk-forward CV.
**Why it happens:** `date_column` is in plugin_settings but train.py template doesn't use it.
**How to avoid:** When `date_column` is present, template should include a comment or import about temporal_split from prepare.py (which already exists).

## Code Examples

### Change 1: cli.py simple mode propagation
```python
# In cli.py, around line 155-159 (inside the profiling try block):
if target_column in df.columns:
    profile = profile_dataset(df, target_column)
    config.metric = profile.metric
    config.direction = profile.direction
    # NEW: propagate task type and data references to plugin
    config.plugin_settings["task"] = profile.task
    config.plugin_settings["csv_path"] = dataset_path.name
    config.plugin_settings["target_column"] = target_column
    if profile.date_columns:
        config.plugin_settings["date_column"] = profile.date_columns[0]
```

### Change 2: TabularPlugin.scaffold() passes task to template
```python
# In tabular/__init__.py, scaffold method:
train_content = template.render(
    csv_path=config.plugin_settings.get("csv_path", "data.csv"),
    target_column=config.plugin_settings.get("target_column", "target"),
    metric=config.metric,
    task=config.plugin_settings.get("task", "classification"),
    time_budget=config.plugin_settings.get("time_budget", 60),
)
```

### Change 3: tabular_train.py.j2 uses task variable
```jinja2
# Configuration section:
TASK = "{{ task }}"

# Model selection in objective():
{% if task == "regression" %}
    if model_name == "rf":
        model = RandomForestRegressor(...)
    elif model_name == "ridge":
        model = Ridge(...)
{% else %}
    if model_name == "rf":
        model = RandomForestClassifier(...)
    elif model_name == "lr":
        model = LogisticRegression(...)
{% endif %}

# Evaluate call:
    result = evaluate(model, X_train_processed, y_train, scoring=METRIC, task="{{ task }}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded regression in template | Task-conditional template | This phase | Correct model families and evaluate() calls |
| metric-only propagation | Full profile propagation | This phase | Simple mode generates correct experiment scaffolds |

## Open Questions

1. **Should date_column trigger temporal_split usage in train.py?**
   - What we know: `prepare.py` already has `temporal_split()`. Date column is detected and stored.
   - What's unclear: Whether train.py template should auto-include temporal CV logic or just note it.
   - Recommendation: Add a comment in rendered train.py noting temporal_split is available when date_column is present. Full temporal template is a separate concern (TABL-03 can be partially closed by awareness, fully closed by template).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest) |
| Config file | pyproject.toml (pytest section) |
| Quick run command | `python3 -m pytest tests/mlforge/test_cli.py tests/mlforge/test_tabular.py tests/mlforge/test_scaffold.py -x -q` |
| Full suite command | `python3 -m pytest tests/mlforge/ -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UX-01 | Simple mode sets task in plugin_settings | unit | `python3 -m pytest tests/mlforge/test_cli.py::TestSimpleMode -x` | Exists, needs new test |
| UX-01 | scaffold renders task-correct train.py | unit | `python3 -m pytest tests/mlforge/test_tabular.py::TestScaffold -x` | Exists, needs new test |
| UX-01 | train.py has correct model for regression | unit | `python3 -m pytest tests/mlforge/test_tabular.py -x` | Needs new test |
| UX-01 | train.py has correct model for classification | unit | `python3 -m pytest tests/mlforge/test_tabular.py -x` | Needs new test |
| TABL-03 | date_column presence noted in rendered train.py | unit | `python3 -m pytest tests/mlforge/test_tabular.py -x` | Needs new test |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/mlforge/test_cli.py tests/mlforge/test_tabular.py tests/mlforge/test_scaffold.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/mlforge/ -q`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
None -- existing test infrastructure covers all needs. New tests are additions to existing test files, not new files or fixtures.

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `src/mlforge/cli.py` (lines 146-166) -- confirmed missing propagation
- Direct code inspection of `src/mlforge/tabular/__init__.py` (lines 30-58) -- confirmed scaffold reads plugin_settings
- Direct code inspection of `src/mlforge/templates/tabular_train.py.j2` (line 65) -- confirmed hardcoded `task="regression"`
- Direct code inspection of `src/mlforge/profiler.py` -- confirmed DatasetProfile has all needed fields
- Test suite: 119 tests pass confirming current behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, pure wiring
- Architecture: HIGH - all integration points inspected directly in source
- Pitfalls: HIGH - identified from reading the actual code paths

**Research date:** 2026-03-20
**Valid until:** Stable (no external dependencies, internal wiring only)
