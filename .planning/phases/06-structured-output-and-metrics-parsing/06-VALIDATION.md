---
phase: 6
slug: structured-output-and-metrics-parsing
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-12
audited: 2026-03-14
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths=["tests"] |
| **Quick run command** | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~35 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q --ignore=tests/test_e2e.py`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 35 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | STRUCT-01 | unit | `uv run pytest tests/test_train.py -q -k "json_output"` | ✅ | ✅ green |
| 06-01-02 | 01 | 1 | STRUCT-01 | unit | `uv run pytest tests/test_runner.py -q -k "json_output"` | ✅ | ✅ green |
| 06-02-01 | 02 | 1 | STRUCT-02 | unit | `uv run pytest tests/test_parse_run_result.py -q` | ✅ | ✅ green |
| 06-XX-XX | all | all | regression | regression | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Test Coverage Detail

### 06-01-01: STRUCT-01 — json_output line in train.py (tests/test_train.py)

Class `TestJsonOutput` (3 tests, all passing):
- `test_json_output_present` — exactly one line starts with `json_output: `
- `test_json_output_parseable` — JSON contains all 6 required keys (metric_name, metric_value, metric_std, direction, elapsed_sec, model)
- `test_json_output_values_match` — metric_value in JSON matches key:value text output

### 06-01-02: STRUCT-01 — _parse_json_output in runner.py (tests/test_runner.py)

Class `TestJsonOutputParsing` (3 tests, all passing):
- `test_parse_json_output_present` — valid json_output line returns dict with all 6 keys
- `test_parse_json_output_missing` — no json_output line returns None
- `test_parse_json_output_invalid` — invalid JSON in json_output line returns None (no exception)

### 06-02-01: STRUCT-02 — parse_run_result.py (tests/test_parse_run_result.py)

Class `TestParseRunResult` (5 tests, all passing):
- `test_parse_full_result` — full JSON with all 4 fields returns correct dict
- `test_parse_missing_fields` — partial JSON returns None for missing keys
- `test_parse_empty_object` — empty `{}` returns all None
- `test_parse_real_structure` — realistic claude -p nested output extracts top-level fields correctly
- `test_cli_stdout` — CLI invocation prints key: value lines to stdout

---

## Wave 0 Completion

- [x] `tests/test_train.py` — `TestJsonOutput` class with 3 tests (present, parseable, values-match)
- [x] `tests/test_runner.py` — `TestJsonOutputParsing` class with 3 tests (present, missing, invalid)
- [x] `tests/test_parse_run_result.py` — New test file with 5 tests covering STRUCT-02
- [x] `scripts/parse_run_result.py` — Implementation exists and is importable + CLI-runnable

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Existing grep parsing still works in scaffolded project | STRUCT-01 | Requires live scaffolded experiment | Scaffold a test project, run train.py, verify `grep "^metric_value:" run.log` still works |

---

## Audit Results (2026-03-14)

Nyquist auditor cross-referenced all VALIDATION.md rows against actual test functions.

**Findings:**
- All 4 rows had tests implemented and passing before audit (Phase 6 was complete)
- VALIDATION.md frontmatter was not updated after completion — corrected now
- Test counts: 3 (test_train json_output) + 3 (test_runner json_output) + 5 (test_parse_run_result) = 11 Phase 6 tests
- Full suite: 231 tests passing (uv run pytest tests/ -q --ignore=tests/test_e2e.py)

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 35s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** green — audited 2026-03-14
