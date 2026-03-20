---
phase: 05-domain-plugins-swarm
plan: 02
subsystem: plugins
tags: [finetuning, lora, qlora, peft, trl, sfttrainer, jinja2, quantization]

# Dependency graph
requires:
  - phase: 01-core-engine
    provides: "DomainPlugin Protocol and plugin registry"
  - phase: 02-tabular-plugin
    provides: "TabularPlugin reference implementation pattern"
provides:
  - "FineTuningPlugin class implementing DomainPlugin Protocol"
  - "Frozen prepare.py with VRAM detection, dataset formatting, chat templates"
  - "ft_train.py.j2 template with QLoRA, LoRA, SFTTrainer, perplexity/ROUGE eval"
  - "10 FT-specific CLAUDE.md protocol rules"
affects: [05-domain-plugins-swarm]

# Tech tracking
tech-stack:
  added: [peft, trl, bitsandbytes, transformers (lazy-imported)]
  patterns: [QLoRA 4-bit NF4, adapter-only saving, chat template formatting, gradient checkpointing]

key-files:
  created:
    - src/mlforge/finetuning/__init__.py
    - src/mlforge/finetuning/prepare.py
    - src/mlforge/templates/ft_train.py.j2
    - tests/mlforge/test_ft_plugin.py
  modified: []

key-decisions:
  - "All peft/trl/bitsandbytes imports lazy (in-method) to avoid requiring GPU deps at import time"
  - "prepare.py uses module-level transformers imports but is standalone (never imported by mlforge core)"
  - "LoRA config uses all-linear target modules for broad adapter coverage"
  - "Template variables stored as Python constants (LORA_R, LORA_ALPHA) for readability in rendered train.py"

patterns-established:
  - "FT plugin follows same scaffold pattern as TabularPlugin: copy frozen prepare.py + render mutable train.py from Jinja2 template"
  - "VRAM detection with quantization recommendation threshold at 16GB"
  - "Chat template formatting via tokenizer.apply_chat_template() for all datasets"

requirements-completed: [FT-01, FT-02, FT-03, FT-04, FT-05]

# Metrics
duration: 5min
completed: 2026-03-20
---

# Phase 05 Plan 02: Fine-Tuning Plugin Summary

**FineTuningPlugin with QLoRA 4-bit quantization, SFTTrainer, perplexity/ROUGE eval, and lazy-imported GPU deps**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-20T02:30:54Z
- **Completed:** 2026-03-20T02:36:11Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- FineTuningPlugin passes DomainPlugin Protocol checks, registers in plugin registry, validates FT metrics and model_name
- Frozen prepare.py with get_vram_info() (GPU detection + quantization recommendation), format_dataset() (JSON/JSONL/CSV + chat templates), create_train_eval_split() (90/10 reproducible split)
- ft_train.py.j2 renders full QLoRA training script with BitsAndBytesConfig (NF4 4-bit), LoRA adapters, SFTTrainer, gradient checkpointing, perplexity and ROUGE evaluation, adapter-only saving, JSON metric output
- 40 tests covering all plugin functionality, all passing with mocked heavy deps (no GPU required)

## Task Commits

Each task was committed atomically:

1. **Task 1: FineTuningPlugin class + registry + tests** - `ab8c8bc` (feat)
2. **Task 2: Frozen prepare.py with VRAM/dataset/split** - `f369f33` (feat)
3. **Task 3: ft_train.py.j2 template with QLoRA + SFTTrainer** - `7167672` (feat)

## Files Created/Modified
- `src/mlforge/finetuning/__init__.py` - FineTuningPlugin class implementing DomainPlugin Protocol
- `src/mlforge/finetuning/prepare.py` - Frozen dataset pipeline with VRAM detection, chat template formatting, train/eval splits
- `src/mlforge/templates/ft_train.py.j2` - Jinja2 template for mutable train.py with QLoRA, SFTTrainer, evaluation
- `tests/mlforge/test_ft_plugin.py` - 40 tests for FT plugin, prepare.py, and template rendering

## Decisions Made
- All peft/trl/bitsandbytes imports are lazy (inside methods) so importing mlforge.finetuning works without GPU deps
- prepare.py uses module-level transformers imports since it is a standalone file copied during scaffold, never imported by mlforge core
- LoRA config targets all-linear modules for maximum adapter coverage
- Template variables rendered as Python constants (LORA_R = 16) for readable generated train.py

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- FineTuningPlugin ready for registration alongside TabularPlugin and DeepLearningPlugin
- Template renders valid Python for any model_name/lora_r/lora_alpha combination
- pyproject.toml `ft` optional dependency group is handled by Plan 01

---
*Phase: 05-domain-plugins-swarm*
*Completed: 2026-03-20*
