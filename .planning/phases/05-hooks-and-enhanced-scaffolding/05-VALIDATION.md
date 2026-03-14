---
phase: 5
slug: hooks-and-enhanced-scaffolding
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-12
audited: 2026-03-14
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
| 05-xx-01 | 01 | 1 | scaffold .claude/ | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude::test_scaffold_creates_dot_claude_dir -x` | ✅ | ✅ green |
| 05-xx-02 | 01 | 1 | settings.json content | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude::test_scaffold_settings_json_valid -x` | ✅ | ✅ green |
| 05-xx-03 | 01 | 1 | hook script exists+exec | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude::test_scaffold_hook_script_exists_and_executable -x` | ✅ | ✅ green |
| 05-xx-04 | 01 | 1 | hook denies prepare.py | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude::test_scaffold_hook_denies_prepare_py -x` | ✅ | ✅ green |
| 05-xx-05 | 01 | 1 | hook allows train.py | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldDotClaude::test_scaffold_hook_allows_train_py -x` | ✅ | ✅ green |
| 05-xx-06 | 02 | 1 | CLAUDE.md shutdown | unit | `uv run pytest tests/test_templates.py::TestClaudeMdTemplate::test_claude_md_has_graceful_shutdown -x` | ✅ | ✅ green |
| 05-xx-07 | 01 | 1 | file count 8 (7 files + .claude/ dir) | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldCreatesAllFiles -x` | ✅ | ✅ green |
| 05-xx-08 | 01 | 1 | gitignore local settings | unit | `uv run pytest tests/test_scaffold.py::TestScaffoldGitignore::test_scaffold_gitignore -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_scaffold.py::TestScaffoldDotClaude` — .claude/ dir creation
- [x] `tests/test_scaffold.py::TestScaffoldDotClaude` — settings.json content validation
- [x] `tests/test_scaffold.py::TestScaffoldDotClaude` — hook file exists + executable
- [x] `tests/test_scaffold.py::TestScaffoldDotClaude` — hook deny/allow behavior
- [x] `tests/test_templates.py::TestClaudeMdTemplate` — graceful shutdown section in CLAUDE.md
- [x] `TestScaffoldCreatesAllFiles` — file count updated to 8 (7 files + .claude/ dir)
- [x] `TestScaffoldGitignore` — `.claude/settings.local.json` pattern present

---

## Test Coverage Notes (from Nyquist Audit 2026-03-14)

All 8 VALIDATION.md rows have passing tests. Cross-reference:

- **05-xx-01:** `TestScaffoldDotClaude::test_scaffold_creates_dot_claude_dir` — PASSES
- **05-xx-02:** `TestScaffoldDotClaude::test_scaffold_settings_json_valid`, `test_scaffold_settings_permissions`, `test_scaffold_settings_deny` — PASSES (note: impl uses broad allow `Bash(*)`, `Edit(*)`, `Write(*)` + explicit deny list, not the narrow `Edit(train.py)` from original plan; this is a deliberate deviation from Plan 01 — Phase 8 Permissions Simplification tracks this)
- **05-xx-03:** `TestScaffoldDotClaude::test_scaffold_hook_script_exists_and_executable` — PASSES
- **05-xx-04:** `TestScaffoldDotClaude::test_scaffold_hook_denies_prepare_py` — PASSES
- **05-xx-05:** `TestScaffoldDotClaude::test_scaffold_hook_allows_train_py` — PASSES
- **05-xx-06:** `TestClaudeMdTemplate::test_claude_md_has_graceful_shutdown`, `test_claude_md_shutdown_mentions_git_reset`, `test_claude_md_shutdown_mentions_results_tsv` — PASSES
- **05-xx-07:** `TestScaffoldCreatesAllFiles::test_scaffold_creates_all_files` asserts `len(list(out.iterdir())) == 8` — PASSES
- **05-xx-08:** `TestScaffoldGitignore::test_scaffold_gitignore` asserts `.claude/settings.local.json` in content — PASSES

Full test run: 23/23 scaffold tests green, 31/31 template tests green.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hook blocks prepare.py edit in live Claude session | Mutable zone enforcement | Requires running Claude Code interactively | `cd experiment-dir && claude` then try to edit prepare.py |
| `permissions.allow` basename matching | Settings correctness | Path matching behavior unclear | Attempt `Edit(prepare.py)` in live session |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** nyquist_compliant — audited 2026-03-14
