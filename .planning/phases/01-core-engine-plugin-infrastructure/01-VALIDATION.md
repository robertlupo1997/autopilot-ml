---
phase: 1
slug: core-engine-plugin-infrastructure
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-19
updated: 2026-03-20
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python3 -m pytest tests/ -x --ignore=tests/fixtures -q` |
| **Full suite command** | `python3 -m pytest tests/ --ignore=tests/fixtures -v` |
| **Estimated runtime** | ~0.5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/ -x --ignore=tests/fixtures -q`
- **After every plan wave:** Run `python3 -m pytest tests/ --ignore=tests/fixtures -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | CORE-04 | unit | `pytest tests/mlforge/test_state.py -x` | ✅ | ✅ green |
| 1-01-02 | 01 | 1 | CORE-10 | integration | `pytest tests/test_git_ops.py -x` | ✅ | ✅ green |
| 1-01-03 | 01 | 1 | CORE-05 | unit | `pytest tests/mlforge/test_checkpoint.py -x` | ✅ | ✅ green |
| 1-01-04 | 01 | 1 | CORE-06 | unit | `pytest tests/mlforge/test_config.py -x` | ✅ | ✅ green |
| 1-02-01 | 02 | 1 | CORE-03 | unit | `pytest tests/mlforge/test_templates.py -x` | ✅ | ✅ green |
| 1-02-02 | 02 | 1 | CORE-03 | unit | `pytest tests/mlforge/test_plugins.py -x` | ✅ | ✅ green |
| 1-02-03 | 02 | 1 | CORE-08 | unit | `pytest tests/test_journal.py -x` | ✅ | ✅ green |
| 1-03-01 | 03 | 2 | CORE-07 | unit | `pytest tests/mlforge/test_hooks.py -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hook blocks file write in Claude Code | CORE-07 | Requires live Claude Code session | 1. Scaffold project 2. Attempt to edit frozen file in Claude Code 3. Verify denial message |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 1s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-03-20

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total tests | 81 |
| All green | yes |
