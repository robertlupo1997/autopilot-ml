---
phase: 03-scaffold-cli-run-engine
verified: 2026-03-19T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 3: Scaffold, CLI + Run Engine Verification Report

**Phase Goal:** Users can install mlforge, run it from the command line, and it orchestrates the full experiment loop with guardrails for unattended overnight execution
**Verified:** 2026-03-19
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                          | Status     | Evidence                                                                           |
|----|-----------------------------------------------------------------------------------------------|------------|------------------------------------------------------------------------------------|
| 1  | User can pip install mlforge and run `mlforge <dataset> <goal>` to start a session            | VERIFIED   | `pyproject.toml` defines `mlforge = "mlforge.cli:main"` entry point; `cli.py` parses positional `dataset` + `goal` args and validates dataset exists |
| 2  | Run engine executes fresh-context-per-iteration loops, keeping improvements and reverting failures | VERIFIED | `engine.py` RunEngine spawns `claude -p` per iteration via `subprocess.run`, routes results through `DeviationHandler.handle()` → keep/revert/retry/stop |
| 3  | Deviation handling auto-recovers from crashes, OOM, and divergence without human intervention  | VERIFIED   | `guardrails.py` DeviationHandler: OOM → retry (max 2), crash/timeout → revert, non-finite metric → revert, no improvement → revert, improvement → keep |
| 4  | Resource guardrails enforce cost caps, time limits, disk usage, and per-experiment timeouts    | VERIFIED   | `guardrails.py` ResourceGuardrails checks 4 hard stops: `experiment_count >= budget_experiments`, `cost_spent_usd >= budget_usd`, elapsed >= `budget_minutes * 60`, free disk < 1.0 GB |
| 5  | Live terminal output shows current experiment number, best metric, and remaining budget        | VERIFIED   | `progress.py` LiveProgress renders rich Table with Experiment count, Best Metric (N/A when None), Cost (`$x.xx/$y.xx`), Keeps/Reverts, Status |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact                         | Expected                                          | Status     | Details                                                              |
|----------------------------------|---------------------------------------------------|------------|----------------------------------------------------------------------|
| `src/mlforge/cli.py`             | CLI entry point with argparse                     | VERIFIED   | 126 lines; argparse `main(argv)` with full arg set; scaffold + engine wiring; --resume support |
| `src/mlforge/scaffold.py`        | Experiment directory scaffolding via plugin system | VERIFIED   | 120 lines; `scaffold_experiment()` wires plugin, templates, hooks, dataset copy, TOML |
| `src/mlforge/guardrails.py`      | ResourceGuardrails, CostTracker, DeviationHandler | VERIFIED   | 139 lines; all three classes implemented with full behavioral logic  |
| `src/mlforge/progress.py`        | LiveProgress terminal display                     | VERIFIED   | 85 lines; rich Table, start/stop lifecycle, context manager          |
| `src/mlforge/engine.py`          | RunEngine class orchestrating experiment loop     | VERIFIED   | 211 lines; run(), _run_one_experiment(), _process_result(), _build_prompt(), SIGINT handling |
| `src/mlforge/state.py`           | SessionState with cost_spent_usd field            | VERIFIED   | `cost_spent_usd: float = 0.0` present; round-trips through to_json/from_json via asdict |
| `src/mlforge/config.py`          | Config with budget/timeout/model fields           | VERIFIED   | budget_usd, per_experiment_timeout_sec, per_experiment_budget_usd, max_turns_per_experiment, model all present with correct defaults |

### Key Link Verification

