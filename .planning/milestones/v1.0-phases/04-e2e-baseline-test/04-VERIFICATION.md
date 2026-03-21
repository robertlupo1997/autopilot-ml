---
phase: 04-e2e-baseline-test
verified: 2026-03-11T00:00:00Z
status: passed
score: 3/3 must-haves verified
re_verification: false
---

# Phase 4: E2E Baseline Test — Verification Report

**Phase Goal:** Run the autonomous loop as-is on a small test dataset (iris or synthetic), using `claude -p` with --max-turns, and document exactly what works and what breaks — draft generation, keep/revert decisions, frozen file compliance, metric parsing, stagnation handling
**Verified:** 2026-03-11
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A reproducible iris.csv test dataset exists for baseline testing | VERIFIED | `tests/fixtures/iris.csv` exists: 151 lines (header + 150 rows), columns: sepal_length, sepal_width, petal_length, petal_width, species |
| 2 | A self-contained shell script runs the full autonomous loop outside Claude Code | VERIFIED | `scripts/run-baseline-test.sh` exists, is executable (`chmod +x`), passes `bash -n` syntax check, contains `claude -p` invocation with `--max-turns 30`, `--max-budget-usd 2.00`, `--allowedTools "Bash Edit Read Write"`, and `--output-format json` |
| 3 | FINDINGS.md documents what works and what breaks in the autonomous loop | VERIFIED | `.planning/phases/04-e2e-baseline-test/FINDINGS.md` exists with all required sections (`## Observations`, `## Issues Found`, `## Recommendations for Phase 5-7`). All 19 observation checklist items are checked with empirical notes. 5 issues documented with severity and target phase. Raw results.tsv, git log, and JSON key fields are included. |

**Score:** 3/3 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/fixtures/iris.csv` | 150-row iris dataset with integer species target; contains "sepal_length" | VERIFIED | 151 lines (150 data rows + header). Header: `sepal_length,sepal_width,petal_length,petal_width,species`. Integer target column confirmed (values 0, 1, 2). |
| `scripts/run-baseline-test.sh` | E2E baseline test script with scaffold + git init + claude -p; contains "claude -p" | VERIFIED | File exists, is executable, passes bash syntax check. Contains `claude -p` (line 140) with multi-line continuation: `--max-turns 30`, `--max-budget-usd 2.00`, `--allowedTools "Bash Edit Read Write"`, `--output-format json`. |
| `.planning/phases/04-e2e-baseline-test/FINDINGS.md` | Structured findings from the baseline run; contains "## Observations" | VERIFIED | Contains `## Observations`, `## Issues Found`, `## Recommendations for Phase 5-7`, `## Run Summary`, and `## Raw Data`. All checklist items populated with real empirical data. No placeholder text or "skip" markers found. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scripts/run-baseline-test.sh` | `uv run automl` | CLI invocation to scaffold experiment | WIRED | Line 90: `uv run automl "$IRIS_CSV" species accuracy \` — correctly passes iris.csv, target column, and metric to the CLI |
| `scripts/run-baseline-test.sh` | `claude -p` | headless mode invocation with --allowedTools | WIRED | Line 140-145: `claude -p "..." --max-turns 30 --max-budget-usd 2.00 --allowedTools "Bash Edit Read Write" --output-format json`. The PLAN defined `pattern: "claude -p.*--allowedTools"` as a single-line regex, but the actual invocation uses multi-line bash continuation — the functional wiring is correct and complete. |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| E2E-BASELINE-01 | 04-01-PLAN.md | Test harness (iris fixture + run script) created for reproducible baseline testing | SATISFIED | `tests/fixtures/iris.csv` (150 rows, 4 features, integer target) and `scripts/run-baseline-test.sh` (executable, syntax-valid, full claude -p invocation) confirmed present |
| E2E-BASELINE-02 | 04-01-PLAN.md | Autonomous loop was invoked on iris dataset via `claude -p` with controlled flags; run completed | SATISFIED | FINDINGS.md contains empirical data: 9 experiments (5 drafts + 4 iterations), stop_reason=tool_use, num_turns=31, cost=$0.854. Raw results.tsv and git log included. Commits `c36cfd0` and `67f9e79` verified in git log. |
| E2E-BASELINE-03 | 04-01-PLAN.md | Structured findings document what works and what breaks, with issues mapped to future phases | SATISFIED | FINDINGS.md documents all 8 observation categories (draft phase, keep/revert, metric parsing, frozen file compliance, context management, crash recovery, stagnation, permissions). 5 issues table with severity (2 major, 3 observational) and target phases (5, 6, 7). Phase 5-7 recommendations are actionable. |

**Orphaned requirements check:** E2E-BASELINE-01, -02, -03 are defined exclusively in the ROADMAP.md (line 92) and 04-01-PLAN.md frontmatter. They do not appear in `.planning/REQUIREMENTS.md` — these are phase-local requirement IDs not tracked in the canonical requirements table. This is a documentation gap but not a goal achievement gap: the ROADMAP is the authoritative source for Phase 4 requirements and all three IDs are covered.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TODO/FIXME/placeholder comments found in any phase artifact. All checklist items in FINDINGS.md are checked (`[x]`). No unchecked `[ ]` items remain. No empty implementations or stub return values in the scripts.

---

### Human Verification Required

#### 1. Actual Claude Loop Behavior

**Test:** Review the `experiment-iris/baseline-run-output.json` file (if it still exists on disk) and confirm the results.tsv data matches what is reported in FINDINGS.md.
**Expected:** results.tsv shows 9 rows matching the table in FINDINGS.md (5 drafts, 4 iterations, best 0.980000 for SVC C=50).
**Why human:** The raw output file was produced outside this Claude Code session by a human-run command. The FINDINGS.md content is self-consistent but the source data file is not committed to git (it lives in the experiment-iris/ working directory which is transient). Verification of the source JSON would confirm the FINDINGS accurately reflect the actual run.

Note: This is a low-priority human check. The empirical data in FINDINGS.md is internally consistent (results.tsv row counts match git log commit counts, JSON fields match described behavior), making fabrication unlikely.

---

### Gaps Summary

No gaps found. All three must-have truths are verified, all three artifacts pass all three levels (exists, substantive, wired), both key links are functionally wired (the multi-line bash continuation for `claude -p ... --allowedTools` satisfies the intent of the PLAN key link even though a single-line regex wouldn't match it), and the existing test suite passes with 109 tests (no regressions introduced by the 2 new files).

The one structural note: E2E-BASELINE-01/02/03 requirement IDs are not defined in `.planning/REQUIREMENTS.md` — they exist only in ROADMAP.md and the plan frontmatter. This is a documentation convention issue, not a goal achievement failure. Phase 4 is observational and its requirements are self-contained to this phase.

**Phase 4 goal is achieved.** The baseline test ran to completion, produced empirical data on the autonomous loop's behavior across all 8 observation categories, identified 5 issues with severity ratings and target phase assignments, and provided actionable recommendations for Phases 5, 6, and 7.

---

_Verified: 2026-03-11_
_Verifier: Claude (gsd-verifier)_
