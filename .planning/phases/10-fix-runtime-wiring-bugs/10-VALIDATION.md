---
phase: 10
slug: fix-runtime-wiring-bugs
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml (pytest section) |
| **Quick run command** | `python3 -m pytest tests/mlforge/test_engine.py tests/mlforge/test_swarm.py tests/mlforge/test_cli.py -x -q` |
| **Full suite command** | `python3 -m pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/test_engine.py tests/mlforge/test_swarm.py tests/mlforge/test_cli.py -x -q`
- **After every plan wave:** Run `python3 -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | INTL-01, INTL-02 | unit | `python3 -m pytest tests/mlforge/test_engine.py::TestIntelligenceIntegration::test_compute_baselines_called_before_loop -x` | ✅ (needs update) | ⬜ pending |
| 10-01-02 | 01 | 1 | INTL-05 | unit | `python3 -m pytest tests/mlforge/test_cli.py -x -k "enable_drafts"` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 1 | SWARM-01 | unit | `python3 -m pytest tests/mlforge/test_swarm.py::TestBuildAgentCommand -x` | ✅ (needs assertion flip) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_cli.py` — add test for `--enable-drafts` flag (INTL-05)
- [ ] `tests/mlforge/test_engine.py` — update baseline test to use function-based prepare.py (INTL-01)
- [ ] `tests/mlforge/test_swarm.py` — flip `--cwd` assertion to negative (SWARM-01)

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
