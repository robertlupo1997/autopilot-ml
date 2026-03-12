---
phase: 4
slug: e2e-baseline-test
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths=["tests"] |
| **Quick run command** | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q --ignore=tests/test_e2e.py`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | scaffold iris | smoke | `uv run automl iris.csv species accuracy` | ✅ | ⬜ pending |
| 04-01-02 | 01 | 1 | train.py runs | smoke | `cd experiment-iris && uv run python train.py` | ✅ | ⬜ pending |
| 04-01-03 | 01 | 1 | existing tests pass | regression | `uv run pytest tests/ -q` | ✅ | ⬜ pending |
| 04-01-04 | 01 | 1 | FINDINGS.md exists | artifact | `test -f .planning/phases/04-e2e-baseline-test/FINDINGS.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_e2e_baseline.py` — smoke test that scaffolds iris.csv, runs train.py once, verifies structured output
- Existing infrastructure covers regression testing (111 tests passing)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| claude -p loop runs E2E | Phase goal | Cannot run `claude -p` inside Claude Code session | Run shell script outside CC; inspect output JSON |
| Agent follows redirect rule | Observational | Agent behavior not deterministic | Check if `run.log` exists and stdout not flooded |
| Frozen file compliance | Observational | Agent behavior not deterministic | `git diff HEAD -- prepare.py` after run |
| Multi-draft generation | Observational | Agent behavior not deterministic | Count unique algorithms in `results.tsv` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
