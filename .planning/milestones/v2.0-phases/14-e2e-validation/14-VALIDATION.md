---
phase: 14
slug: e2e-validation
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-14
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (installed) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q --ignore=tests/test_e2e.py`
- **After Task 2 (human gate):** No automated test — human provides run output
- **Before `/gsd:verify-work`:** Full suite must be green + FINDINGS.md populated
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | EVAL-01 | smoke | `uv run pytest tests/test_phase14_validation.py::TestForecastValidationHarnessScript -x -q` | ✅ | ✅ green |
| 14-01-02 | 01 | 1 | EVAL-01 | manual | Inspect run.log json_output after human run — FINDINGS.md populated with beats_seasonal_naive=True | N/A | ✅ green |
| 14-01-03 | 01 | 1 | EVAL-02 | manual | Count results.tsv rows after human run — FINDINGS.md shows 7 experiments, 2 keep decisions | N/A | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Notes:*
- *14-01-01: The original plan specified `bash -n scripts/run-forecast-validation-test.sh` as the smoke test command. The implemented smoke test `TestForecastValidationHarnessScript::test_script_passes_bash_syntax_check` calls `bash -n` internally and provides broader coverage (9 tests total in the class). Both are equivalent.*
- *14-01-02 and 14-01-03 are manual requirements (autonomous claude -p run). Validation run was executed by the user on 2026-03-14. Results documented in FINDINGS.md: EVAL-01 PASSED (Ridge MAPE 0.029 < seasonal naive 0.061), EVAL-02 PASSED (7 experiments, 2 keep decisions, 0 frozen file violations).*

---

## Wave 0 Requirements

- [x] `tests/fixtures/quarterly_revenue.csv` — 40-quarter synthetic dataset (40 rows, `quarter` + `revenue` columns, seed=42)
- [x] `scripts/run-forecast-validation-test.sh` — E2E harness script (executable, passes bash -n, --date-column quarter, both frozen file checks, EVAL-01/EVAL-02 assertions)

*Existing 330 tests cover all src/ modules; no gaps in unit infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Result |
|----------|-------------|------------|-------------------|--------|
| Agent beats seasonal naive MAPE | EVAL-01 | Requires autonomous claude -p run | Run harness, check beats_seasonal_naive in json_output | PASSED (0.029 < 0.061) |
| At least 5 experiments with 1+ keep | EVAL-02 | Requires autonomous claude -p run | Count results.tsv rows and status values | PASSED (7 expts, 2 keeps) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved

---

## Validation Audit

**Audit date:** 2026-03-15
**Auditor:** GSD Nyquist Auditor

| Metric | Value |
|--------|-------|
| Total task IDs | 3 |
| Automated tests found | 1/1 automated tasks |
| Automated tests passing | 1/1 |
| Manual verifications documented | 2/2 (in FINDINGS.md) |
| Gaps filled | 0 (all pre-existing) |
| Gaps remaining | 0 |

Automated coverage: `TestQuarterlyRevenueFixture` (6 tests) + `TestForecastValidationHarnessScript` (9 tests) in `tests/test_phase14_validation.py` — 15 tests all passing. Manual EVAL-01 and EVAL-02 requirements met per the human-executed validation run documented in `FINDINGS.md` (Ridge MAPE 0.029 < seasonal naive 0.061; 7 experiments, 2 keep decisions; 0 frozen file violations; 0 permission denials). Full suite: 330 passed.
