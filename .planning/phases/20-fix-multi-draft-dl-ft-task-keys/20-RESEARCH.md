# Phase 20: Fix Multi-Draft DL/FT Task Keys - Research

**Researched:** 2026-03-20
**Domain:** Multi-draft algorithm family registry for non-tabular domains
**Confidence:** HIGH

## Summary

The `ALGORITHM_FAMILIES` dict in `src/mlforge/intelligence/drafts.py` currently only contains tabular ML families (linear, random_forest, xgboost, lightgbm, svm), each keyed by `classification` and `regression` task types. When `--enable-drafts` is used with DL or FT domains, `_build_draft_prompt()` in engine.py calls `family_info.get(task, family_name)` where `task` is a domain-specific type like `image_classification`, `text_classification`, `custom`, or `sft`. Since none of these keys exist in the current family dicts, the fallback is the raw family name string (e.g., "linear") -- which is meaningless for DL/FT domains.

The fix requires: (1) adding DL-specific entries to `ALGORITHM_FAMILIES` with appropriate model family lists keyed by DL task types, (2) adding FT-specific entries with adapter/method families keyed by FT task types, and (3) making the engine select the correct family subset based on domain. The stagnation branch code in `_process_result` also iterates `ALGORITHM_FAMILIES` for untried families, so domain filtering is needed there too.

**Primary recommendation:** Restructure `ALGORITHM_FAMILIES` as a domain-keyed top-level dict (or add separate `DL_ALGORITHM_FAMILIES` / `FT_ALGORITHM_FAMILIES` dicts) and add a `get_families_for_domain(domain)` helper that `_run_draft_phase` and stagnation logic both use.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTL-05 | Multi-draft start generates 3-5 diverse initial solutions (different model families), picks best, iterates linearly | Currently only works for tabular. Adding DL/FT family entries enables multi-draft for all domains. |
| DL-04 | Plugin generates domain-specific CLAUDE.md protocol with deep learning rules and anti-patterns | DL families in ALGORITHM_FAMILIES enable draft prompts to reference correct DL model classes (ResNet, ViT, etc.) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mlforge (internal) | current | All changes are internal to the mlforge codebase | No external deps needed |

### Supporting
No new dependencies. All changes are to existing modules.

## Architecture Patterns

### Current Structure (Problem)

```python
# drafts.py -- CURRENT (tabular-only)
ALGORITHM_FAMILIES: dict[str, dict[str, str]] = {
    "linear": {
        "description": "Linear models (Ridge/LogisticRegression)",
        "classification": "LogisticRegression",
        "regression": "Ridge",
    },
    # ... only tabular families
}
```

```python
# engine.py -- _build_draft_prompt
model_class = family_info.get(task, family_name)  # Falls back to family_name for DL/FT
```

### Recommended Pattern: Domain-Keyed Families

```python
# drafts.py -- RECOMMENDED
ALGORITHM_FAMILIES: dict[str, dict[str, dict[str, str]]] = {
    "tabular": {
        "linear": {
            "description": "Linear models (Ridge/LogisticRegression)",
            "classification": "LogisticRegression",
            "regression": "Ridge",
        },
        "random_forest": { ... },
        "xgboost": { ... },
        "lightgbm": { ... },
        "svm": { ... },
    },
    "deeplearning": {
        "resnet": {
            "description": "ResNet CNN family (torchvision/timm)",
            "image_classification": "resnet50",
            "text_classification": "distilbert-base-uncased",
            "custom": "resnet50",
        },
        "vit": {
            "description": "Vision Transformer (timm)",
            "image_classification": "vit_base_patch16_224",
            "text_classification": "bert-base-uncased",
            "custom": "vit_base_patch16_224",
        },
        "efficientnet": {
            "description": "EfficientNet family (timm)",
            "image_classification": "efficientnet_b0",
            "text_classification": "roberta-base",
            "custom": "efficientnet_b0",
        },
    },
    "finetuning": {
        "qlora_r8": {
            "description": "QLoRA with rank 8 (memory efficient)",
            "sft": "QLoRA r=8 alpha=8",
        },
        "qlora_r16": {
            "description": "QLoRA with rank 16 (balanced)",
            "sft": "QLoRA r=16 alpha=16",
        },
        "qlora_r32": {
            "description": "QLoRA with rank 32 (higher capacity)",
            "sft": "QLoRA r=32 alpha=32",
        },
        "lora_full": {
            "description": "LoRA without quantization (needs more VRAM)",
            "sft": "LoRA r=16 alpha=16 (no quantization)",
        },
    },
}
```

