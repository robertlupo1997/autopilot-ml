---
phase: 9
slug: resume-capability
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-13
audited: 2026-03-14
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
| **Estimated runtime** | ~47 seconds (233 tests) |

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
| 09-01-01 | 01 | 1 | checkpoint-save | unit | `uv run pytest tests/test_checkpoint.py::TestSaveCheckpoint -x` | yes | green |
| 09-01-02 | 01 | 1 | checkpoint-load | unit | `uv run pytest tests/test_checkpoint.py::TestLoadCheckpoint -x` | yes | green |
| 09-01-03 | 01 | 1 | checkpoint-roundtrip | unit | `uv run pytest tests/test_checkpoint.py::TestRoundTrip -x` | yes | green |
| 09-01-04 | 01 | 1 | atomic-write | unit | `uv run pytest tests/test_checkpoint.py::TestAtomicWrite -x` | yes | green |
| 09-01-05 | 01 | 1 | checkpoint-exists | unit | `uv run pytest tests/test_checkpoint.py::TestCheckpointExists -x` | yes | green |
| 09-01-06 | 01 | 1 | gitignore-checkpoint | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldGitignore -x` | yes | green |
| 09-02-01 | 02 | 1 | cli-resume-flag | unit | `uv run pytest tests/test_cli.py::TestCliResumeFlag -x` | yes | green |
| 09-02-02 | 02 | 1 | claudemd-resume-section | unit | `uv run pytest tests/test_templates.py::TestClaudeMdResumeSection -x` | yes | green |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `tests/test_checkpoint.py` — 24 tests across TestSaveCheckpoint, TestAtomicWrite, TestLoadCheckpoint, TestLoadLoopState, TestCheckpointExists, TestRoundTrip — all passing
- [x] Extend `tests/test_scaffold.py` — TestScaffoldGitignore tests confirm checkpoint.json and checkpoint.json.tmp in .gitignore — all passing
- [x] Extend `tests/test_cli.py` — TestCliResumeFlag (4 tests) confirms --resume flag accepted without error — all passing
- [x] Extend `tests/test_templates.py` — TestClaudeMdResumeSection (9 tests) confirms "Session Resume Check" section in CLAUDE.md — all passing

*Existing infrastructure covers framework install — pytest already present.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Resume protocol followed by claude -p agent | claudemd-resume | Agent behavior not unit-testable | Run `claude -p` with --resume, verify agent reads checkpoint |

---

## Audit Notes (2026-03-14)

Nyquist auditor verified all 8 task rows against actual test functions. No missing tests found — all test classes named in the verification map exist and pass. Full suite: 233 tests, 0 failures.

Test class to file mapping confirmed:
- `TestSaveCheckpoint`, `TestAtomicWrite`, `TestLoadCheckpoint`, `TestLoadLoopState`, `TestCheckpointExists`, `TestRoundTrip` → `tests/test_checkpoint.py`
- `TestScaffoldGitignore` → `tests/test_scaffold.py`
- `TestCliResumeFlag` → `tests/test_cli.py`
- `TestClaudeMdResumeSection` → `tests/test_templates.py`

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** green — audited 2026-03-14, 233/233 tests passing
