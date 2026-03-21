# v1.0 Finalization Prompt

Run with: `claude -p "$(cat .planning/finalize-v1.0.md)"`

---

You are finalizing the v1.0 milestone for mlforge. The milestone audit found 2 minor integration gaps and tech debt. All 48 requirements are satisfied. You need to create two gap-closure phases, plan and execute them, re-audit, and complete the milestone.

## Context

Read these files first:
- .planning/ROADMAP.md
- .planning/REQUIREMENTS.md
- .planning/v1.0-MILESTONE-AUDIT.md
- src/mlforge/cli.py

## Step 1: Create Phase 23 and Phase 24

### Phase 23: Add Missing CLI Flags

Add to ROADMAP.md after Phase 22:

**Goal**: Add --model-name and --direction CLI flags to close remaining integration gaps
**Depends on**: Phase 21
**Requirements**: FT-01, UX-01, CORE-06, UX-02
**Gap Closure**: Closes INT-FT-MODEL-NAME and INT-DIRECTION-FLAG from v1.0 audit

**Success Criteria:**
1. `--model-name` argparse argument added to CLI, passed through to `plugin_settings["model_name"]` for FT domain
2. `--direction` argparse argument added to CLI (choices: minimize, maximize), overrides auto-detected direction in config
3. `mlforge dataset goal --domain finetuning --model-name meta-llama/Llama-3.2-1B` works without argparse error
4. `mlforge dataset goal --metric rmse --direction minimize` correctly sets direction=minimize

### Phase 24: Tech Debt Cleanup

**Goal**: Remove dead code identified by v1.0 milestone audit
**Depends on**: Phase 23
**Requirements**: None (tech debt)

**Success Criteria:**
1. `SessionState.to_json()` and `SessionState.from_json()` removed (checkpoint.py uses `dataclasses.asdict()`)
2. `temporal_split()` removed from `tabular/prepare.py` (never called)
3. Unused `ALGORITHM_FAMILIES` import removed from `engine.py` line 23 (only `get_families_for_domain` is used)
4. All existing tests still pass after dead code removal
5. No new test failures introduced

Do NOT touch:
- dl_train.py.j2 intentional TODOs (by design)
- Old automl module test files (legacy, out of scope)

### Actions for Step 1:
1. Add both phases to ROADMAP.md with the details above
2. Create directories: `.planning/phases/23-add-missing-cli-flags/` and `.planning/phases/24-tech-debt-cleanup/`
3. Commit: `docs(roadmap): add gap closure phases 23-24`

## Step 2: Plan Phase 23

Create `.planning/phases/23-add-missing-cli-flags/23-01-PLAN.md` with:

**Files to modify:**
- `src/mlforge/cli.py` — add `--model-name` and `--direction` argparse arguments
- `src/mlforge/cli.py` — wire arguments to config/plugin_settings in the run flow

**Implementation:**
1. Add `--model-name` argument: `parser.add_argument("--model-name", type=str, default=None, help="HuggingFace model name for fine-tuning domain")`
2. Add `--direction` argument: `parser.add_argument("--direction", choices=["minimize", "maximize"], default=None, help="Metric optimization direction override")`
3. In the CLI run flow, if `args.model_name` is set, add it to `plugin_settings["model_name"]`
4. In the CLI run flow, if `args.direction` is set, override `config.direction` with the value

**Tests:**
- Test `--model-name` is accepted by argparse and appears in plugin_settings
- Test `--direction minimize` sets config.direction to "minimize"
- Test `--direction maximize` sets config.direction to "maximize"
- Test default behavior unchanged when flags not provided

Commit: `docs(phase-23): plan CLI flag additions`

## Step 3: Execute Phase 23

Implement the plan from Step 2:

1. Read `src/mlforge/cli.py` to understand current argparse setup and run flow
2. Add the two arguments to the argument parser
3. Wire them into the run flow (look for where plugin_settings and config are set up)
4. Add tests in the appropriate test file (likely `tests/test_cli.py`)
5. Run `python -m pytest tests/ -x -q` to verify all tests pass
6. Commit: `feat(phase-23): add --model-name and --direction CLI flags`
7. Create `.planning/phases/23-add-missing-cli-flags/23-VERIFICATION.md` confirming success criteria met

## Step 4: Plan Phase 24

Create `.planning/phases/24-tech-debt-cleanup/24-01-PLAN.md` with:

**Files to modify:**
- `src/mlforge/state.py` (or wherever SessionState lives) — remove `to_json()` and `from_json()`
- `src/mlforge/tabular/prepare.py` — remove `temporal_split()`
- `src/mlforge/engine.py` — remove unused `ALGORITHM_FAMILIES` import on line 23

**Implementation:**
1. grep for `to_json` and `from_json` on SessionState to confirm they're unused
2. grep for `temporal_split` to confirm it's unused
3. grep for `ALGORITHM_FAMILIES` in engine.py to confirm only `get_families_for_domain` is used
4. Remove each dead code item
5. Run full test suite to confirm no regressions

Commit: `docs(phase-24): plan tech debt cleanup`

## Step 5: Execute Phase 24

1. Verify each item is truly dead code by grepping for usage
2. Remove dead code items one at a time
3. Run `python -m pytest tests/ -x -q` after each removal
4. Commit: `refactor(phase-24): remove dead code (to_json, from_json, temporal_split, unused import)`
5. Create `.planning/phases/24-tech-debt-cleanup/24-VERIFICATION.md` confirming success criteria met

## Step 6: Re-Audit

Run the equivalent of `/gsd:audit-milestone`:

1. Count requirements: all 48 should still be [x] in REQUIREMENTS.md
2. Verify integration gaps closed:
   - INT-FT-MODEL-NAME: grep for `--model-name` in cli.py — should exist
   - INT-DIRECTION-FLAG: grep for `--direction` in cli.py — should exist
3. Verify broken flow fixed: "FT with explicit --model-name" should now work
4. Verify tech debt reduced: grep for removed dead code — should be gone
5. Run `python -m pytest tests/ -x -q` — all tests pass
6. Update `.planning/v1.0-MILESTONE-AUDIT.md` frontmatter:
   - `status: passed` (was `tech_debt`)
   - `scores.integration: 48/48` (was `46/48`)
   - `scores.flows: 9/9` (was `8/9`)
   - Remove the two integration gap entries
   - Remove the dead code tech debt entries
7. Commit: `docs(audit): v1.0 re-audit passed — all gaps closed`

## Step 7: Update REQUIREMENTS.md

Update the coverage section:
```
- Satisfied: 48
- Pending (gap closure): 0
```

Commit with the audit update if not already included.

## Step 8: Final Summary

Print a summary of what was done:
- Phases created and executed
- Tests passing count
- Integration gaps closed
- Tech debt removed
- Milestone status

## Rules

- Read files before modifying them
- Run tests after every code change
- Do not modify files not listed in the plans
- Do not add features beyond what's specified
- If tests fail, fix the issue before proceeding
- Use atomic commits at each step boundary