### Helper Function Pattern

```python
def get_families_for_domain(domain: str) -> dict[str, dict[str, str]]:
    """Return algorithm families for the given domain.

    Falls back to tabular families for unknown domains.
    """
    return ALGORITHM_FAMILIES.get(domain, ALGORITHM_FAMILIES.get("tabular", {}))
```

### Engine Integration Points

Two places in `engine.py` consume `ALGORITHM_FAMILIES`:

1. **`_run_draft_phase()`** (line 322): Iterates all families, builds draft prompt per family.
   - Change: `for family_name, family_info in get_families_for_domain(self.config.domain).items()`

2. **`_process_result()`** (line 267): Stagnation check filters untried families.
   - Change: `untried = [f for f in get_families_for_domain(self.config.domain) if f not in self.state.tried_families]`

3. **Import in engine.py** (line 23): Currently imports `ALGORITHM_FAMILIES` directly.
   - Change: Also import `get_families_for_domain`

### Anti-Patterns to Avoid

- **Flat dict with all domains mixed together:** Would cause tabular runs to try DL models and vice versa. Domain separation is essential.
- **Hardcoding domain checks in engine.py:** Keep domain logic in drafts.py where families are defined. Engine should just call the helper.
- **Breaking the existing tabular flow:** All tabular tests must continue passing. The tabular families dict structure stays identical -- just nested under a "tabular" key.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Domain routing | if/elif chain in engine | `get_families_for_domain()` helper | Single source of truth, testable, extensible |

## Common Pitfalls

### Pitfall 1: Breaking Existing Tabular Tests
**What goes wrong:** Tests reference `ALGORITHM_FAMILIES["linear"]` directly and break when structure changes.
**Why it happens:** Existing tests and engine code import `ALGORITHM_FAMILIES` directly with flat access.
**How to avoid:** Either (a) keep `ALGORITHM_FAMILIES` as the flat tabular dict and add separate `DL_ALGORITHM_FAMILIES` / `FT_ALGORITHM_FAMILIES`, or (b) restructure to domain-keyed and update all 3 test files + 1 engine import.
**Warning signs:** Test failures in `test_drafts.py`, `test_engine.py`.

### Pitfall 2: Stagnation Using Wrong Domain Families
**What goes wrong:** A DL run triggers stagnation and tries branching to "xgboost" -- a tabular family.
**Why it happens:** `_process_result` stagnation check currently iterates the global `ALGORITHM_FAMILIES`.
**How to avoid:** Stagnation code must use the same domain-filtered families as draft phase.

### Pitfall 3: FT Task Key Mismatch
**What goes wrong:** FT maps both classification and regression to "sft" via `_TASK_TYPE_MAP`. If FT families don't have "sft" as a key, the fallback string renders in prompts.
**Why it happens:** Scaffold task mapping runs before engine, so by draft phase time `task` is "sft".
**How to avoid:** Ensure FT family entries use "sft" as the task key, matching the mapped value.

### Pitfall 4: DL "custom" Task Key
**What goes wrong:** DL custom task type doesn't match any family entry.
**Why it happens:** "custom" is a valid DL task but easy to forget.
**How to avoid:** Every DL family entry must have "custom" key in addition to "image_classification" and "text_classification".

## Code Examples

### Current _build_draft_prompt (engine.py:368-387)
```python
def _build_draft_prompt(self, family_name: str, family_info: dict, task: str) -> str:
    model_class = family_info.get(task, family_name)  # BUG: falls back to family_name for DL/FT
    return (
        "You are an ML research agent. Read CLAUDE.md for your protocol. "
        f"This is a DRAFT experiment. Use ONLY {model_class} from "
        f"{family_info.get('description', family_name)}. "
        # ...
    )
```