| From                        | To                           | Via                                               | Status  | Details                                                              |
|-----------------------------|------------------------------|---------------------------------------------------|---------|----------------------------------------------------------------------|
| `cli.py`                    | `scaffold.py`                | `scaffold_experiment()` call                      | WIRED   | Line 96: `scaffold_experiment(config=config, dataset_path=..., target_dir=..., run_id=...)` |
| `scaffold.py`               | `plugins.py`                 | `get_plugin()` + `plugin.scaffold()`              | WIRED   | Lines 96, 99: `plugin = get_plugin(config.domain)` then `plugin.scaffold(target_dir, config)` |
| `scaffold.py`               | `hooks.py`                   | `write_hook_files()` for frozen enforcement       | WIRED   | Line 110: `write_hook_files(target_dir, plugin.frozen_files)` |
| `engine.py`                 | `guardrails.py`              | `ResourceGuardrails.should_stop()` per iteration  | WIRED   | Line 68: `not self.guardrails.should_stop(self.state)` in loop condition |
| `engine.py`                 | `guardrails.py`              | `DeviationHandler.handle()` for result processing | WIRED   | Line 162: `action = self.deviation.handle(result_for_handler, self.state)` |
| `engine.py`                 | `guardrails.py`              | `CostTracker.record()` after each experiment      | WIRED   | Line 150: `self.cost_tracker.record(cost, self.state)` |
| `engine.py`                 | `checkpoint.py`              | `save_checkpoint()` before each experiment        | WIRED   | Lines 71, 79: `save_checkpoint(self.state, self._checkpoint_dir)` pre-loop and in finally |
| `engine.py`                 | `git_ops.py`                 | `commit_experiment` / `revert_to_last_commit`     | WIRED   | Lines 165, 176: `self.git.commit_experiment(...)` on keep; `self.git.revert_to_last_commit()` on revert |
| `engine.py`                 | `progress.py`                | `LiveProgress` context manager                    | WIRED   | Lines 45, 65: `self.progress = LiveProgress(...)` and `with self.progress:` |
| `cli.py`                    | `engine.py`                  | `RunEngine(...)` + `.run()`                       | WIRED   | Lines 109-110: `engine = RunEngine(target_dir, config, state)` then `engine.run()` |
| `guardrails.py`             | `state.py`                   | `SessionState.cost_spent_usd`                     | WIRED   | Line 74 of guardrails.py: `state.cost_spent_usd = self._total` |
| `guardrails.py`             | `config.py`                  | `Config` budget fields                            | WIRED   | Lines 39, 44, 50: `self.config.budget_experiments`, `.budget_usd`, `.budget_minutes` |
| `progress.py`               | `state.py`                   | `experiment_count`, `best_metric`, `cost_spent_usd` | WIRED | Lines 59, 63, 67: all three state fields rendered in Table |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                   | Status    | Evidence                                                                    |
|-------------|-------------|-------------------------------------------------------------------------------|-----------|-----------------------------------------------------------------------------|
| CORE-01     | 03-01       | User can install mlforge via pip and run `mlforge <dataset> <goal>`           | SATISFIED | `pyproject.toml` entry point + argparse CLI in `cli.py`                     |
| CORE-02     | 03-03       | Agent executes keep/revert experiment loop                                    | SATISFIED | `engine.py` RunEngine keep/revert routing in `_process_result()`            |
| CORE-09     | 03-02       | Deviation handling auto-recovers from crashes, OOM, and divergence            | SATISFIED | `DeviationHandler.handle()` routes OOM→retry, crash→revert, divergence→revert |
| GUARD-01    | 03-01       | Frozen file zone enforcement prevents agent from modifying infrastructure files | SATISFIED | `hooks.py` `write_hook_files()` generates `.claude/settings.json` deny rules + `guard-frozen.sh` (chmod 755) |
| GUARD-02    | 03-02       | Resource guardrails enforce cost caps, GPU limits, disk usage boundaries      | SATISFIED | `ResourceGuardrails.should_stop()` checks 4 conditions with hard stops      |
| GUARD-03    | 03-03       | Crash recovery automatically saves state before each experiment               | SATISFIED | `save_checkpoint()` called before every loop iteration and in finally block |
| GUARD-04    | 03-02       | Live progress monitoring shows current experiment, best metric, budget remaining | SATISFIED | `LiveProgress` rich Table renders all three values continuously              |
| GUARD-05    | 03-02       | Cost tracking records API token usage per experiment with running total and budget cap | SATISFIED | `CostTracker.record()` accumulates costs and syncs to `SessionState.cost_spent_usd` |
| INTL-07     | 03-02       | Experiment time/cost budget with per-experiment timeout and total session budget | SATISFIED | `Config` has `per_experiment_timeout_sec` + `budget_usd`; `ResourceGuardrails` enforces both; subprocess timeout passed to `subprocess.run` |

**All 9 required IDs satisfied. No orphaned requirements for Phase 3.**

### Anti-Patterns Found

None detected. Scanned `cli.py`, `scaffold.py`, `guardrails.py`, `progress.py`, `engine.py` for TODO/FIXME/placeholder comments, empty return stubs, and console.log-only handlers. All implementations are substantive.

### Human Verification Required

#### 1. Actual `mlforge` Binary on PATH

**Test:** Install mlforge in a clean virtualenv (`pip install -e .`), then run `mlforge --help`
**Expected:** Prints argparse usage and returns 0
**Why human:** Entry point wiring in pyproject.toml cannot be confirmed to produce a working binary without actually installing the package

#### 2. Overnight Run Termination on Cost Cap

**Test:** Run `mlforge data.csv "predict x" --budget-usd 0.01` against a live Claude endpoint
**Expected:** Session stops cleanly after the first experiment exceeds $0.01, printing a summary
**Why human:** Requires a real claude -p subprocess response with `total_cost_usd` in JSON; cannot simulate exact API cost behavior in tests

#### 3. guard-frozen.sh Live Hook Enforcement

**Test:** In a scaffolded directory, attempt to edit `prepare.py` with Claude Code running with the generated `.claude/settings.json`
**Expected:** Claude Code denies the edit and outputs a deny reason message
**Why human:** Hook enforcement requires actual Claude Code tool invocation; cannot be verified purely from file contents

### Gaps Summary

No gaps. All 5 observable truths pass at all three levels (exists, substantive, wired). All 9 requirement IDs have verified implementation evidence. Full test suite passes 269 tests (including 116 tests covering Phase 3 files directly).

---

_Verified: 2026-03-19_
_Verifier: Claude (gsd-verifier)_
