# Phase 4: E2E Baseline Test -- Findings

**Date:** 2026-03-11
**Dataset:** iris.csv (150 rows, 4 features, 3-class classification)
**Target metric:** accuracy
**Max turns:** 30
**Budget cap:** $2.00
**Model:** claude-opus-4-6

## Run Summary

| Field | Value |
|-------|-------|
| stop_reason | tool_use (hit max_turns mid-action) |
| num_turns | 31 |
| total_cost_usd | $0.854 |
| experiments_run | 9 (5 drafts + 4 iterations) |
| best_metric | 0.980000 (SVC C=50 rbf kernel, iteration 7) |
| frozen_file_compliance | PASSED — prepare.py unchanged |

## Observations

### Draft Phase

- [x] 3-5 drafts generated
- [x] Different algorithm families used
- [x] Best draft selected correctly
- [x] Draft results logged in results.tsv
- Notes: 5 drafts ran across distinct algorithm families: LogisticRegression, RandomForestClassifier (n_estimators=200), SVC (rbf), XGBClassifier (default), LGBMClassifier (default). LogisticRegression scored highest at 0.966667 and was selected as best draft. All draft results appear in results.tsv with correct status values (draft-keep / draft-discard).

### Keep/Revert Cycle

- [x] Git commits on keep
- [x] Git reset on revert
- [x] Metric comparison working (strict greater-than)
- Notes: Two keeps recorded (iterations 6 and 7: SVC C=10 then C=50). Two reverts recorded (iterations 8 and 9: SVC C=100 regressed, SVC C=50 gamma=0.1 also reverted). Git log confirms commits exist for both keep iterations. Revert iterations have no git commit, consistent with reset behavior. Metric comparison is strict: iteration 8 (0.973333) was correctly identified as worse than iteration 7 (0.980000) and reverted.

### Metric Parsing

- [x] `grep "^metric_value:"` returned float values
- [x] No formatting regressions (spacing, case)
- [x] run.log captured properly (not inline)
- Notes: run.log tail shows metric_value printed correctly as `0.973333` with 6 decimal places. Metric labels (metric_name, metric_value, metric_std, direction, elapsed_sec, model) all formatted correctly. Output was redirected to run.log with no context flooding observed. One minor diagnostic bug: the run-baseline-test.sh parser grabbed the metric_std column instead of metric_value when summarizing best_metric (this is a script-level display bug only, not a loop bug).

### Frozen File Compliance

- [x] prepare.py never modified
- [x] Only train.py edited
- Notes: `git diff HEAD -- prepare.py` returned empty. The agent correctly operated only within the mutable zone (train.py). No hooks enforcement was needed — the CLAUDE.md instructions alone were sufficient to prevent prepare.py modification in this run.

### Context Management

- [x] Output redirected to run.log
- [x] No context flooding observed
- Notes: Claude invoked via `claude -p` with output captured to `baseline-run-output.json`. run.log captured subprocess output. No evidence of context flooding. The venv warning (`VIRTUAL_ENV does not match project environment path`) appeared in run.log but is cosmetic and did not affect behavior.

### Crash Recovery

- [x] Crashes detected and handled (if any occurred)
- [x] Consecutive crash counter working
- Notes: No crashes observed in this run. All 9 experiments completed successfully with valid metric values. The crash recovery machinery (consecutive_crashes counter, crash status in results.tsv) was not exercised.

### Stagnation Handling

- [x] Strategy shift after N reverts (if triggered)
- Notes: Not triggered in this run. The agent was still actively exploring (reverting C=100, trying gamma=0.1) when max_turns was reached. With only 4 post-draft iterations, stagnation threshold (5 consecutive reverts) was not hit. This is expected behavior for a 30-turn cap on a simple dataset.

### Permission / Tool Issues

- [x] All required tools (Bash, Edit, Read, Write) worked
- [x] No unexpected permission denials
- Notes: permission_denials array was empty. All tool calls (Bash, Edit, Read, Write) executed without restriction. The `--allowedTools "Bash Edit Read Write"` flag was sufficient.

## Issues Found