### Fixed _run_draft_phase (engine.py)
```python
def _run_draft_phase(self) -> list[DraftResult]:
    task = self.config.plugin_settings.get("task", "classification")
    families = get_families_for_domain(self.config.domain)  # NEW
    results: list[DraftResult] = []

    for family_name, family_info in families.items():  # domain-filtered
        prompt = self._build_draft_prompt(family_name, family_info, task)
        # ... rest unchanged
```

### Fixed stagnation in _process_result (engine.py)
```python
families = get_families_for_domain(self.config.domain)  # NEW
untried = [f for f in families if f not in self.state.tried_families]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat ALGORITHM_FAMILIES (tabular only) | Domain-keyed families | Phase 20 | Multi-draft works for DL/FT domains |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml |
| Quick run command | `python -m pytest tests/mlforge/test_drafts.py tests/mlforge/test_engine.py -x -q` |
| Full suite command | `python -m pytest tests/mlforge/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTL-05 | DL families in ALGORITHM_FAMILIES | unit | `pytest tests/mlforge/test_drafts.py -x -q` | Needs update |
| INTL-05 | FT families in ALGORITHM_FAMILIES | unit | `pytest tests/mlforge/test_drafts.py -x -q` | Needs update |
| INTL-05 | get_families_for_domain returns correct subset | unit | `pytest tests/mlforge/test_drafts.py -x -q` | New test |
| DL-04 | _build_draft_prompt renders DL model class | unit | `pytest tests/mlforge/test_engine.py -x -q` | New test |
| DL-04 | _run_draft_phase uses domain families | unit | `pytest tests/mlforge/test_engine.py -x -q` | Needs update |
| INTL-05 | Stagnation uses domain-filtered families | unit | `pytest tests/mlforge/test_engine.py -x -q` | Needs update |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/mlforge/test_drafts.py tests/mlforge/test_engine.py -x -q`
- **Per wave merge:** `python -m pytest tests/mlforge/ -x -q`
- **Phase gate:** Full suite green before verify

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. Tests need updating, not new framework setup.

## Open Questions

1. **Exact DL model families to include**
   - What we know: timm provides ResNet, EfficientNet, ViT; transformers provides BERT, DistilBERT, RoBERTa
   - What's unclear: Exactly which 3-5 families provide maximum diversity for multi-draft
   - Recommendation: ResNet, ViT, EfficientNet for image; DistilBERT, BERT, RoBERTa for text. 3-4 families is sufficient.

2. **FT families -- model vs adapter config**
   - What we know: FT always uses LoRA/QLoRA (protocol rule). Diversity comes from adapter config (rank, alpha) not model architecture.
   - What's unclear: Whether varying LoRA rank alone provides enough diversity for useful multi-draft
   - Recommendation: Vary LoRA rank (8, 16, 32) and quantization (QLoRA vs LoRA). 3-4 families is sufficient.

## Sources

### Primary (HIGH confidence)
- `src/mlforge/intelligence/drafts.py` -- current ALGORITHM_FAMILIES structure
- `src/mlforge/engine.py` -- _run_draft_phase, _build_draft_prompt, stagnation logic
- `src/mlforge/deeplearning/__init__.py` -- _VALID_TASKS: image_classification, text_classification, custom
- `src/mlforge/finetuning/__init__.py` -- FT plugin structure
- `src/mlforge/scaffold.py` -- _TASK_TYPE_MAP showing FT maps to "sft"
- `tests/mlforge/test_drafts.py` -- existing draft tests
- `tests/mlforge/test_engine.py` -- existing engine draft/stagnation tests

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all changes are internal, no new deps
- Architecture: HIGH -- clear pattern from existing tabular implementation, straightforward domain extension
- Pitfalls: HIGH -- identified from direct code reading, all verifiable

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable internal codebase)
