---
phase: 13
slug: scaffold-and-cli-updates
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (installed) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_cli.py tests/test_scaffold.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_cli.py tests/test_scaffold.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | SCAF-01 | unit | `uv run pytest tests/test_cli.py::TestCliDateColumnFlag -x -q` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | SCAF-02 | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting -x -q` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 1 | SCAF-02 | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldStandardPathUnchanged -x -q` | ❌ W0 | ⬜ pending |
| 13-01-04 | 01 | 1 | SCAF-03 | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting::test_forecast_program_md_naive_mape -x -q` | ❌ W0 | ⬜ pending |
| 13-01-05 | 01 | 1 | SCAF-03 | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldForecasting::test_forecast_program_md_seasonal_naive_mape -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli.py` — add `TestCliDateColumnFlag` class (new class in existing file)
- [ ] `tests/test_scaffold.py` — add `TestScaffoldForecasting` and `TestScaffoldStandardPathUnchanged` classes

*No new test files needed — all new tests go in existing test files.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
