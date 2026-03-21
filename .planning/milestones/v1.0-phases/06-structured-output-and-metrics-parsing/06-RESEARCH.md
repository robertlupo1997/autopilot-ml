# Phase 6: Structured Output and Metrics Parsing - Research

**Researched:** 2026-03-12
**Domain:** Train.py output format, runner.py metric extraction, agent-side grep parsing, JSON structured output, CLAUDE.md protocol
**Confidence:** HIGH

---

## Summary

Phase 6 is a conditional improvement phase: it was added to the roadmap because Phase 4 might reveal grep-based metric parsing to be fragile. Phase 4 is now complete. The verdict: **the current parsing works and no formatting regressions were observed.** The grep-based `metric_value:` extraction succeeded on all 9 experiments in the baseline run.

However, Phase 4 surfaced a different, narrower parsing problem: the agent reads metrics from `run.log` by grepping text, and its reasoning for keep/revert decisions is opaque. There is also a practical need to parse `stop_reason`, `num_turns`, and `total_cost_usd` from the outer `claude -p --output-format json` result, which is not currently automated. Phase 6's scope should be reoriented around these two concrete problems rather than a speculative full JSON rewrite.

The two deliverables that provide real value are: (1) making train.py emit a JSON block in addition to its existing key:value lines, so the agent can use either format, and (2) adding an automated parser script that extracts `stop_reason`/`num_turns`/`cost` from `baseline-run-output.json` for the Phase 7 validation test. The grep-based extraction in `runner.py` does not need replacement — it is the Python runner's parser, and it works correctly.

**Primary recommendation:** Keep grep-based parsing in runner.py as-is. Add a JSON block to train.py's structured output as an optional bonus line. Add a parse_run_result.py helper for the test harness to automate extraction from the `claude -p` JSON output. No requirement to replace the current format wholesale.

---

## Standard Stack

### What Currently Exists (Confirmed Working)

| Component | Implementation | Status |
|-----------|---------------|--------|
| `runner.py._extract_field` | `re.search(rf"^{field_name}:\s+(.+)$", text, re.MULTILINE)` | Working — no regressions in Phase 4 |
| `train.py` output format | `key:  value` lines separated by `---` sentinel | 9/9 experiments parsed correctly |
| Agent-side parsing | `grep "^metric_value:" run.log` per CLAUDE.md step 6 | Agent followed this reliably in Phase 4 |
| `claude -p --output-format json` | JSON result to stdout with stop_reason, num_turns, cost | Working but parsed manually in Phase 4 |

### The Actual Problem (Narrow Scope)

Phase 4 FINDINGS.md lists exactly two output-parsing concerns for Phase 6:

1. **Manual JSON extraction from baseline-run-output.json** — Stop reason, turn count, and cost were extracted by hand. A small Python helper would automate this for Phase 7.
2. **Opaque draft-selection reasoning** — Agent switched from LogisticRegression (best draft) to SVC family for iterations. Structured output could capture why (though this is an observation concern, not a parsing failure).

There is no correctness bug to fix. The scope is quality-of-life and Phase 7 test automation.

### Libraries: No New Dependencies Needed

| Tool | Already Available | Use |
|------|-------------------|-----|
| `json` (stdlib) | Yes | Parse `claude -p --output-format json` output |
| `re` (stdlib) | Yes | Already used in runner.py |
| `dataclasses` (stdlib) | Yes | Already used for ExperimentResult |

No third-party JSON schema libraries needed. The output is simple enough for stdlib json.

---

## Architecture Patterns

### Current Output Format (train.py)

```
---
metric_name:  accuracy
metric_value: 0.980000
metric_std:   0.017889
direction:    maximize
elapsed_sec:  1.1
model:        SVC
```

Parsed by `runner.py._extract_field()` via multiline regex. Parsed by the Claude Code agent via `grep "^metric_value:" run.log`. Both work correctly.

### Option A: Add JSON Block as Final Line (Recommended)

Add a JSON summary line at the end of train.py's output. The existing key:value format stays intact (backward compatible). The runner.py parser does not change. The agent can optionally use the JSON line.

```python
# In train.py, after existing print statements:
import json as _json
print("json_output:", _json.dumps({
    "metric_name": METRIC,
    "metric_value": round(score_mean, 6),
    "metric_std": round(score_std, 6),
    "direction": direction,
    "elapsed_sec": round(elapsed, 1),
    "model": type(model).__name__,
}))
```

**Why this is valuable:**
- Allows the agent to parse one canonical line instead of running multiple greps
- Agent can parse it with `python3 -c "import json; d=json.loads(open('run.log').read().split('json_output: ')[1].split('\n')[0]); print(d['metric_value'])"`
- Backward compatible — runner.py is unchanged
- Template must be updated in `train_template.py` and propagated to `scaffold.py`

