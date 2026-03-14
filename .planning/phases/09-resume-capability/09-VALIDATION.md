---
phase: 9
slug: resume-capability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed, `tests/` directory exists) |
| **Config file** | none — pytest auto-discovers `tests/test_*.py` |
| **Quick run command** | `uv run pytest tests/test_checkpoint.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_checkpoint.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | checkpoint-save | unit | `uv run pytest tests/test_checkpoint.py::TestSaveCheckpoint -x` | W0 | pending |
| 09-01-02 | 01 | 1 | checkpoint-load | unit | `uv run pytest tests/test_checkpoint.py::TestLoadCheckpoint -x` | W0 | pending |
| 09-01-03 | 01 | 1 | checkpoint-roundtrip | unit | `uv run pytest tests/test_checkpoint.py::TestRoundTrip -x` | W0 | pending |
| 09-01-04 | 01 | 1 | atomic-write | unit | `uv run pytest tests/test_checkpoint.py::TestAtomicWrite -x` | W0 | pending |
| 09-01-05 | 01 | 1 | checkpoint-exists | unit | `uv run pytest tests/test_checkpoint.py::TestCheckpointExists -x` | W0 | pending |
| 09-01-06 | 01 | 1 | gitignore-checkpoint | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldGitignore -x` | exists (extend) | pending |
| 09-02-01 | 02 | 1 | cli-resume-flag | unit | `uv run pytest tests/test_cli.py::TestCliResumeFlag -x` | W0 | pending |
| 09-02-02 | 02 | 1 | claudemd-resume-section | unit | `uv run pytest tests/test_templates.py::TestClaudeMdResumeSection -x` | W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_checkpoint.py` — stubs for save, load, round-trip, atomic write, exists
- [ ] Extend `tests/test_scaffold.py` — test `checkpoint.json` and `checkpoint.json.tmp` in .gitignore
- [ ] Extend `tests/test_cli.py` — test `--resume` flag accepted without error
- [ ] Extend `tests/test_templates.py` — test "Session Resume Check" section in CLAUDE.md

*Existing infrastructure covers framework install — pytest already present.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Resume protocol followed by claude -p agent | claudemd-resume | Agent behavior not unit-testable | Run `claude -p` with --resume, verify agent reads checkpoint |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
