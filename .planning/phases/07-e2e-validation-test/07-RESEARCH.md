# Phase 7: E2E Validation Test - Research

**Researched:** 2026-03-12
**Domain:** End-to-end integration testing of a `claude -p` autonomous ML loop
**Confidence:** HIGH

## Summary

Phase 7 is a validation-only phase. No new code will be written to `src/automl/`. The
deliverable is a test harness shell script (modeled on `scripts/run-baseline-test.sh` from
Phase 4) plus a structured FINDINGS.md that certifies every behavior claim made by Phases
5-6. The planner must produce tasks that are either "run a script outside Claude Code and
document findings" or "write a script / helper that makes the run observable."

The baseline run (Phase 4) reached `stop_reason=tool_use` after 31 turns on a near-ceiling
iris dataset. Phase 7 must demonstrate the three things Phase 4 could not: (1) graceful
shutdown (stop_reason=end_turn or natural stagnation exit), (2) hook enforcement of frozen
files, (3) stagnation forcing a strategy-category shift. All three require a noisier dataset
and a higher turn cap (50+).

**Primary recommendation:** Write `scripts/run-validation-test.sh` as the single executable
artifact of this phase, modeled on `run-baseline-test.sh` but upgraded with: noisier dataset,
50 max turns, no budget cap below $4, structured assertions using `parse_run_result.py`, and
a FINDINGS.md template that has specific pass/fail slots for each behavior under test.

---

## What Changed in Phases 5-6 (What This Phase Must Validate)

| Change | Source | What to Verify |
|--------|--------|----------------|
| `.claude/settings.json` with `permissions.allow` | Phase 5 Plan 1 | Agent starts without `--dangerously-skip-permissions` or manual `--allowedTools` |
| `guard-frozen.sh` PreToolUse hook | Phase 5 Plan 1 | Hook fires and denies `prepare.py` write attempts; `permission_denials` in output JSON is non-empty when agent tries |
| CLAUDE.md Graceful Shutdown section | Phase 5 Plan 2 | stop_reason is `end_turn` not `tool_use`; git tree is clean on exit |
| `json_output:` line in train.py | Phase 6 Plan 1 | Last line of each `run.log` is parseable JSON matching key:value block |
| `parse_run_result.py` | Phase 6 Plan 2 | Script extracts correct stop_reason, num_turns, total_cost_usd from output JSON |

---

## Standard Stack

### Core (no changes — all pre-existing)

| Tool/Library | Version | Purpose | Status |
|-------------|---------|---------|--------|
| `claude` CLI | current | Headless loop execution via `claude -p` | Pre-installed |
| `uv` | current | Dependency management, `uv run automl` scaffold | Pre-installed |
| `pytest` | 7.x | Unit tests for harness helpers | In pyproject.toml |
| `scripts/parse_run_result.py` | project | Extracts stop_reason, num_turns, cost from JSON output | Built in Phase 6 |
| `scripts/run-baseline-test.sh` | project | Phase 4 harness — template for Phase 7 script | Exists |

### Dataset Requirements

Phase 4 used iris (150 rows, 3-class, near-ceiling at 0.98 accuracy). This was insufficient
to trigger stagnation in 30 turns. Phase 7 needs a dataset where:

- Best achievable accuracy is in the 0.80-0.92 range (forces real iteration, not trivial wins)
- Small enough to run 50+ experiments in budget (< 500 rows, < 10 features)
- Classification task (to match iris setup and avoid metric-direction changes)
- Already available or trivially generatable from sklearn

**Recommended dataset options** (from sklearn, no download required):

| Dataset | Rows | Classes | Expected accuracy range | Notes |
|---------|------|---------|------------------------|-------|
| `load_breast_cancer()` | 569 | 2 | 0.90-0.97 | Near ceiling, may still be easy |
| `load_wine()` | 178 | 3 | 0.92-0.98 | Small and fast, near ceiling |
| Synthetic via `make_classification(n_samples=300, n_features=10, n_informative=5, n_redundant=3, flip_y=0.1)` | 300 | 2 | ~0.82-0.90 | Controllable noise, recommended |

**Recommendation:** Use `sklearn.datasets.make_classification` with `flip_y=0.1` (10% label
noise) to produce a dataset with a natural accuracy ceiling around 0.88-0.90. This forces the
agent to genuinely improve rather than start near-perfect, and stagnation will trigger within
50 turns. Save as `tests/fixtures/noisy.csv`.

