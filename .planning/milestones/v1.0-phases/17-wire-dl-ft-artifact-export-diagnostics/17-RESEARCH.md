# Phase 17: Wire DL/FT Artifact Export + Diagnostics - Research

**Researched:** 2026-03-20
**Domain:** Cross-domain artifact export, diagnostics, and swarm verification for DL/FT
**Confidence:** HIGH

## Summary

Phase 17 closes three integration gaps where infrastructure built for tabular ML (artifact export, diagnostics, swarm verification) is hardcoded to tabular-specific file patterns (`.joblib`, `python train.py --eval-only`) and does not fire for deep learning or fine-tuning domains. The five success criteria each involve surgical edits to existing modules with well-understood interfaces.

The current `export_artifact()` only looks for `best_model.joblib`. DL saves `best_model.pt` and FT saves an `best_adapter/` directory. The current `verify_best_result()` hardcodes `python train.py --eval-only` as eval command. The DL/FT templates do not write `predictions.csv`, so `_run_diagnostics()` never fires for those domains. The `_run_diagnostics()` task detection uses `config.plugin_settings.get("task")` which returns DL-specific values like `image_classification` -- these need mapping to the `classification`/`regression` dichotomy that `diagnose_classification`/`diagnose_regression` expect.

**Primary recommendation:** One plan with 5 tasks -- each maps 1:1 to a success criterion. All changes are small and isolated (export.py, dl_train.py.j2, ft_train.py.j2, verifier.py, engine.py).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DL-04 | Plugin generates domain-specific CLAUDE.md protocol with deep learning rules and anti-patterns | DL template_context needs artifact preservation rule (like tabular's) |
| FT-04 | Plugin generates domain-specific CLAUDE.md protocol with fine-tuning rules and anti-patterns | FT template_context needs artifact preservation rule (like tabular's) |
| UX-03 | Best model artifact exported with metadata after session completes | export_artifact() must handle .pt and adapter dirs, not just .joblib |
| SWARM-04 | Verification agent checks metric improvement claims against actual holdout performance | verify_best_result() must use domain-aware eval commands |
| INTL-03 | Diagnostics engine analyzes WHERE the model fails | DL/FT templates must write predictions.csv so _run_diagnostics() fires |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| torch | >=2.0 | DL model save/load (.pt files) | Already used in dl_train.py.j2 |
| peft | >=0.7 | Adapter save/load (save_pretrained) | Already used in ft_train.py.j2 |
| pandas | >=2.0 | predictions.csv write | Already lazy-imported in engine.py |
| shutil | stdlib | Copy files and directories | Already used in export.py |

### Supporting
No new libraries needed. All changes use existing dependencies.

## Architecture Patterns

### Pattern 1: Domain-Aware Artifact Discovery
**What:** `export_artifact()` must search for model files in domain priority order
**When to use:** Post-session artifact export
**Current state:** Only checks `best_model.joblib`
**Target state:** Check `.joblib` (tabular), `.pt` (DL), and `best_adapter/` directory (FT)

```python
# Priority order for model artifact discovery
_MODEL_PATTERNS = [
    ("best_model.joblib", "file"),     # tabular
    ("best_model.pt", "file"),         # DL
    ("best_adapter", "directory"),     # FT (adapter dir with config + weights)
]
```

**Key design choice:** Search in order, export first match. This keeps the function simple and domain-agnostic -- no need to pass domain config. The file/directory distinction matters because `shutil.copy2` works for files but `shutil.copytree` is needed for adapter directories.

### Pattern 2: Predictions.csv Write in Templates
**What:** DL/FT train templates write `predictions.csv` with `y_true`, `y_pred` columns after training
**When to use:** End of template's `__main__` block, before JSON output
**Established pattern:** `tabular_train.py.j2` already does this (line 133)

For DL: After training loop completes, run inference on val_loader, collect predictions, write CSV.
For FT: After training completes, run inference on eval set, collect predictions, write CSV.

### Pattern 3: Domain-Aware Eval Command in Verifier
**What:** `verify_best_result()` uses different eval commands per domain
**Current state:** Hardcoded `python train.py --eval-only`
**Target state:** Accept domain-aware eval_script parameter, or use `python train.py` (the templates already output JSON as last line)

**Key insight:** The DL and FT templates already print JSON result as the last line of stdout when run normally. The `--eval-only` flag does not exist in any template. The simplest fix is to use `python train.py` as the default eval command for all domains -- the train scripts re-run and output results. However, for efficiency, the verifier could accept the eval_script as a parameter from the caller (SwarmManager) which knows the domain.

### Pattern 4: Task Type Mapping in Diagnostics
**What:** `_run_diagnostics()` maps DL/FT task types to classification/regression
**Current state:** `config.plugin_settings.get("task")` returns `image_classification`, `text_classification`, or `custom` for DL
**Target state:** Map these to `classification` or `regression` for the diagnostics functions

```python
_CLASSIFICATION_TASKS = {"classification", "image_classification", "text_classification", "custom"}
# Anything not in this set -> regression
```

### Anti-Patterns to Avoid
- **Domain-specific if/elif chains in export:** Use ordered search list instead
- **Adding --eval-only flag to templates:** Over-engineering; the templates already output JSON when run
- **Importing torch/peft in export.py:** Keep export.py lightweight; just copy files/dirs
- **Separate diagnostics functions for DL/FT:** The existing classification/regression diagnostics work on any y_true/y_pred arrays regardless of domain

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Directory copy | Manual file-by-file copy | `shutil.copytree` | Handles nested adapter files correctly |
| Model format detection | Parse file headers | Filename convention check | `.pt`, `.joblib`, `best_adapter/` are fixed by templates |

## Common Pitfalls

### Pitfall 1: Adapter Directory Export
**What goes wrong:** Using `shutil.copy2` on a directory raises an error
**Why it happens:** FT adapter is a directory (`best_adapter/`), not a single file
**How to avoid:** Use `shutil.copytree` for directories, `shutil.copy2` for files
**Warning signs:** `IsADirectoryError` or `PermissionError` during export

### Pitfall 2: DL Predictions Memory
**What goes wrong:** Collecting all predictions in GPU memory causes OOM
**Why it happens:** Validation loop accumulates tensors on GPU
**How to avoid:** Move predictions to CPU with `.cpu().numpy()` before appending to list
**Warning signs:** CUDA OOM during prediction collection

### Pitfall 3: Task Type Mapping
**What goes wrong:** `_run_diagnostics()` calls `diagnose_regression` for image classification
**Why it happens:** DL task is `image_classification` which does not match `== "regression"` check
**How to avoid:** Explicitly map DL/FT task types to classification/regression; default to classification
**Warning signs:** Diagnostics show "worst predictions" and "bias" for a classification task

### Pitfall 4: FT Predictions Shape
**What goes wrong:** FT predictions are text strings, not numeric values
**Why it happens:** LLM fine-tuning generates text, not class labels
**How to avoid:** For perplexity/loss metrics, write per-sample loss as y_pred and 0.0 as y_true. For ROUGE, skip predictions.csv (text diagnostics not supported by current diagnostics engine). Use a guard: only write predictions.csv when predictions are numeric.
**Warning signs:** `diagnose_classification` crashes on string arrays

### Pitfall 5: Verifier Eval Script Assumptions
**What goes wrong:** `python train.py --eval-only` fails because no template supports `--eval-only`
**Why it happens:** The flag was hardcoded as default in verifier.py but never implemented in any template
**How to avoid:** Change default to `python train.py` which all templates support (they train + output JSON)

## Code Examples

### 1. Domain-Aware export_artifact (export.py)

```python
# Source: Current codebase analysis
def export_artifact(
    experiment_dir: Path, state: SessionState, config: Config
) -> Path | None:
    artifacts_dir = experiment_dir / "artifacts"

    # Check for model files in priority order
    model_candidates = [
        ("best_model.joblib", False),   # tabular
        ("best_model.pt", False),       # DL
        ("best_adapter", True),         # FT (directory)
    ]

    found_path = None
    is_dir = False
    for name, is_directory in model_candidates:
        candidate = experiment_dir / name
        if is_directory and candidate.is_dir():
            found_path = candidate
            is_dir = True
            break
        elif not is_directory and candidate.is_file():
            found_path = candidate
            break

    if found_path is None:
        return None

    artifacts_dir.mkdir(exist_ok=True)

    if is_dir:
        shutil.copytree(found_path, artifacts_dir / found_path.name, dirs_exist_ok=True)
    else:
        shutil.copy2(found_path, artifacts_dir / found_path.name)

    # Write metadata sidecar (same as before)
    ...
    return artifacts_dir
```

### 2. DL Predictions Write (dl_train.py.j2 -- add before JSON output)

```python
    # --- Save predictions for diagnostics engine ---
    model.eval()
    all_preds = []
    all_labels = []
    with torch.no_grad():
        for batch in val_loader:
            # ... get inputs/labels per task type ...
            logits = model(inputs)  # or model(**kwargs)
            preds = logits.argmax(dim=-1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    import pandas as pd
    pd.DataFrame({"y_true": all_labels, "y_pred": all_preds}).to_csv("predictions.csv", index=False)

    # Save best model
    torch.save(model.state_dict(), "best_model.pt")  # already exists
```

### 3. FT Predictions Write (ft_train.py.j2 -- add before JSON output)

```python
    # --- Save predictions for diagnostics (loss-based) ---
    model.eval()
    all_losses = []
    with torch.no_grad():
        for item in dataset["eval"]:
            text = item["text"] if isinstance(item, dict) else str(item)
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_LENGTH).to(model.device)
            outputs = model(**inputs, labels=inputs["input_ids"])
            all_losses.append(outputs.loss.item())

    import pandas as pd
    pd.DataFrame({"y_true": [0.0] * len(all_losses), "y_pred": all_losses}).to_csv("predictions.csv", index=False)
```

### 4. Diagnostics Task Mapping (engine.py)

```python
def _run_diagnostics(self) -> None:
    predictions_path = self.experiment_dir / "predictions.csv"
    if not predictions_path.exists():
        return

    import pandas as pd
    df = pd.read_csv(predictions_path)
    y_true = df["y_true"].values
    y_pred = df["y_pred"].values

    task = self.config.plugin_settings.get("task", "classification")
    # Map DL/FT tasks to classification/regression
    classification_tasks = {"classification", "image_classification", "text_classification", "custom"}
    if task in classification_tasks:
        diag = diagnose_classification(y_true, y_pred)
        task_type = "classification"
    else:
        diag = diagnose_regression(y_true, y_pred)
        task_type = "regression"

    content = self._format_diagnostics(diag, task_type)
    (self.experiment_dir / "diagnostics.md").write_text(content)
```

### 5. Domain-Aware Verifier (verifier.py)

```python
def verify_best_result(
    experiment_dir: Path,
    scoreboard: SwarmScoreboard,
    eval_script: str = "python train.py",  # Changed default -- all templates support this
) -> dict | None:
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `.joblib` only export | Multi-format export (.joblib, .pt, adapter dir) | This phase | DL/FT artifacts exportable |
| Hardcoded `--eval-only` | `python train.py` (universal) | This phase | Verifier works for all domains |
| No predictions.csv in DL/FT | Templates write predictions.csv | This phase | Diagnostics fire for all domains |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml |
| Quick run command | `python3 -m pytest tests/mlforge/ -x -q` |
| Full suite command | `python3 -m pytest tests/mlforge/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UX-03 | export_artifact handles .pt files | unit | `python3 -m pytest tests/mlforge/test_export.py -x` | Exists, needs new tests |
| UX-03 | export_artifact handles adapter directories | unit | `python3 -m pytest tests/mlforge/test_export.py -x` | Exists, needs new tests |
| DL-04 | DL template_context has artifact preservation rule | unit | `python3 -m pytest tests/mlforge/test_templates.py -x` | Exists, needs new tests |
| FT-04 | FT template_context has artifact preservation rule | unit | `python3 -m pytest tests/mlforge/test_templates.py -x` | Exists, needs new tests |
| INTL-03 | dl_train.py.j2 contains predictions.csv write | unit | `python3 -m pytest tests/mlforge/test_templates.py -x` | Exists, needs new tests |
| INTL-03 | ft_train.py.j2 contains predictions.csv write | unit | `python3 -m pytest tests/mlforge/test_templates.py -x` | Exists, needs new tests |
| SWARM-04 | verify_best_result default eval script changed | unit | `python3 -m pytest tests/mlforge/test_swarm.py -x` | Exists, needs new tests |
| INTL-03 | _run_diagnostics maps DL task types correctly | unit | `python3 -m pytest tests/mlforge/test_engine.py -x` | Exists, needs new tests |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/mlforge/ -x -q`
- **Per wave merge:** `python3 -m pytest tests/mlforge/ -q`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. New tests added alongside implementation.

## Open Questions

1. **FT Predictions Format**
   - What we know: FT metrics are perplexity/loss/ROUGE -- not classification labels
   - What's unclear: Should predictions.csv use per-sample loss values, or should we skip predictions.csv for FT altogether?
   - Recommendation: Write per-sample loss as y_pred with 0.0 as y_true for loss/perplexity metrics. For ROUGE metrics, skip predictions.csv (text diagnostics are not supported by the current diagnostics engine). This is pragmatic and avoids over-engineering.

2. **Verifier Eval Command**
   - What we know: No template supports `--eval-only`. Running `python train.py` re-trains.
   - What's unclear: Is re-training acceptable for verification, or should we add eval-only modes to templates?
   - Recommendation: Change default to `python train.py` for now. Adding eval-only modes is a separate concern and can be a future enhancement. Re-training is acceptable for verification because it validates that the code produces consistent results.

## Sources

### Primary (HIGH confidence)
- `src/mlforge/export.py` -- current artifact export implementation
- `src/mlforge/swarm/verifier.py` -- current verifier with hardcoded eval_script
- `src/mlforge/templates/dl_train.py.j2` -- DL template, no predictions.csv
- `src/mlforge/templates/ft_train.py.j2` -- FT template, no predictions.csv
- `src/mlforge/templates/tabular_train.py.j2` -- reference implementation with predictions.csv + joblib
- `src/mlforge/engine.py` -- _run_diagnostics() with task type detection
- `src/mlforge/intelligence/diagnostics.py` -- classification/regression diagnostics functions
- `src/mlforge/tabular/__init__.py` -- artifact preservation rule pattern in template_context
- `src/mlforge/deeplearning/__init__.py` -- DL plugin template_context (missing artifact rule)
- `src/mlforge/finetuning/__init__.py` -- FT plugin template_context (missing artifact rule)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all changes use existing dependencies
- Architecture: HIGH - patterns established by tabular plugin, extending to DL/FT
- Pitfalls: HIGH - specific edge cases identified from code review (adapter dirs, task mapping, FT predictions)

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable codebase, no external dependency changes)
