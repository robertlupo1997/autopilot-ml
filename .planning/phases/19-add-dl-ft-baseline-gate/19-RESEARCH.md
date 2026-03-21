# Phase 19: Add DL/FT Baseline Gate - Research

**Researched:** 2026-03-20
**Domain:** Baseline computation and gate enforcement for Deep Learning and Fine-tuning domains
**Confidence:** HIGH

## Summary

Phase 19 closes MISS-01 from the v1.0 audit: the dual-baseline gate currently only works for the tabular domain. The `_compute_baselines()` method in `engine.py` (line 516-550) explicitly returns `None` for non-tabular domains, and `passes_baseline_gate()` in `tabular/baselines.py` is a general-purpose comparator that already works with any `{name: {score, std}}` dict regardless of domain.

The work is straightforward: (1) implement domain-appropriate baseline computation functions for DL and FT, (2) extend `_compute_baselines()` to dispatch by domain, and (3) ensure the existing `passes_baseline_gate()` and engine gate logic work unchanged. The gate enforcement in `_process_result()` (lines 232-242) is already domain-agnostic -- it checks `self.state.baselines` regardless of domain, so no changes needed there.

**Primary recommendation:** Create `deeplearning/baselines.py` and `finetuning/baselines.py` with domain-specific `compute_baselines()` functions, then modify `engine.py._compute_baselines()` to dispatch to the appropriate module based on `self.config.domain`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTL-01 | Baseline establishment runs naive + domain-specific baselines before agent starts experimenting | New `compute_baselines()` in DL (random classifier / constant loss) and FT (base model perplexity/loss) modules |
| INTL-02 | Dual-baseline gate requires agent to beat both naive and domain-specific baselines before keeping an experiment | Existing `passes_baseline_gate()` is domain-agnostic; only `_compute_baselines()` dispatch needs extension |
</phase_requirements>

## Architecture Patterns

### Current Baseline Flow

```
engine.py:run()
  -> self._compute_baselines()      # Line 99: called before loop
     -> if domain != "tabular": return None   # Line 523: THE GAP
     -> loads prepare.py dynamically
     -> calls compute_baselines(X, y, metric, task)
  -> self.state.baselines = result

engine.py:_process_result()
  -> if self.state.baselines and metric_value is not None:   # Line 232
       if not passes_baseline_gate(...):  # Domain-agnostic check
         downgrade keep -> revert
```

### Target Architecture

```
engine.py:_compute_baselines()
  -> domain == "tabular"       -> tabular/baselines.py:compute_baselines()
  -> domain == "deeplearning"  -> deeplearning/baselines.py:compute_baselines()
  -> domain == "finetuning"    -> finetuning/baselines.py:compute_baselines()
```

### Recommended Project Structure Change

```
src/mlforge/
  deeplearning/
    baselines.py      # NEW: DL baseline computation
  finetuning/
    baselines.py      # NEW: FT baseline computation
  engine.py           # MODIFIED: dispatch in _compute_baselines()
```

### Pattern: Domain-Appropriate Baselines

**Deep Learning baselines** (classification tasks: image_classification, text_classification, custom):
- **Naive baseline (random):** Random predictions with uniform class distribution -- equivalent to DummyClassifier(strategy="uniform"). Score: 1/num_classes for accuracy.
- **Domain-specific baseline (most_frequent):** Predict the most common class -- equivalent to DummyClassifier(strategy="most_frequent").
- These do NOT require loading data or running the model. They can be computed from the config (num_classes) or from a simple label scan of the dataset.

**Fine-tuning baselines** (generative/language tasks):
- **Naive baseline:** Random perplexity baseline. For loss metric: a constant-prediction loss (e.g., log(vocab_size) for cross-entropy). For perplexity: exp(log(vocab_size)).
- **Domain-specific baseline:** Base model (pre-fine-tuning) loss/perplexity on the eval set. This IS the meaningful baseline -- fine-tuning should improve upon the pre-trained model's starting performance.
- NOTE: Base model evaluation requires loading the model, which is expensive and GPU-dependent. A practical alternative is to use a theoretical constant as the "naive" baseline and let the first experiment establish the "base model" baseline from the train.py output.

### Design Decision: Lightweight vs Heavy Baselines

**Recommended: Lightweight baselines that do not require GPU or heavy imports.**

Rationale:
1. The engine itself runs on CPU (it spawns `claude -p` subprocesses). Loading PyTorch models in the engine would be architecturally wrong.
2. The tabular baselines use sklearn DummyClassifier/DummyRegressor -- simple, fast, no GPU needed.
3. DL/FT baselines should follow the same pattern: compute theoretical bounds without loading models.

**DL approach:**
- Read the dataset labels to count classes (for classification metrics)
- Compute random-chance and most-frequent scores analytically or with sklearn DummyClassifier on labels
- For loss metric: use -log(1/num_classes) as random baseline

