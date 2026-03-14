---
phase: 8
slug: permissions-simplification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (uv run pytest) |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/test_scaffold.py -q -x` |
| **Full suite command** | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_scaffold.py -q -x`
- **After every plan wave:** Run `uv run pytest tests/ -q --ignore=tests/test_e2e.py`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | Broaden allow | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude::test_scaffold_settings_permissions -x` | Yes (update needed) | ⬜ pending |
| 08-01-02 | 01 | 1 | Add deny | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude -x` | Yes (new assertion needed) | ⬜ pending |
| 08-01-03 | 01 | 1 | Script comment | manual | manual review | Yes | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scaffold.py` — update `test_scaffold_settings_permissions` expected list to `["Bash(*)", "Edit(*)", "Write(*)", "Read", "Glob", "Grep"]`
- [ ] `tests/test_scaffold.py` — add assertion for `data["permissions"]["deny"]` containing `"Edit(prepare.py)"` and `"Write(prepare.py)"`

*Existing infrastructure covers all phase requirements — no new test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| run-validation-test.sh comment | Script docs | Comment is documentation, not behavior | Inspect script for explanatory comment about --allowedTools |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
