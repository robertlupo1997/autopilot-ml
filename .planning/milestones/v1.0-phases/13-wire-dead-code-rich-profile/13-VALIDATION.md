---
phase: 13
slug: wire-dead-code-rich-profile
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/mlforge/test_engine.py tests/mlforge/test_swarm.py tests/mlforge/test_cli.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/mlforge/test_engine.py tests/mlforge/test_swarm.py tests/mlforge/test_cli.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | CORE-10 | unit | `python -m pytest tests/mlforge/test_engine.py -x -q -k tag_best` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | CORE-10 | unit | `python -m pytest tests/mlforge/test_engine.py -x -q -k tag_best_skip` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 1 | CORE-10 | unit | `python -m pytest tests/mlforge/test_engine.py -x -q -k tag_best_dup` | ❌ W0 | ⬜ pending |
| 13-01-04 | 01 | 1 | SWARM-01 | unit | `python -m pytest tests/mlforge/test_swarm.py -x -q -k publish` | ❌ W0 | ⬜ pending |
| 13-01-05 | 01 | 1 | SWARM-02 | unit | `python -m pytest tests/mlforge/test_swarm.py -x -q -k scoreboard_populated` | ❌ W0 | ⬜ pending |
| 13-01-06 | 01 | 1 | UX-04 | unit | `python -m pytest tests/mlforge/test_cli.py -x -q -k profile_display` | ❌ W0 | ⬜ pending |
| 13-01-07 | 01 | 1 | UX-04 | unit | `python -m pytest tests/mlforge/test_cli.py -x -q -k leakage` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_engine.py` — add tag_best wiring tests (3 tests)
- [ ] `tests/mlforge/test_swarm.py` — add publish_result wiring tests (2 tests)
- [ ] `tests/mlforge/test_cli.py` — add profile display tests (2 tests)

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