---

## Architecture Patterns

### Pattern 1: Validation Test Harness (extends Phase 4 baseline pattern)

The Phase 4 `run-baseline-test.sh` is the proven template. Phase 7 replaces/augments it
with `run-validation-test.sh`. Key structural changes from Phase 4:

```
scripts/
  run-baseline-test.sh      # Phase 4 — DO NOT MODIFY (historical record)
  run-validation-test.sh    # Phase 7 — new validation harness

tests/fixtures/
  iris.csv                  # Phase 4 dataset — unchanged
  noisy.csv                 # Phase 7 dataset — new, noisier

.planning/phases/07-e2e-validation-test/
  FINDINGS.md               # Populated after human runs the script
```

**Key differences from Phase 4 script:**

```bash
# Phase 4 (baseline)
claude -p "..." \
  --max-turns 30 \
  --max-budget-usd 2.00 \
  --allowedTools "Bash Edit Read Write" \   # explicit, overrides settings.json
  --output-format json

# Phase 7 (validation) — DO NOT pass --allowedTools
claude -p "..." \
  --max-turns 50 \
  --max-budget-usd 4.00 \
  --output-format json                      # No --allowedTools — let settings.json govern
```

Not passing `--allowedTools` is critical: the entire point of Phase 5 was to make
`cd experiment-dir && claude` work without flags. Passing `--allowedTools` would bypass
`settings.json` and make the hook test meaningless.

**CRITICAL NOTE:** The Phase 4 script passes `--allowedTools "Bash Edit Read Write"` to
explicitly allow all tools. Phase 7 must NOT pass this flag. The settings.json
`permissions.allow` list should be sufficient. This is a behavioral change in the harness.

### Pattern 2: CLAUDECODE env var guard (existing, keep)

The Phase 4 script already checks `$CLAUDECODE` to prevent accidental execution inside a
Claude Code session. Keep this guard unchanged in Phase 7.

```bash
if [ -n "${CLAUDECODE:-}" ]; then
    echo "ERROR: Must be run outside Claude Code session"
    exit 1
fi
```

### Pattern 3: Structured assertions (new in Phase 7)

Phase 7 can use `parse_run_result.py` to programmatically assert stop conditions:

```bash
# Assert stop_reason is end_turn (graceful) not tool_use (interrupt)
STOP_REASON=$(python3 scripts/parse_run_result.py validation-run-output.json | grep "^stop_reason" | cut -d: -f2 | tr -d ' ')
if [ "$STOP_REASON" != "end_turn" ] && [ "$STOP_REASON" != "max_turns" ]; then
    echo "WARN: stop_reason=$STOP_REASON — expected end_turn or max_turns"
fi
```

Note: `max_turns` is also an acceptable stop_reason — it means the agent hit the turn cap
cleanly (not mid-action). Both `end_turn` and `max_turns` indicate graceful completion.
`tool_use` (seen in Phase 4) means the agent was interrupted mid-action.

### Pattern 4: Hook verification approach

To verify the hook fires, the FINDINGS.md template should capture:

1. `permission_denials` count from the output JSON (hook fires when agent tries to write
   prepare.py; the denial will appear here)
2. `git diff HEAD -- prepare.py` — should still be empty (hook works)
3. Manual observation: does the agent receive a "FROZEN" message and immediately pivot?

Note: If the agent never TRIES to write prepare.py (same as Phase 4), `permission_denials`
will be 0. That is still a passing outcome — the CLAUDE.md instructions prevent the attempt.
The hook is a safety net. Record whatever happens honestly.

### Anti-Patterns to Avoid

- **Passing `--allowedTools` in the Phase 7 harness** — this defeats the purpose of
  settings.json and makes the hook test meaningless.
- **Using iris.csv again** — near-ceiling at 0.98, stagnation will not trigger in 50 turns.
- **Hard-asserting `stop_reason == end_turn`** — `max_turns` is also acceptable. Hard-assert
  only that stop_reason is NOT `tool_use`.
- **Overwriting `run-baseline-test.sh`** — it is the Phase 4 historical record. Create a
  new file.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parse output JSON | Custom jq / python inline | `scripts/parse_run_result.py` | Built in Phase 6 for exactly this purpose |