**FT approach:**
- Use theoretical baselines: log(vocab_size) for loss, exp(log(vocab_size)) for perplexity
- These are the "random guessing" equivalents for language modeling
- Common vocab sizes: 32000 (Llama), 50257 (GPT-2), 32000 (Mistral) -- default to 32000 if unknown
- A second baseline: slightly better than random (e.g., 90% of random-guess loss) as the "domain-specific" gate

### Anti-Patterns to Avoid

- **Loading PyTorch/transformers in engine.py:** The engine is CPU-only infrastructure. DL/FT deps are standalone in experiment directories. NEVER import torch in engine.py.
- **Dynamically loading DL prepare.py:** Unlike tabular's prepare.py (which uses pandas/numpy available to mlforge), the DL/FT prepare.py files import torch at module level. Loading them in the engine would fail.
- **Over-engineering baselines:** The baselines are a gate, not a benchmark suite. They should be trivially fast to compute. The point is "are you better than random guessing?" not "are you better than a fine-tuned model?"

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Class-frequency baselines for DL | Custom counting logic | sklearn.dummy.DummyClassifier on label arrays | Already proven in tabular baselines, handles edge cases |
| Baseline score format | New format | Existing `{name: {score, std}}` dict | passes_baseline_gate() already consumes this format |
| Gate enforcement for DL/FT | New gate logic | Existing passes_baseline_gate() | Already domain-agnostic, just needs populated baselines |

## Common Pitfalls

### Pitfall 1: Importing GPU Dependencies in Engine
**What goes wrong:** Adding `import torch` or `from transformers import ...` to engine.py or the new baseline modules.
**Why it happens:** Seems natural to compute "real" baselines using the actual frameworks.
**How to avoid:** DL baselines use sklearn DummyClassifier on extracted labels (numpy arrays). FT baselines use math.log() for theoretical bounds. No torch/transformers imports.
**Warning signs:** Any `import torch` in files under `src/mlforge/` (except `deeplearning/prepare.py` and `finetuning/prepare.py` which are standalone).

### Pitfall 2: Forgetting to Handle Missing Data for DL
**What goes wrong:** DL datasets (images) don't have a simple CSV to scan for labels.
**Why it happens:** Tabular baselines load CSV via prepare.py. DL data might be image folders.
**How to avoid:** For DL, get task type and num_classes from config.plugin_settings. If not available, scan the data directory for class folders. Fallback: return None (skip baselines gracefully).

### Pitfall 3: Breaking the Existing Test
**What goes wrong:** `test_baselines_skipped_for_non_tabular` (test_engine.py line 742) asserts `state.baselines is None` for domain="dl".
**Why it happens:** This test was written when DL baselines didn't exist.
**How to avoid:** Update this test to verify baselines ARE computed for DL/FT domains. The domain string in config is "deeplearning" not "dl" (see DeepLearningPlugin.name).

### Pitfall 4: FT Metric Direction Confusion
**What goes wrong:** Fine-tuning uses loss/perplexity (direction=minimize) but baselines computed for maximize direction.
**Why it happens:** Forgetting that FT metrics go in opposite direction from tabular accuracy.
**How to avoid:** The direction is already in `self.config.direction` and `passes_baseline_gate()` handles both directions. Just ensure FT baseline scores are the values to beat (higher loss = worse = the baseline).

## Code Examples

### DL Baselines (deeplearning/baselines.py)

```python
# Pattern: Lightweight baselines without GPU deps
from __future__ import annotations

import math
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score


def compute_baselines(
    labels: np.ndarray,
    scoring: str,
    task: str,
) -> dict[str, dict[str, float]]:
    """Compute DL baselines from label array only (no features needed).

    For classification: random and most_frequent strategies via DummyClassifier.
    For loss metric: theoretical random-guess cross-entropy loss.
    """
    if scoring == "loss":
        num_classes = len(np.unique(labels))
        random_loss = -math.log(1.0 / max(num_classes, 2))
        return {
            "random_guess": {"score": random_loss, "std": 0.0},
            "uniform_prediction": {"score": random_loss * 0.95, "std": 0.0},
        }

    # Classification metrics (accuracy, f1, f1_weighted)
    X_dummy = np.zeros((len(labels), 1))  # Dummy features
    strategies = {
        "random": DummyClassifier(strategy="uniform", random_state=42),
        "most_frequent": DummyClassifier(strategy="most_frequent"),
    }
    cv = StratifiedKFold(n_splits=min(5, len(labels)), shuffle=True, random_state=42)

    baselines = {}
    for name, model in strategies.items():
        scores = cross_val_score(model, X_dummy, labels, scoring=scoring, cv=cv)
        baselines[name] = {"score": float(scores.mean()), "std": float(scores.std())}

    return baselines
```

### FT Baselines (finetuning/baselines.py)

