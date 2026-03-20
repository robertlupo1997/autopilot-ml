---
phase: 3
slug: scaffold-cli-run-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/mlforge/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/mlforge/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | CORE-01 | unit | `python -m pytest tests/mlforge/test_cli.py -x` | No - W0 | pending |
| 03-01-02 | 01 | 1 | GUARD-01 | unit | `python -m pytest tests/mlforge/test_scaffold.py -x` | No - W0 | pending |
| 03-02-01 | 02 | 1 | CORE-02 | unit | `python -m pytest tests/mlforge/test_engine.py -x` | No - W0 | pending |
| 03-02-02 | 02 | 1 | GUARD-03 | unit | `python -m pytest tests/mlforge/test_engine.py::test_checkpoint_before_experiment -x` | No - W0 | pending |
| 03-02-03 | 02 | 1 | CORE-09 | unit | `python -m pytest tests/mlforge/test_guardrails.py::test_deviation_handler -x` | No - W0 | pending |
| 03-03-01 | 03 | 2 | GUARD-02 | unit | `python -m pytest tests/mlforge/test_guardrails.py::test_resource_guardrails -x` | No - W0 | pending |
| 03-03-02 | 03 | 2 | GUARD-05 | unit | `python -m pytest tests/mlforge/test_guardrails.py::test_cost_tracker -x` | No - W0 | pending |
| 03-03-03 | 03 | 2 | INTL-07 | unit | `python -m pytest tests/mlforge/test_guardrails.py::test_budget_enforcement -x` | No - W0 | pending |
| 03-03-04 | 03 | 2 | GUARD-04 | unit | `python -m pytest tests/mlforge/test_progress.py -x` | No - W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_cli.py` — stubs for CORE-01 (CLI parsing, help, missing args)
- [ ] `tests/mlforge/test_scaffold.py` — stubs for GUARD-01 (scaffold output structure, hook files)
- [ ] `tests/mlforge/test_engine.py` — stubs for CORE-02, GUARD-03 (run engine with mocked subprocess)
- [ ] `tests/mlforge/test_guardrails.py` — stubs for CORE-09, GUARD-02, GUARD-05, INTL-07
- [ ] `tests/mlforge/test_progress.py` — stubs for GUARD-04 (LiveProgress rendering)
- [ ] `tests/mlforge/conftest.py` — shared fixtures (mock claude -p responses, tmp experiment dirs)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live terminal display looks correct | GUARD-04 | Visual rendering cannot be automated | Run `mlforge` on sample dataset, verify table updates in terminal |
| pip install + CLI entry point works | CORE-01 | End-to-end install requires clean venv | `pip install -e .` then `mlforge --help` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
