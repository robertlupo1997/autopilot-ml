---
phase: 05-domain-plugins-swarm
plan: 01
subsystem: ml-domain
tags: [pytorch, timm, transformers, deeplearning, jinja2, gpu, plugin]

# Dependency graph
requires:
  - phase: 01-core-engine
    provides: DomainPlugin Protocol and plugin registry
  - phase: 02-tabular-plugin
    provides: TabularPlugin reference implementation pattern
provides:
  - DeepLearningPlugin class conforming to DomainPlugin Protocol
  - Frozen prepare.py with GPU detection, image and text data loading
  - dl_train.py.j2 Jinja2 template with time-budgeted PyTorch training
  - pyproject.toml dl and ft optional dependency groups
affects: [05-02-finetuning-plugin, e2e-validation]

# Tech tracking
tech-stack:
  added: [torch, torchvision, timm, transformers, datasets, peft, trl, bitsandbytes, evaluate, rouge-score]
  patterns: [lazy-import for heavy deps, frozen-prepare standalone file, task-conditional Jinja2 template]

key-files:
  created:
    - src/mlforge/deeplearning/__init__.py
    - src/mlforge/deeplearning/prepare.py
    - src/mlforge/templates/dl_train.py.j2
    - tests/mlforge/test_dl_plugin.py
  modified:
    - pyproject.toml

key-decisions:
  - "Module-level torch imports in prepare.py are safe because it is copied to experiment dir, never imported by mlforge core"
  - "Both dl and ft optional dependency groups added in this plan to avoid parallel write conflicts with Plan 02"
  - "Custom task renders a minimal nn.Module skeleton with TODO placeholder, keeping time budget and early stopping wired"

patterns-established:
  - "DL plugin lazy import: all torch/timm/transformers imports inside methods, not at module level"
  - "Task-conditional Jinja2 template: single dl_train.py.j2 handles image, text, and custom via if/elif/else blocks"

requirements-completed: [DL-01, DL-02, DL-03, DL-04, DL-05]

# Metrics
duration: 4min
completed: 2026-03-20
---

# Phase 05 Plan 01: Deep Learning Plugin Summary

**DeepLearningPlugin with frozen GPU-aware prepare.py, task-conditional Jinja2 train template (image/text/custom), and dl+ft optional deps**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T02:30:40Z
- **Completed:** 2026-03-20T02:35:34Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- DeepLearningPlugin class satisfying DomainPlugin Protocol with lazy imports (no torch at module level)
- Frozen prepare.py with get_device_info(), load_image_data(), and load_text_data() for GPU-aware data pipelines
- dl_train.py.j2 template rendering valid Python for image classification (timm), text classification (transformers), and custom architectures
- Training template includes TIME_BUDGET_SEC, early stopping (patience=5), gradient clipping (clip_grad_norm_), ReduceLROnPlateau, mixed precision, and best_model.pt saving
- pyproject.toml with both dl and ft optional dependency groups

## Task Commits

Each task was committed atomically:

1. **Task 1: DeepLearningPlugin class + plugin registry integration + tests** - `4f5663b` (test)
2. **Task 2: Frozen prepare.py + pyproject.toml optional deps** - `f369f33` (feat)
3. **Task 3: DL train.py Jinja2 template with time budget + training features** - `ffb9cdb` (feat)

## Files Created/Modified
- `src/mlforge/deeplearning/__init__.py` - DeepLearningPlugin class with scaffold, validate_config, template_context
- `src/mlforge/deeplearning/prepare.py` - Frozen GPU detection + image/text data loading
- `src/mlforge/templates/dl_train.py.j2` - Jinja2 template for time-budgeted PyTorch training
- `tests/mlforge/test_dl_plugin.py` - 36 tests covering Protocol, validation, scaffold, template, lazy imports
- `pyproject.toml` - Added dl and ft optional dependency groups

## Decisions Made
- Module-level torch imports in prepare.py are correct because it is a standalone file copied during scaffold, never imported by mlforge core
- Both dl and ft optional dependency groups added here to avoid parallel write conflicts with Plan 02
- Custom task renders a minimal nn.Module skeleton with TODO placeholder, keeping all training infrastructure (time budget, early stopping, gradient clipping) pre-wired

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failures in test_scoreboard.py (missing module) and test_ft_plugin.py (parallel plan incomplete) -- out of scope, not caused by this plan

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- DeepLearningPlugin ready for integration with scaffold CLI and run engine
- Plan 02 (fine-tuning plugin) can proceed in parallel -- pyproject.toml ft deps already added
- E2E validation of DL pipeline will require actual torch installation

---
*Phase: 05-domain-plugins-swarm*
*Completed: 2026-03-20*