**Why NOT a full JSON-only rewrite:**
- Phase 4 confirmed key:value format works reliably
- The runner.py regex parser works correctly and has test coverage
- CLAUDE.md instructs the agent to `grep "^metric_value:"` — changing the output format requires updating the template and the CLAUDE.md protocol simultaneously
- Risk of introducing new bugs without a correctness benefit

### Option B: Full JSON Output (Not Recommended for Phase 6)

Replace the key:value block with pure JSON output. The agent and runner.py would both parse JSON.

**Tradeoffs:**
- Requires changes to train.py template, train_template.py, runner.py, all runner tests, and CLAUDE.md
- The `grep "^metric_value:"` instruction in CLAUDE.md.tmpl would need to become a python JSON parse call
- Much larger change surface for no correctness gain
- Deferred to v2 if there is a real parsing failure

### parse_run_result.py Helper (New File, High Value)

A small script that automates extracting the outer `claude -p` result fields. Used by Phase 7 test harness.

```python
#!/usr/bin/env python3
"""Parse baseline-run-output.json from claude -p --output-format json."""
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)

print(f"stop_reason:    {data.get('stop_reason', 'unknown')}")
print(f"num_turns:      {data.get('num_turns', 'unknown')}")
print(f"total_cost_usd: {data.get('total_cost_usd', 'unknown')}")
print(f"is_error:       {data.get('is_error', 'unknown')}")
```

Usage: `python3 parse_run_result.py baseline-run-output.json`

This belongs in the project's top-level `scripts/` directory or `.planning/` test tools, not in `src/automl/` (it is a test harness helper, not library code).

### Recommended Project Structure for Phase 6 Changes

```
src/automl/
└── train_template.py    # Add JSON block line at end of structured output

scripts/
└── parse_run_result.py  # New: automate extraction from claude -p JSON output

tests/
└── test_runner.py       # Extend: verify json_output line is parseable
└── test_train.py        # Extend: verify json_output line present in output
```

### Anti-Patterns to Avoid

- **Replacing runner.py's regex parser with JSON**: The regex works, has test coverage, and changing it introduces risk with no benefit. Phase 4 confirmed zero formatting regressions.
- **Requiring json schema validation**: `--json-schema` flag from the ROADMAP description is for validating the Claude Code agent's *natural language result*, not train.py's output. It is not the right tool here.
- **Touching CLAUDE.md template**: Any change to the `grep "^metric_value:"` instruction in CLAUDE.md.tmpl is a large blast radius — it changes agent behavior for all scaffolded projects. Avoid unless there is a parsing failure.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema validation | Custom validator | stdlib `json.load()` + key checks | Output is 6 well-known fields; schema overkill |
| Structured log aggregation | Custom log parser | Direct `results.tsv` reading | Already implemented and working |
| Metric extraction rewrite | New runner.py parser | Existing `_extract_field` regex | Zero failures in Phase 4 |
| Claude output parsing | Custom HTTP/SDK client | `json.load()` on `--output-format json` file | File is already written by `tee` in Phase 4 |

**Key insight:** The "structured output" work in Phase 6 is additive (add JSON line to train.py), not a replacement. The existing key:value format is the ground truth; JSON is an optional bonus for ergonomics.

---

## Common Pitfalls

### Pitfall 1: Confusing Two Different JSON Outputs
**What goes wrong:** Phase 6 mentions "--output-format json and --json-schema" — these are `claude -p` CLI flags for the *outer* orchestration result (stop_reason, cost, turns), NOT for train.py's metric output. Mixing these up leads to implementing the wrong thing.
**Why it happens:** The ROADMAP description uses these flag names in the context of "structured JSON output" but the context is ambiguous.
**How to avoid:** There are two separate outputs: (1) train.py's stdout → parsed by runner.py and the agent's grep, (2) `claude -p --output-format json` → the outer run result with stop_reason/cost. Treat them as independent problems.
**Warning signs:** If a plan task says "add --json-schema to claude -p invocation" to fix train.py parsing — that's the wrong lever.

### Pitfall 2: Breaking the Agent's grep Instruction
**What goes wrong:** Changing train.py's output format without updating the `grep "^metric_value:"` instruction in CLAUDE.md.tmpl. The agent then silently fails to extract metrics.
**Why it happens:** train_template.py and claude.md.tmpl are separate files; changes to one don't automatically update the other.
**How to avoid:** If any format change is made to the structured output block, update the CLAUDE.md.tmpl grep instruction in the same plan task. They are tightly coupled.
**Warning signs:** Agent's grep returns empty; agent treats successful runs as crashes.