| Generate noisy dataset | Custom data generator | `sklearn.datasets.make_classification` | Deterministic, reproducible, no download |
| Assert structured output | Custom grep in harness | Just check `run.log` tail contains `json_output:` | The runner already parses it; harness just needs to verify it appears |
| Stop_reason assertion | Complex bash parsing | `parse_run_result.py` + `cut` | One-liner with existing tool |

---

## Common Pitfalls

### Pitfall 1: Passing --allowedTools overrides settings.json
**What goes wrong:** Researcher adds `--allowedTools "Bash Edit Read Write"` to the Phase 7
command "to be safe," not realizing this overrides the project settings.json entirely. The
hook never fires. The test proves nothing about Phase 5.
**Why it happens:** Phase 4 required the flag because settings.json did not exist yet. Habit.
**How to avoid:** The plan must explicitly state: NO `--allowedTools` in the Phase 7 command.
**Warning signs:** If `permission_denials` is always 0 AND the agent never mentions "FROZEN"
in any tool response, it is possible the hook is not being loaded.

### Pitfall 2: stop_reason interpretation confusion
**What goes wrong:** FINDINGS.md treats `max_turns` as a failure (same as Phase 4's
`tool_use`). Actually `max_turns` is fine — it means the turn cap was hit at a clean
turn boundary. `tool_use` is the bad one (mid-action interrupt).
**How to avoid:** Document both acceptable values: `end_turn` (natural completion) and
`max_turns` (hit cap cleanly). Only flag `tool_use` as degraded behavior.

### Pitfall 3: Stagnation not triggering with a ceiling dataset
**What goes wrong:** Noisy dataset still allows the agent to improve every few iterations,
so 5 consecutive reverts never occur. Phase 7 exits without exercising stagnation logic.
**How to avoid:** Use `flip_y=0.10` or higher in `make_classification` to force a real
accuracy ceiling around 0.88. If still not triggering, note it in FINDINGS as "stagnation
not observed — further runs needed with harder dataset."

