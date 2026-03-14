---
phase: 14
slug: e2e-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 14-01-01 | 01 | 1 | EVAL-01 | smoke | `bash -n scripts/run-forecast-validation-test.sh` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | EVAL-01 | manual | Inspect run.log json_output after human run | N/A | ⬜ pending |
| 14-01-03 | 01 | 1 | EVAL-02 | manual | Count results.tsv rows after human run | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fixtures/quarterly_revenue.csv` — synthetic 40-quarter dataset
- [ ] `scripts/run-forecast-validation-test.sh` — E2E harness script

*Existing 315 tests cover all src/ modules; no gaps in unit infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Agent beats seasonal naive MAPE | EVAL-01 | Requires autonomous claude -p run | Run harness, check beats_seasonal_naive in json_output |
| At least 5 experiments with 1+ keep | EVAL-02 | Requires autonomous claude -p run | Count results.tsv rows and status values |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
