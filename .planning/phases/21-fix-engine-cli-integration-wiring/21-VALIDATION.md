---
phase: 21
slug: fix-engine-cli-integration-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `python3 -m pytest tests/mlforge/test_engine.py tests/mlforge/test_cli.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/mlforge/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/mlforge/test_engine.py tests/mlforge/test_cli.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/mlforge/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | DL-04, INTL-01 | unit | `python3 -m pytest tests/mlforge/test_cli.py -x -k dataset_path_dl` | ❌ W0 | ⬜ pending |
| 21-01-02 | 01 | 1 | GUARD-05 | unit | `python3 -m pytest tests/mlforge/test_cli.py -x -k dataset_path_expert` | ❌ W0 | ⬜ pending |
| 21-01-03 | 01 | 1 | FT-03, INTL-05 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k sft_diagnostics` | ❌ W0 | ⬜ pending |
| 21-01-04 | 01 | 1 | DL-01, INTL-05 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k draft_dl_fallback` | ❌ W0 | ⬜ pending |
| 21-01-05 | 01 | 1 | GUARD-02, CORE-08 | unit | `python3 -m pytest tests/mlforge/test_engine.py -x -k max_turns_prompt` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/mlforge/test_engine.py` — add tests for sft diagnostics routing, DL draft fallback, max_turns system prompt
- [ ] `tests/mlforge/test_cli.py` — add test for dataset_path in plugin_settings for DL domain (simple and expert modes)

*Existing infrastructure covers framework install — pytest already configured, 392+ tests passing.*

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
