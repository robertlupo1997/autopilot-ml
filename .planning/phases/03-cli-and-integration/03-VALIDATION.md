---
phase: 3
slug: cli-and-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | CLI-01 | integration | `uv run pytest tests/test_scaffold.py::test_scaffold_creates_all_files -x` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | CLI-02 | unit | `uv run pytest tests/test_cli.py::test_cli_argument_parsing -x` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 1 | CLI-03 | integration | `uv run pytest tests/test_scaffold.py::test_scaffold_file_contents -x` | ❌ W0 | ⬜ pending |
| 3-01-04 | 01 | 1 | CLI-04 | integration | `uv run pytest tests/test_scaffold.py::test_scaffolded_project_runs -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scaffold.py` — stubs for CLI-01, CLI-03, CLI-04
- [ ] `tests/test_cli.py` — stubs for CLI-02
- [ ] Test fixture: small CSV for scaffold testing (reuse from conftest.py)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E2E: scaffold + autonomous loop improves beyond baseline | Success Criterion 3 | Requires Claude Code agent to run loop | Scaffold project, run claude with CLAUDE.md, verify results.tsv shows improvement |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 25s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