### Pitfall 3: Changing runner.py Parsing Without Full Test Coverage
**What goes wrong:** Modifying `_extract_field` or `_parse_output` and breaking the 121 existing passing tests.
**Why it happens:** runner.py has extensive test coverage in `test_runner.py`. Any change must preserve all existing tests.
**How to avoid:** Run `uv run pytest tests/test_runner.py -q` after any runner.py change. Do not remove existing extraction patterns; add new ones alongside.
**Warning signs:** Test failures in `TestMetricExtraction` class.

### Pitfall 4: Adding JSON Line in Wrong Position
**What goes wrong:** Adding `json_output:` before the existing key:value lines. Runner.py's `_extract_string_field` for `model` field picks up the JSON string (it matches the same regex pattern).
**Why it happens:** The `_extract_string_field` regex `^{field_name}:\s+(.+)$` is greedy and matches any line starting with the field name.
**How to avoid:** Add the JSON line AFTER the existing `---` header and all key:value lines, as the last printed line. Alternatively, prefix it distinctly (e.g., `json_output:` rather than a bare `{`).
**Warning signs:** `model_name` field returns JSON string instead of `"SVC"`.

### Pitfall 5: Forgetting to Update train_template.py vs train.py
**What goes wrong:** Updating `train_template.py` (in `src/automl/`) but not the `train.py` generated by `scaffold_experiment()`.
**Why it happens:** `scaffold_experiment()` reads `train_template.py` at scaffold time, so existing experiment directories are not updated.
**How to avoid:** Phase 6 only affects newly scaffolded projects. Document that existing experiment directories (e.g., from Phase 4) must be re-scaffolded to pick up the JSON output line.
**Warning signs:** Phase 7's scaffolded experiment directory doesn't have the JSON line; tests fail because they check the live scaffolded file.

---

## Code Examples

### Current train.py Structured Output (Confirmed Working in Phase 4)

```python
# Source: src/automl/train_template.py (current)
print("---")
print(f"metric_name:  {METRIC}")
print(f"metric_value: {score_mean:.6f}")
print(f"metric_std:   {score_std:.6f}")
print(f"direction:    {direction}")
print(f"elapsed_sec:  {elapsed:.1f}")
print(f"model:        {type(model).__name__}")
```

Parsed by: `re.search(rf"^metric_value:\s+(.+)$", text, re.MULTILINE)` in runner.py (line 132).
Parsed by agent: `grep "^metric_value:" run.log` per CLAUDE.md.tmpl step 6.

### Proposed JSON Line Addition

```python
# Add after existing print block in train_template.py
import json as _json  # use alias to avoid shadowing user's json imports
_result = {
    "metric_name": METRIC,
    "metric_value": round(score_mean, 6),
    "metric_std": round(score_std, 6),
    "direction": direction,
    "elapsed_sec": round(elapsed, 1),
    "model": type(model).__name__,
}
print(f"json_output: {_json.dumps(_result)}")
```

### Agent-Side JSON Parsing (from CLAUDE.md.tmpl)

```bash
# Current instruction (works, keep):
grep "^metric_value:" run.log

# Optional bonus instruction (if JSON line is added):
python3 -c "
import json, re, sys
content = open('run.log').read()
m = re.search(r'^json_output: (.+)$', content, re.MULTILINE)
if m:
    d = json.loads(m.group(1))
    print(d['metric_value'])
"
```

### parse_run_result.py (New Helper Script)

```python
#!/usr/bin/env python3
"""Parse the outer claude -p --output-format json result file.

Usage: python3 scripts/parse_run_result.py <path-to-output.json>
"""
import json
import sys

def parse_run_result(path: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    return {
        "stop_reason": data.get("stop_reason"),
        "num_turns": data.get("num_turns"),
        "total_cost_usd": data.get("total_cost_usd"),
        "is_error": data.get("is_error"),
        "permission_denials": data.get("permission_denials", []),
    }

if __name__ == "__main__":
    result = parse_run_result(sys.argv[1])
    for k, v in result.items():
        print(f"{k}: {v}")
```

### Extending runner.py to also try JSON (Optional, Additive)

```python
# Add to runner.py _parse_output (after existing field extractions):
def _parse_json_output(self, text: str) -> Optional[dict]:
    """Try to parse json_output line if present. Returns None if absent."""
    import json
    match = re.search(r"^json_output:\s+(.+)$", text, re.MULTILINE)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            return None
    return None
```

This is purely additive — the existing `_extract_field` regex remains the primary parser. The JSON parse is a fallback bonus.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Blanket `--dangerously-skip-permissions` | `--allowedTools "Bash Edit Read Write"` | Safer, tested in Phase 4 |
| Manual stop_reason extraction | Automated `parse_run_result.py` (Phase 6) | Phase 7 test automation |
| Key:value only output | Key:value + optional JSON line (Phase 6) | Agent can use either; runner.py unchanged |

