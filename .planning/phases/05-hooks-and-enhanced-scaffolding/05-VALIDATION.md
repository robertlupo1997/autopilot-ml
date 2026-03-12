---
phase: 5
slug: hooks-and-enhanced-scaffolding
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths=["tests"] |
| **Quick run command** | `uv run pytest tests/test_scaffold.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_scaffold.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-xx-01 | TBD | 0 | scaffold .claude/ | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude -x` | ❌ W0 | ⬜ pending |
| 05-xx-02 | TBD | 0 | settings.json content | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldSettings -x` | ❌ W0 | ⬜ pending |
| 05-xx-03 | TBD | 0 | hook script exists+exec | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldHookScript -x` | ❌ W0 | ⬜ pending |
| 05-xx-04 | TBD | 0 | hook denies prepare.py | unit | `uv run pytest tests/test_scaffold.py::TestGuardFrozenHook -x` | ❌ W0 | ⬜ pending |
| 05-xx-05 | TBD | 0 | hook allows train.py | unit | same test class | ❌ W0 | ⬜ pending |
| 05-xx-06 | TBD | 0 | CLAUDE.md shutdown | unit | `uv run pytest tests/test_templates.py::TestClaudeMd -x` | ❌ W0 | ⬜ pending |
| 05-xx-07 | TBD | 1 | file count 9 | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldCreatesAllFiles -x` | ✅ needs update | ⬜ pending |
| 05-xx-08 | TBD | 1 | gitignore local settings | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldGitignore -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scaffold.py::TestScaffoldDotClaude` — .claude/ dir creation
- [ ] `tests/test_scaffold.py::TestScaffoldSettings` — settings.json content validation
- [ ] `tests/test_scaffold.py::TestScaffoldHookScript` — hook file exists + executable
- [ ] `tests/test_scaffold.py::TestGuardFrozenHook` — hook deny/allow behavior
- [ ] `tests/test_templates.py::TestClaudeMd` — graceful shutdown section in CLAUDE.md
- [ ] Update `TestScaffoldCreatesAllFiles` — file count 7 → 9
- [ ] Update `_gitignore_content()` — add `.claude/settings.local.json`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hook blocks prepare.py edit in live Claude session | Mutable zone enforcement | Requires running Claude Code interactively | `cd experiment-dir && claude` then try to edit prepare.py |
| `permissions.allow` basename matching | Settings correctness | Path matching behavior unclear | Attempt `Edit(prepare.py)` in live session |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
