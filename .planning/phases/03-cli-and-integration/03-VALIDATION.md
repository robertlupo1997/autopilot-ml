---
phase: 3
slug: cli-and-integration
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-10
audited: 2026-03-14
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
| 3-01-01 | 01 | 1 | CLI-01 | integration | `uv run pytest "tests/test_scaffold.py::TestScaffoldCreatesAllFiles::test_scaffold_creates_all_files" -x` | ✅ | ✅ green |
| 3-01-02 | 01 | 1 | CLI-02 | unit | `uv run pytest tests/test_cli.py::test_cli_valid_args -x` | ✅ | ✅ green |
| 3-01-03 | 01 | 1 | CLI-03 | integration | `uv run pytest "tests/test_scaffold.py::TestScaffoldTrainConfig::test_scaffold_train_py_config" -x` | ✅ | ✅ green |
| 3-01-04 | 01 | 1 | CLI-04 | integration | `uv run pytest tests/test_e2e.py::test_scaffolded_project_runs -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_scaffold.py` — 23 tests covering CLI-01, CLI-03, CLI-04 (and phase 5, 8-10 additions)
- [x] `tests/test_cli.py` — 15 tests covering CLI-02 (including --resume and --agents flags)
- [x] `tests/test_e2e.py` — 2 tests covering CLI-04 end-to-end
- [x] Test fixture: `sample_classification_csv` in conftest.py

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E2E: scaffold + autonomous loop improves beyond baseline | Success Criterion 3 | Requires Claude Code agent to run loop | Scaffold project, run claude with CLAUDE.md, verify results.tsv shows improvement |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 25s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** audited 2026-03-14 — all 4 task requirements verified green

### Audit Notes (2026-03-14)
VALIDATION.md was drafted with placeholder test names before implementation. The actual tests were written with class-based organization and different node IDs. This audit cross-referenced all 4 task requirements against the 38 passing tests in test_scaffold.py and test_cli.py (plus 2 in test_e2e.py) and updated all commands to the correct pytest node IDs. No missing behavioral coverage was found — the implementation exceeds the original 9-test requirement with 40 total tests.