```python
# Pattern: Theoretical baselines for language modeling
from __future__ import annotations

import math


def compute_baselines(
    metric: str,
    vocab_size: int = 32000,
) -> dict[str, dict[str, float]]:
    """Compute fine-tuning baselines from theoretical bounds.

    For loss: random-guess cross-entropy = log(vocab_size).
    For perplexity: exp(log(vocab_size)) = vocab_size.
    """
    random_ce_loss = math.log(vocab_size)

    if metric == "perplexity":
        return {
            "random_guess": {"score": float(vocab_size), "std": 0.0},
            "untrained_model": {"score": float(vocab_size) * 0.8, "std": 0.0},
        }

    # loss (default)
    return {
        "random_guess": {"score": random_ce_loss, "std": 0.0},
        "untrained_model": {"score": random_ce_loss * 0.8, "std": 0.0},
    }
```

### Engine Dispatch (engine.py modification)

```python
def _compute_baselines(self) -> dict | None:
    if self.config.domain == "tabular":
        # ... existing tabular logic unchanged ...
        return compute_baselines(X_train, y_train, self.config.metric, task)

    if self.config.domain == "deeplearning":
        from mlforge.deeplearning.baselines import compute_baselines as dl_baselines
        labels = self._load_dl_labels()
        if labels is None:
            return None
        task = self.config.plugin_settings.get("task", "image_classification")
        return dl_baselines(labels, self.config.metric, task)

    if self.config.domain == "finetuning":
        from mlforge.finetuning.baselines import compute_baselines as ft_baselines
        vocab_size = self.config.plugin_settings.get("vocab_size", 32000)
        return ft_baselines(self.config.metric, vocab_size)

    return None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Baselines only for tabular | Baselines for all domains | This phase | DL/FT experiments must beat random-guess baselines |
| DL/FT skip baseline gate | DL/FT enforced through same gate | This phase | Prevents keeping sub-random experiments |

## Open Questions

1. **How to extract DL labels without importing torch?**
   - What we know: DL datasets might be image folders (class subdirectories) or CSV files with labels.
   - What's unclear: Whether to scan filesystem or rely on config.plugin_settings for num_classes.
   - Recommendation: Try scanning for class directories first; fallback to plugin_settings; return None if neither works. Consider adding a small helper in _compute_baselines that reads labels from the dataset path without torch.

2. **Should FT baselines use actual vocab_size from the tokenizer?**
   - What we know: Vocab sizes vary (32K for Llama/Mistral, 50K+ for GPT-2/Falcon).
   - What's unclear: Whether it's worth loading tokenizer config just for baseline computation.
   - Recommendation: Use 32000 as default, allow override via `plugin_settings.vocab_size`. Loading tokenizer JSON config without transformers is possible but adds complexity for minimal gain.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml (pytest section) |
| Quick run command | `python -m pytest tests/mlforge/test_baselines.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTL-01 | DL compute_baselines returns random + most_frequent | unit | `pytest tests/mlforge/test_dl_baselines.py -x` | No - Wave 0 |
| INTL-01 | FT compute_baselines returns theoretical baselines | unit | `pytest tests/mlforge/test_ft_baselines.py -x` | No - Wave 0 |
| INTL-01 | Engine._compute_baselines dispatches to DL module | unit | `pytest tests/mlforge/test_engine.py -k baselines -x` | Partial - existing test needs update |
| INTL-01 | Engine._compute_baselines dispatches to FT module | unit | `pytest tests/mlforge/test_engine.py -k baselines -x` | No - Wave 0 |
| INTL-02 | DL runs populate state.baselines (not None) | unit | `pytest tests/mlforge/test_engine.py -k "baselines and deeplearning" -x` | No - Wave 0 |
| INTL-02 | FT runs populate state.baselines (not None) | unit | `pytest tests/mlforge/test_engine.py -k "baselines and finetuning" -x` | No - Wave 0 |
| INTL-02 | passes_baseline_gate works with DL baseline format | unit | `pytest tests/mlforge/test_baselines.py -x` | Partially - existing gate tests cover format |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/mlforge/test_baselines.py tests/mlforge/test_engine.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/mlforge/test_dl_baselines.py` -- covers INTL-01 for DL domain
- [ ] `tests/mlforge/test_ft_baselines.py` -- covers INTL-01 for FT domain
- [ ] Update `test_baselines_skipped_for_non_tabular` in test_engine.py -- currently asserts None, must verify baselines populated

## Sources

### Primary (HIGH confidence)
- `src/mlforge/engine.py` lines 516-550 -- current `_compute_baselines()` implementation
- `src/mlforge/tabular/baselines.py` -- existing baseline pattern (compute_baselines + passes_baseline_gate)
- `src/mlforge/deeplearning/__init__.py` -- DL plugin valid metrics/tasks
- `src/mlforge/finetuning/__init__.py` -- FT plugin valid metrics
- `tests/mlforge/test_engine.py` lines 684-827 -- existing baseline tests
- `tests/mlforge/test_baselines.py` -- existing tabular baseline tests

### Secondary (MEDIUM confidence)
- sklearn DummyClassifier with strategy="uniform" for random-chance classification baseline -- verified in sklearn docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses existing sklearn DummyClassifier pattern + math.log for theoretical bounds
- Architecture: HIGH - Follows established dispatch pattern, existing gate logic is domain-agnostic
- Pitfalls: HIGH - All identified from direct code reading

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable codebase, no external dependency changes expected)
