---
phase: 8
slug: permissions-simplification
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-13
audited: 2026-03-14
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
| 08-01-01 | 01 | 1 | Broaden allow | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude::test_scaffold_settings_permissions -x` | Yes | ✅ green |
| 08-01-02 | 01 | 1 | Add deny | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude::test_scaffold_settings_deny -x` | Yes | ✅ green |
| 08-01-03 | 01 | 1 | Script comment | manual | manual review | Yes | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_scaffold.py` — `test_scaffold_settings_permissions` expects `["Bash(*)", "Edit(*)", "Write(*)", "Read", "Glob", "Grep"]` — DONE
- [x] `tests/test_scaffold.py` — `test_scaffold_settings_deny` asserts `data["permissions"]["deny"] == ["Edit(prepare.py)", "Write(prepare.py)"]` — DONE

*Existing infrastructure covers all phase requirements — no new test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Result |
|----------|-------------|------------|--------|
| run-validation-test.sh comment | Script docs | Comment is documentation, not behavior | CONFIRMED: "HEADLESS PERMISSIONS NOTE (Phase 8)" block present with "settings.json alone isn't sufficient in headless -p mode" language |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** audited 2026-03-14 by gsd-nyquist-auditor — all 3 tasks verified, 23/23 scaffold tests pass