| # | Category | Severity | Description | Phase to Fix |
|---|----------|----------|-------------|--------------|
| 1 | Stop Behavior | Major | stop_reason is `tool_use` not `end_turn` — agent hit max_turns while executing a tool action, meaning it was interrupted mid-step rather than completing gracefully | 5 |
| 2 | Script Bug | Minor | run-baseline-test.sh diagnostics script parsed metric_std column instead of metric_value when displaying "best metric" summary | 5 |
| 3 | Venv Warning | Minor | VIRTUAL_ENV path mismatch warning appears in run.log on every uv invocation — cosmetic but noisy | 5 |
| 4 | Draft Selection | Observation | Agent selected LogisticRegression as best draft but then pivoted to SVC family for iterations — the switch was correct (SVC outperformed) but the reasoning path is opaque without structured logs | 6 |
| 5 | Turn Budget | Observation | 30-turn cap was insufficient to reach stagnation threshold (5 consecutive reverts). Only 4 post-draft iterations ran. Phase 7 validation should use 50+ turns to exercise stagnation logic | 7 |

## Recommendations for Phase 5-7

### Phase 5 (Hooks + Scaffolding)

- The CLAUDE.md instructions alone prevented prepare.py modification — hooks are a safety net, not a primary mechanism. Design hooks to be non-disruptive (warn/log rather than hard-fail) to avoid stopping a working loop.
- Fix the run-baseline-test.sh metric_std parsing bug before Phase 7 validation.
- Suppress or handle the VIRTUAL_ENV path mismatch warning (add `--active` flag to uv commands in train.py, or set VIRTUAL_ENV correctly in the scaffold environment).
- Consider adding a graceful shutdown signal or summary write step that runs even on max_turns interrupt, so results.tsv is always complete at termination.

### Phase 6 (Structured Output)

- The current metric parsing (`grep "^metric_value:"`) works reliably — no formatting regressions observed. JSON output is a quality-of-life improvement, not a correctness fix.
- Priority: Parse stop_reason and num_turns from baseline-run-output.json automatically to surface them in FINDINGS without manual extraction.
- The opaque draft-selection pivot (LogisticRegression -> SVC) suggests value in logging the agent's reasoning for each keep/revert decision — structured output would capture this.

### Phase 7 (Validation Test)

- Increase max_turns to 50+ to exercise the stagnation handling path (5+ consecutive reverts).
- Use a dataset where the best achievable accuracy is not trivially high (iris is near-perfect at 0.98) — consider a dataset with more noise to force genuine stagnation.
- Verify stop_reason is `end_turn` (graceful completion) rather than `tool_use` (mid-action interrupt).
- Re-verify frozen file compliance with an active hook (not just CLAUDE.md instructions).
- Confirm stagnation triggers a strategy category shift in the results.tsv description field.

## Raw Data

### results.tsv

```
iteration	metric_value	metric_std	elapsed_sec	status	description
1	0.966667	0.021082	2.2	draft-keep	LogisticRegression baseline
2	0.960000	0.024944	2.2	draft-discard	RandomForestClassifier n_estimators=200
3	0.966667	0.021082	1.2	draft-discard	SVC rbf kernel
4	0.946667	0.032660	3.0	draft-discard	XGBClassifier default
5	0.946667	0.032660	1.5	draft-discard	LGBMClassifier default
6	0.973333	0.024944	1.1	keep	SVC C=10 rbf kernel
7	0.980000	0.017889	1.1	keep	SVC C=50 rbf kernel
8	0.973333	0.024944	1.0	revert	SVC C=100 rbf kernel - overfitting
9	0.973333	0.024944	1.1	revert	SVC C=50 gamma=0.1
```

### git log

```
80b4a6d iter7: SVC C=50 rbf
a772902 iter6: SVC C=10 rbf
162a354 select best draft: LogisticRegression (0.966667)
459626f draft: LGBMClassifier
435fa27 draft: XGBClassifier
1033fd2 draft: SVC
72db166 draft: RandomForestClassifier
f1920dd initial scaffold
```

### baseline-run-output.json (key fields)

```json
{
  "stop_reason": "tool_use",
  "num_turns": 31,
  "total_cost_usd": 0.8544334999999997,
  "is_error": false,
  "permission_denials": [],
  "model": "claude-opus-4-6"
}
```
