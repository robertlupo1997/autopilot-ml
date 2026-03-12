---
phase: 6
slug: structured-output-and-metrics-parsing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths=["tests"] |
| **Quick run command** | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q --ignore=tests/test_e2e.py`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | STRUCT-01 | unit | `uv run pytest tests/test_train.py -q -k "json_output"` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | STRUCT-01 | unit | `uv run pytest tests/test_runner.py -q -k "json_output"` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | STRUCT-02 | unit | `uv run pytest tests/test_parse_run_result.py -q` | ❌ W0 | ⬜ pending |
| 06-XX-XX | all | all | regression | regression | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_train.py` — Add `test_json_output_present` and `test_json_output_parseable` stubs
- [ ] `tests/test_runner.py` — Add `test_parse_json_output_present` and `test_parse_json_output_missing` stubs
- [ ] `tests/test_parse_run_result.py` — New test file covering `parse_run_result.py` script behavior
- [ ] `scripts/` directory — Create if not exists

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Existing grep parsing still works in scaffolded project | STRUCT-01 | Requires live scaffolded experiment | Scaffold a test project, run train.py, verify `grep "^metric_value:" run.log` still works |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