**Phase 4 verdict (2026-03-11):** grep-based metric parsing works — 9/9 experiments parsed correctly with no formatting regressions. Phase 6 is a quality-of-life enhancement, not a correctness fix.

---

## Open Questions

1. **Should json_output line be added to CLAUDE.md.tmpl as the preferred parsing method?**
   - What we know: Current grep works. JSON would be more robust if agent modifies the output format.
   - What's unclear: Whether the agent ever reformats print statements (Phase 4 showed it did not).
   - Recommendation: Keep grep as the canonical instruction. Add JSON line to train.py silently. Document it in comments but don't change the CLAUDE.md grep instruction — minimal blast radius.

2. **Where should parse_run_result.py live?**
   - What we know: It is a test harness tool for Phase 7, not library code.
   - Recommendation: `scripts/` directory at project root. Out of `src/automl/` (not a library concern) and out of `tests/` (not a test file itself).

3. **Does Phase 6 need any new requirements added to REQUIREMENTS.md?**
   - What we know: No STRUCT-XX requirements exist. Phase 6 was added conditionally.
   - Recommendation: Add 2-3 narrow requirements: STRUCT-01 (train.py emits json_output line), STRUCT-02 (parse_run_result.py automates outer result parsing), STRUCT-03 (runner.py optionally parses json_output). These reflect the actual scope.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (dev dependency in pyproject.toml) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths=["tests"] |
| Quick run command | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` |
| Full suite command | `uv run pytest tests/ -q` |

**Current test count:** 121 tests passing (as of 2026-03-12).

### Phase Requirements to Test Map

Phase 6 has no formal requirement IDs assigned in REQUIREMENTS.md. The following map is derived from the phase goal and the two concrete deliverables identified in research:

| Deliverable | Behavior | Test Type | Automated Command | File Exists? |
|-------------|----------|-----------|-------------------|-------------|
| json_output line in train.py | `train.py` stdout contains `json_output: {...}` with valid JSON | unit | `uv run pytest tests/test_train.py -q -k "json_output"` | Wave 0 |
| json_output parseable by runner.py | `_parse_json_output` returns dict with metric_value | unit | `uv run pytest tests/test_runner.py -q -k "json_output"` | Wave 0 |
| parse_run_result.py | Extracts stop_reason/num_turns/cost from JSON file | unit | `uv run pytest tests/test_parse_run_result.py -q` | Wave 0 |
| Existing tests unbroken | All 121 current tests still pass | regression | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` | Exists |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -q --ignore=tests/test_e2e.py` (fast, < 10 seconds)
- **Per wave merge:** `uv run pytest tests/ -q` (full suite)
- **Phase gate:** Full suite green (121+ tests) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_train.py` — Add test: `test_json_output_present` verifying `json_output:` line exists in stdout
- [ ] `tests/test_train.py` — Add test: `test_json_output_parseable` verifying the JSON is valid and contains expected keys
- [ ] `tests/test_runner.py` — Add test: `test_parse_json_output_present` for new `_parse_json_output` method
- [ ] `tests/test_runner.py` — Add test: `test_parse_json_output_missing` returns None gracefully
- [ ] `tests/test_parse_run_result.py` — New test file covering `parse_run_result.py` script behavior
- [ ] `scripts/` directory — Create if not exists

---

## Sources

### Primary (HIGH confidence)

- `/home/tlupo/AutoML/.planning/phases/04-e2e-baseline-test/FINDINGS.md` — Authoritative Phase 4 results: 9/9 experiments parsed correctly, no formatting regressions, grep worked reliably
- `/home/tlupo/AutoML/src/automl/runner.py` — Current parsing implementation (regex at line 132-138)
- `/home/tlupo/AutoML/src/automl/train_template.py` — Current output format (lines 43-49)
- `/home/tlupo/AutoML/src/automl/templates/claude.md.tmpl` — CLAUDE.md agent instruction for grep (step 6 in Phase 2 loop)
- `/home/tlupo/AutoML/.planning/research/claude-code-capabilities-research.md` — `--output-format json` behavior and fields confirmed working

### Secondary (MEDIUM confidence)

- `.planning/ROADMAP.md` — Phase 6 goal description and "conditional on Phase 4 findings" caveat
- `.planning/STATE.md` — Decision log confirming "LOOP-03: Agent reads metric via grep/regex from run.log (not by reading full output)"

### Tertiary (LOW confidence)

- None — all claims verified against source code and Phase 4 empirical data

---

## Metadata

**Confidence breakdown:**
- Current parsing status: HIGH — verified by Phase 4 empirical run (9/9 experiments)
- Recommended changes: HIGH — additive only, no replacement of working code
- Test gaps: HIGH — identified by reading test_runner.py and test_train.py directly

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stdlib json and regex are stable; re-verify if Claude Code output format changes)
