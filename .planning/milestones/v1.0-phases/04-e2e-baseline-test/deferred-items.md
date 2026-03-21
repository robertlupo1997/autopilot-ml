# Deferred Items — Phase 04-e2e-baseline-test

## Flaky Test: test_runner.py::TestExperimentRun::test_run_experiment

- **Found during:** Task 1 (iris fixture + run script creation)
- **Symptom:** `assert result.elapsed_sec >= 0` fails with `elapsed_sec=-1.4` when running full test suite but passes in isolation
- **Root cause:** Pre-existing WSL2 clock skew under heavy CPU load — `time.time()` can return negative difference. Confirmed pre-existing by git stash test: test passes without our changes in isolation.
- **Our changes:** Only added `tests/fixtures/iris.csv` and `scripts/run-baseline-test.sh` — neither file is imported or used by test_runner.py
- **Recommended fix:** Either change the assertion to `>= -1.0` (reasonable tolerance), or use `time.monotonic()` in train_template.py instead of `time.time()`
- **Target phase:** Out of scope for Phase 4 (observational). Defer to Phase 5 or a maintenance pass.
