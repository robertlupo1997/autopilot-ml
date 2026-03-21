---
phase: 4
slug: e2e-baseline-test
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-11
audited: 2026-03-14
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths=["tests"] |
| **Quick run command** | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~40 seconds (237 tests) |

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
| 04-01-01 | 01 | 1 | iris.csv fixture exists with 150 rows + 5 columns | integration | `uv run pytest tests/test_e2e_baseline.py::test_iris_fixture_has_correct_shape -v` | ✅ | ✅ green |
| 04-01-02 | 01 | 1 | train.py runs and emits structured output | smoke | `uv run pytest tests/test_e2e.py -v` | ✅ | ✅ green |
| 04-01-03 | 01 | 1 | existing tests pass | regression | `uv run pytest tests/ -q` | ✅ | ✅ green |
| 04-01-04 | 01 | 1 | FINDINGS.md exists with Observations + Issues Found | artifact | `uv run pytest tests/test_e2e_baseline.py::test_findings_md_exists_with_required_sections -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_e2e_baseline.py` — artifact verification for iris.csv, run-baseline-test.sh, and FINDINGS.md (4 tests, all green)
- [x] `tests/test_e2e.py` — smoke tests that scaffold a project and run train.py; verify structured output (2 tests, all green)
- [x] Existing infrastructure covers regression testing (237 tests passing as of audit 2026-03-14)

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

- [x] All tasks have automated verify command
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test_e2e_baseline.py created, all green)
- [x] No watch-mode flags
- [x] Feedback latency < 20s for quick command
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** nyquist-auditor 2026-03-14