### Pitfall 4: json_output verification confusion
**What goes wrong:** Tester checks if `json_output:` appears in the wrong file. It appears
in `run.log` (train.py's stdout, redirected). It does NOT appear in `baseline-run-output.json`
(the claude -p outer envelope).
**How to avoid:** Verify `json_output:` in `run.log` (the most recent experiment output),
not in the outer `validation-run-output.json`.

### Pitfall 5: claude -p cannot run inside Claude Code
**What goes wrong:** Someone tries to execute `run-validation-test.sh` from a CC terminal.
The `$CLAUDECODE` env var guard will catch this, but the error message must be clear.
**How to avoid:** Keep the existing `$CLAUDECODE` guard from Phase 4. State explicitly in
the plan that Task 2 is a `human-action` gate (blocking checkpoint).

---

## Code Examples

### Generate noisy.csv (insert into harness script or run once)

```python
# Source: sklearn.datasets.make_classification docs
from sklearn.datasets import make_classification
import pandas as pd
import numpy as np

X, y = make_classification(
    n_samples=300,
    n_features=10,
    n_informative=5,
    n_redundant=3,
    flip_y=0.10,       # 10% label noise — forces genuine ceiling
    random_state=42,
)
df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(10)])
df["target"] = y
df.to_csv("tests/fixtures/noisy.csv", index=False)
```

### Run command (Phase 7 — no --allowedTools)

```bash
# Critical: no --allowedTools flag. settings.json governs permissions.
claude -p "Follow the CLAUDE.md protocol exactly. NEVER STOP until max-turns is reached." \
    --max-turns 50 \
    --max-budget-usd 4.00 \
    --output-format json \
    2>&1 | tee validation-run-output.json
```

### Stop reason assertion (in harness script)

```bash
STOP_REASON=$(python3 "$PROJECT_ROOT/scripts/parse_run_result.py" \
    "$EXPERIMENT_DIR/validation-run-output.json" \
    | grep "^stop_reason:" | cut -d' ' -f2)
echo "  stop_reason: $STOP_REASON"
if [ "$STOP_REASON" = "tool_use" ]; then
    echo "  WARN: stop_reason=tool_use -- agent interrupted mid-action (degraded behavior)"
else
    echo "  OK: stop_reason=$STOP_REASON (end_turn or max_turns -- acceptable)"
fi
```

### Verify json_output in run.log (harness)

```bash
# json_output appears in run.log (train.py stdout), NOT in validation-run-output.json
if [ -f run.log ]; then
    if grep -q "^json_output:" run.log; then
        echo "  OK: json_output line present in run.log"
        JSON_LINE=$(grep "^json_output:" run.log | tail -1 | sed 's/^json_output: //')
        python3 -c "import json; d=json.loads('$JSON_LINE'); print('  metric_value:', d.get('metric_value'))" 2>/dev/null \
            || echo "  WARN: json_output present but not parseable"
    else
        echo "  WARN: json_output line not found in run.log"
    fi
fi
```

### FINDINGS.md observation template (Phase 7-specific sections)

The FINDINGS.md for Phase 7 needs these sections in addition to the Phase 4 checklist:

```markdown
### Hook Enforcement (NEW — Phase 5)
- [ ] Agent started without --dangerously-skip-permissions or manual --allowedTools
- [ ] permission_denials count (from output JSON): {value}
- [ ] prepare.py unchanged (git diff HEAD -- prepare.py empty)
- Notes: {what happened when/if agent tried to touch prepare.py}

### Graceful Shutdown (NEW — Phase 5)
- [ ] stop_reason is end_turn or max_turns (not tool_use)
- [ ] git status is clean on exit (no uncommitted changes to train.py)
- Notes: {what stop_reason was, git state at termination}

### Structured Output (NEW — Phase 6)
- [ ] json_output line present in run.log
- [ ] json_output JSON is parseable and values match key:value block
- Notes: {sample json_output from last experiment}
```

---

## Plan Structure (Recommended)

Phase 7 maps naturally to the Phase 4 plan structure: one plan with three tasks.

| Task | Type | Description |
|------|------|-------------|
| Task 1 | `auto` | Generate `noisy.csv` fixture and write `scripts/run-validation-test.sh` |
| Task 2 | `checkpoint:human-action` (blocking) | User runs the validation script outside Claude Code |
| Task 3 | `auto` | Analyze results and populate `FINDINGS.md` |

**Single plan is appropriate.** All three tasks are sequentially dependent. No parallelism
is possible (Task 2 is a human gate). One plan keeps the gate visible.

**Autonomous flag:** `autonomous: false` — like Phase 4, because Task 2 requires human
execution of `claude -p` outside Claude Code.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths=["tests"] |
| Quick run command | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` |
| Full suite command | `uv run pytest tests/ -q` |
| Estimated runtime | ~26 seconds (130 tests currently) |

### Phase Requirements to Test Map

Phase 7 has no formal requirement IDs in REQUIREMENTS.md. Its success criteria are
behavioral observations documented in FINDINGS.md. The automated harness assertions
supplement but cannot replace human observation of agent behavior.

| Behavior Under Test | Test Type | Automated Command | Notes |
|---------------------|-----------|-------------------|-------|
| noisy.csv fixture generated correctly | smoke | `python -c "import pandas as pd; df=pd.read_csv('tests/fixtures/noisy.csv'); assert len(df)==300"` | Task 1 artifact |
| run-validation-test.sh passes bash syntax | smoke | `bash -n scripts/run-validation-test.sh` | Task 1 artifact |
| parse_run_result.py extracts stop_reason | unit | `uv run pytest tests/test_parse_run_result.py -q` | Already passing from Phase 6 |
| Full suite green before human run | regression | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` | Task 1 gate |
| stop_reason not tool_use | manual | Inspect validation-run-output.json after human run | Task 2/3 |
| json_output in run.log | manual | Inspect run.log in experiment dir after human run | Task 2/3 |
| hook fires on prepare.py attempt | manual | Inspect permission_denials in output JSON | Task 2/3 |
| stagnation triggers strategy shift | manual | Count consecutive reverts in results.tsv | Task 2/3 |

### Sampling Rate

- **Per task commit (Task 1):** `uv run pytest tests/ -q --ignore=tests/test_e2e.py`
- **After Task 2 (human gate):** No automated test — human provides run output
- **Phase gate (before /gsd:verify-work):** Full suite green + FINDINGS.md populated

### Wave 0 Gaps

No new test files need to be created. All test infrastructure exists:

- `tests/test_parse_run_result.py` — covers the Phase 6 helper used by Phase 7 harness
- `scripts/run-baseline-test.sh` — template for Task 1; syntax-check with `bash -n`
- Existing 130 tests cover all src/ modules

The human-action gate (Task 2) is the validation bottleneck, not test infrastructure.

---

## State of the Art

| Old Approach (Phase 4) | Phase 7 Approach | Change | Impact |
|----------------------|-----------------|--------|--------|
| `--allowedTools "Bash Edit Read Write"` flag | No `--allowedTools` (settings.json governs) | Phase 5 result | Proves hook enforcement works end-to-end |
| iris.csv (near-ceiling, stagnation unlikely) | noisy.csv with flip_y=0.10 | Phase 7 design | Exercises stagnation logic |
| 30 max turns | 50 max turns | Phase 4 finding | Allows stagnation threshold (5 reverts) to trigger |
| Manual JSON field extraction | `parse_run_result.py` | Phase 6 result | Automated stop_reason assertion in harness |
| No graceful shutdown section in CLAUDE.md | Graceful Shutdown section added | Phase 5 result | Expect stop_reason to improve from tool_use |
| No json_output in train.py | json_output line as last stdout | Phase 6 result | Agent and harness can parse metrics from JSON |

---

## Open Questions

1. **Will the agent attempt to write prepare.py at all with the new hooks + CLAUDE.md?**
   - What we know: Phase 4 showed the agent respected the CLAUDE.md instructions alone
     (no hook attempts triggered). Phase 5 adds a hard hook as a safety net.
   - What's unclear: The Phase 7 run may show 0 `permission_denials` again, which is a
     passing result but does not exercise the hook path. If we want to actively test the
     hook, we would need to temporarily weaken the CLAUDE.md instructions — not recommended
     for a validation test.
   - Recommendation: Accept 0 denials as passing; document it as "CLAUDE.md instructions
     remain primary enforcement mechanism, hook not triggered." Don't weaken CLAUDE.md.

2. **What is the right `--max-budget-usd` for 50 turns?**
   - What we know: Phase 4 ran 31 turns at $0.85 with claude-opus-4-6. 50 turns would
     extrapolate to ~$1.40. However model pricing and turn complexity vary.
   - Recommendation: Set `--max-budget-usd 4.00` for headroom. The budget cap is a safety
     net, not the expected stopping condition.

3. **Will the noisy dataset trigger genuine stagnation?**
   - What we know: `flip_y=0.10` targets ~0.88-0.90 ceiling. With 50 turns (40+ post-draft
     iterations), stagnation is likely but not guaranteed — depends on agent strategy choices.
   - Recommendation: If stagnation does not trigger, document it as "stagnation not observed
     in this run — algorithm ceiling may be higher than expected." This is an honest finding,
     not a failure of the implementation.

---

## Sources

### Primary (HIGH confidence)

- `.planning/phases/04-e2e-baseline-test/FINDINGS.md` — direct observations from Phase 4 run
- `.planning/phases/05-hooks-and-enhanced-scaffolding/05-VERIFICATION.md` — verified Phase 5 deliverables
- `.planning/phases/06-structured-output-and-metrics-parsing/06-01-SUMMARY.md` — Phase 6 Plan 1 deliverables
- `.planning/phases/06-structured-output-and-metrics-parsing/06-02-SUMMARY.md` — Phase 6 Plan 2 deliverables
- `src/automl/scaffold.py` — current scaffold code with hook generation
- `src/automl/templates/claude.md.tmpl` — current CLAUDE.md template
- `scripts/run-baseline-test.sh` — Phase 4 harness (template for Phase 7)
- `scripts/parse_run_result.py` — Phase 6 helper used in Phase 7 assertions

### Secondary (MEDIUM confidence)

- STATE.md decisions block — architectural decisions logged per phase
- ROADMAP.md Phase 7 description — validated goal statement

### Tertiary (LOW confidence)

- None

---

## Metadata

**Confidence breakdown:**
- Plan structure: HIGH — Phase 4 is a proven template; Phase 7 is structurally identical
- Dataset selection: HIGH — sklearn.datasets.make_classification is deterministic and local
- Hook behavior: MEDIUM — hook was unit-tested but never exercised in a live claude -p run
- Stagnation coverage: MEDIUM — depends on agent behavior in a live run, not fully controllable
- Stop_reason improvement: MEDIUM — Graceful Shutdown section was added, but agent behavior is probabilistic

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable domain)
