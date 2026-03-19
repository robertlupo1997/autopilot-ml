---
phase: 1
slug: core-engine-plugin-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/ -x --ignore=tests/fixtures -q` |
| **Full suite command** | `python -m pytest tests/ --ignore=tests/fixtures -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x --ignore=tests/fixtures -q`
- **After every plan wave:** Run `python -m pytest tests/ --ignore=tests/fixtures -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | CORE-04 | unit | `pytest tests/test_state.py -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | CORE-10 | integration | `pytest tests/test_git_ops.py -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | CORE-05 | unit | `pytest tests/test_checkpoint.py -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | CORE-06 | unit | `pytest tests/test_config.py -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | CORE-03 | unit | `pytest tests/test_templates.py -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | CORE-03 | unit | `pytest tests/test_plugins.py -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | CORE-08 | unit | `pytest tests/test_journal.py -x` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | CORE-07 | unit | `pytest tests/test_hooks.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_state.py` — stubs for CORE-04 (SessionState JSON persistence)
- [ ] `tests/test_git_ops.py` — stubs for CORE-10 (GitPython branch/commit/revert/tag)
- [ ] `tests/test_checkpoint.py` — stubs for CORE-05 (checkpoint save/load/resume)
- [ ] `tests/test_config.py` — stubs for CORE-06 (TOML config loading with defaults)
- [ ] `tests/test_templates.py` — stubs for CORE-03 (Jinja2 template rendering)
- [ ] `tests/test_plugins.py` — stubs for CORE-03 (plugin protocol conformance)
- [ ] `tests/test_journal.py` — stubs for CORE-08 (JSONL journal append/load)
- [ ] `tests/test_hooks.py` — stubs for CORE-07 (hook settings generation, frozen guard)
- [ ] `tests/conftest.py` — shared fixtures (tmp dirs, mock repos, sample configs)
- [ ] New `src/mlforge/` package structure with `__init__.py`
- [ ] Updated `pyproject.toml` for mlforge package name and dependencies (gitpython, jinja2)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hook blocks file write in Claude Code | CORE-07 | Requires live Claude Code session | 1. Scaffold project 2. Attempt to edit frozen file in Claude Code 3. Verify denial message |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
