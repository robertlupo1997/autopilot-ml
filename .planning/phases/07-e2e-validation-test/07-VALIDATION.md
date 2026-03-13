---
phase: 7
slug: e2e-validation-test
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths=["tests"] |
| **Quick run command** | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~26 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q --ignore=tests/test_e2e.py`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green + FINDINGS.md populated
- **Max feedback latency:** 26 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | VAL-01 | smoke | `python -c "import pandas as pd; df=pd.read_csv('tests/fixtures/noisy.csv'); assert len(df)==300"` | ❌ W0 | ⬜ pending |
| 07-01-01 | 01 | 1 | VAL-02 | smoke | `bash -n scripts/run-validation-test.sh` | ❌ W0 | ⬜ pending |
| 07-01-01 | 01 | 1 | regression | regression | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` | ✅ | ⬜ pending |
| 07-01-02 | 01 | CP | VAL-03 | manual | Human runs script outside Claude Code | N/A | ⬜ pending |
| 07-01-03 | 01 | 1 | VAL-04 | manual+auto | `uv run python scripts/parse_run_result.py validation-run-output.json` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fixtures/noisy.csv` — Generate noisy classification dataset (flip_y=0.10, 300 rows)
- [ ] `scripts/run-validation-test.sh` — Validation test harness script

*Existing infrastructure covers parse_run_result.py (Phase 6) and all src/ module tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full autonomous loop runs unattended | VAL-03 | Requires live `claude -p` execution outside Claude Code | Run `scripts/run-validation-test.sh` in separate terminal, observe completion |
| stop_reason is end_turn or max_turns | VAL-04 | Requires live run output | Inspect validation-run-output.json after human run |
| Hook fires on prepare.py write attempt | VAL-05 | Agent may not trigger hook (acceptable) | Check permission_denials in output JSON |
| json_output line present in run.log | VAL-06 | Requires live scaffolded experiment | Inspect run.log in experiment directory |
| Stagnation triggers strategy shift | VAL-07 | Depends on agent behavior over 50 turns | Count consecutive reverts in results.tsv |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 26s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
