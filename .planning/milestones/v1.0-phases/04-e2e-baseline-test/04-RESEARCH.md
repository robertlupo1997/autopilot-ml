# Phase 4: E2E Baseline Test - Research

**Researched:** 2026-03-11
**Domain:** Claude Code headless mode (`claude -p`), autonomous ML loop, test harness design, observability
**Confidence:** HIGH

---

## Summary

Phase 4 is an observability phase, not a building phase. The goal is to scaffold a real experiment project using the v1.0 CLI, invoke the autonomous loop with `claude -p --max-turns`, and systematically document what works and what breaks. Findings directly feed Phase 5 (hooks + scaffolding fixes) and Phase 6 (structured output, if parsing proves fragile).

The autonomous loop CLAUDE.md instructs the agent to perform: multi-draft initialization (3-5 algorithm families), iterative keep/revert on the winner, crash recovery, stagnation detection, and results.tsv logging — all without human intervention. The key question is whether this chain works end-to-end in headless mode without `--dangerously-skip-permissions`.

The primary technical decision to resolve is the correct `--allowedTools` set that gives the agent everything it needs (Bash for running train.py and git, Edit/Write for train.py, Read for run.log/program.md) while avoiding a blanket `--dangerously-skip-permissions` flag. A secondary question is whether the CLAUDE.md protocol is sufficient guidance in isolation — the sub-agent context-injection issue from the capability research does not apply here since the agent spawns directly from the scaffolded directory.

**Primary recommendation:** Implement Phase 4 as a single plan: scaffold + run + observe. Script the observation session, capture all output, and produce a structured findings document (FINDINGS.md) to inform phases 5-7.

---

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| `claude -p` headless mode | 2.1.74 (current) | Non-interactive agent invocation | Built into Claude Code CLI |
| `--max-turns N` | same | Limit loop iterations for controlled testing | Prevents runaway cost during baseline test |
| `--max-budget-usd N` | same | Dollar cap for the test run | Safety net for unattended execution |
| `--allowedTools` | same | Pre-approve tools without `--dangerously-skip-permissions` | Safer than blanket bypass |
| `--output-format json` | same | Machine-readable result for programmatic observation | Single JSON result with cost/turns/stop_reason |
| `uv run automl` | 0.x | Scaffold the experiment project | Already built and working |
| iris dataset (sklearn) | 1.5+ | Small, deterministic, widely understood | Fits in seconds, known baseline ~0.97 accuracy |

### Minimum `--allowedTools` Set for Autonomous Loop
The CLAUDE.md protocol requires exactly these operations:
- `Bash` — run `uv run python train.py > run.log 2>&1`, grep run.log, run git commands
- `Edit` — modify `train.py` (the only mutable file)
- `Read` — read `program.md`, `results.tsv`, `run.log`
- `Write` — append to `results.tsv`

Full flag: `--allowedTools "Bash Edit Read Write"`

**Without these, the loop stalls.** The CLAUDE.md instructs the agent to do all four operations. Any missing tool causes an immediate permission failure or silent skip.

### What `--output-format json` Returns
```json
{
  "type": "result",
  "subtype": "success",
  "is_error": false,
  "num_turns": 12,
  "result": "...",
  "stop_reason": "max_turns",
  "total_cost_usd": 1.23,
  "usage": { "input_tokens": ..., "output_tokens": ... }
}
```
`stop_reason` values: `"end_turn"` (agent stopped itself), `"max_turns"` (limit hit), `"error"`.

---

## Architecture Patterns

### What the E2E Test Must Invoke
```
automl iris.csv species accuracy --goal "classify iris species"
cd experiment-iris
git init && git add . && git commit -m "initial scaffold"
claude -p "NEVER STOP. Follow CLAUDE.md protocol." \
  --max-turns 20 \
  --max-budget-usd 2.00 \
  --allowedTools "Bash Edit Read Write" \
  --output-format json
```

The `git init` step is required: the CLAUDE.md protocol commits train.py before each experiment run (`git add train.py && git commit -m "..."`) and uses `git reset --hard HEAD~1` for reverts. Without a git repo, every git command crashes immediately.

### Recommended Test Dataset: Iris via sklearn
```python
# Source: sklearn datasets (built into scikit-learn)
from sklearn.datasets import load_iris
import pandas as pd

iris = load_iris()
df = pd.DataFrame(iris.data, columns=iris.feature_names)
df["species"] = iris.target
df.to_csv("iris.csv", index=False)
```
- 150 rows, 4 features, 3-class classification
- Baseline LogisticRegression accuracy ~0.97
- Runs in <1 second per experiment
- deterministic, no missing values, no preprocessing surprises

### Observation Script Pattern
Phase 4 is a single, scripted run with a pre-written observation checklist. The plan should produce a `FINDINGS.md` documenting:

| Observation Point | What to Check |
|-------------------|---------------|
| Draft phase | Did 3-5 drafts run? Were they different algorithm families? |
| Draft selection | Was best commit checked out? Was winner marked draft-keep? |
| Keep/revert cycle | Did git commits happen on keep? Did reset happen on revert? |
| Metric parsing | Did `grep "^metric_value:"` reliably return a float? |
| results.tsv | Is it being written? Correct format? |
| run.log | Captured? No context flooding? |
| Frozen file compliance | Did agent touch prepare.py? (should be NO) |
| Stagnation | Did N reverts trigger strategy shift? (may not trigger in 20 turns) |
| Crash recovery | If a crash happened, was it handled? |
| Permission denials | Were any tool uses blocked? |
| Stop reason | `max_turns`, `end_turn`, or `error`? |

### Recommended Structure for Phase 4 Plans

**1 plan is sufficient** — the phase is observational, not constructional. Break it into:
- Plan 04-01: Run the baseline test and produce FINDINGS.md

Sub-tasks within that plan:
1. Generate iris.csv from sklearn
2. Scaffold the experiment project with `uv run automl`
3. Initialize git in the scaffolded directory
4. Run `claude -p` with controlled flags and observe
5. Capture and document all findings in FINDINGS.md

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dataset for testing | Custom synthetic CSV | sklearn's iris | Known baseline, fast, deterministic, 3-class covers multi-class case |
| Agent invocation | Custom runner.py integration | `claude -p` directly | That's the target being tested — don't add indirection |
| Metric verification | Custom parser | `grep "^metric_value:"` as specified in CLAUDE.md | Test what the agent actually does, not what we'd prefer it to do |
| Cost control | None | `--max-budget-usd 2.00` | Built into the CLI, zero effort |

**Key insight:** Phase 4 tests the system as users will actually run it. Don't add abstractions that mask real behavior.

---

## Common Pitfalls

### Pitfall 1: Running `claude -p` Inside a Claude Code Session
**What goes wrong:** `Error: Claude Code cannot be launched inside another Claude Code session.`
**Why it happens:** The `CLAUDECODE` environment variable is set in all Claude Code sub-processes.
**How to avoid:** The test must be run by the user in a terminal outside Claude Code, OR the plan must document this and provide a shell script to run separately.
**Warning signs:** If a plan task says "run claude -p" in Bash — that will fail inside the GSD dev session.

### Pitfall 2: Missing `git init` Before Running the Loop
**What goes wrong:** Every git command in the CLAUDE.md protocol fails immediately. `git commit`, `git reset --hard HEAD~1`, `git add` all return `fatal: not a git repository`.
**Why it happens:** `scaffold_experiment()` does NOT initialize a git repo — it only creates files. The user must `git init && git add . && git commit`.
**How to avoid:** The plan's setup step must explicitly include git initialization before invoking `claude -p`.
**Warning signs:** The agent's first commit attempt fails; agent may try to fix with git init (unpredictable behavior).

### Pitfall 3: Blanket `--dangerously-skip-permissions` vs `--allowedTools`
**What goes wrong:** Using `--dangerously-skip-permissions` bypasses all safety, making Phase 4 results unrepresentative of the intended production use (which should use `--allowedTools`).
**Why it happens:** It's the path of least resistance to get the loop running.
**How to avoid:** Use `--allowedTools "Bash Edit Read Write"` explicitly. This is what Phase 5 will bake into the scaffolded `.claude/settings.json`. Testing with the intended tool set now catches permission gaps early.
**Warning signs:** If the loop requires tools beyond Bash/Edit/Read/Write, that's a finding — document it, don't hide it.

### Pitfall 4: Context Flooding from train.py Output
**What goes wrong:** Agent runs `uv run python train.py` without redirecting to run.log. All training output floods the context window.
**Why it happens:** The agent ignores the CLAUDE.md rule "ALWAYS redirect stdout and stderr to `run.log`".
**How to avoid:** The CLAUDE.md template already specifies `uv run python train.py > run.log 2>&1`. Observe whether the agent actually follows this instruction — it's a key finding.
**Warning signs:** The agent's conversation context grows rapidly; experiment output appears inline in the agent's reasoning.

### Pitfall 5: `--max-turns` Too Low to Observe Multi-Draft Phase
**What goes wrong:** With `--max-turns 5`, the agent completes only 1-2 drafts and never reaches iterative improvement. Findings are incomplete.
**Why it happens:** Each draft involves: edit train.py, git commit, run, grep, log = ~4-5 tool calls. With 3 drafts + 5 iterations minimum, need at least ~25-30 turns.
**How to avoid:** Use `--max-turns 30` for the baseline test. This is ~$1.50-2.00 with current pricing.
**Warning signs:** `stop_reason: "max_turns"` with `num_turns` equal to the limit and drafts not yet complete.

### Pitfall 6: Metric Parsing Regression (spacing/format)
**What goes wrong:** The runner's `_extract_field` regex expects `^metric_value:\s+(.+)$` (one or more spaces). If the agent accidentally reformats train.py to print `metric_value:0.85` (no space) or `METRIC_VALUE: 0.85` (uppercase), parsing fails.
**Why it happens:** Agent may try to "clean up" train.py formatting.
**How to avoid:** Observe exactly what the agent prints and compare with the regex in runner.py.
**Warning signs:** `grep "^metric_value:"` returns empty even when train.py ran successfully.

### Pitfall 7: `uv` Not Available in Scaffolded Environment
**What goes wrong:** `uv run python train.py` fails with `command not found: uv` inside the experiment directory.
**Why it happens:** The experiment dir's `pyproject.toml` lists dependencies but `uv` must be installed and the dependencies synced first.
**How to avoid:** The plan should include a `uv sync` step in the scaffolded directory before running `claude -p`. Or verify `uv` is installed and `uv run` works.
**Warning signs:** First experiment run crashes with `ModuleNotFoundError: No module named 'sklearn'`.

---

## Code Examples

### Generating iris.csv
```python
# Source: sklearn documentation (official)
from sklearn.datasets import load_iris
import pandas as pd

iris = load_iris()
df = pd.DataFrame(iris.data, columns=[c.replace(" (cm)", "").replace(" ", "_") for c in iris.feature_names])
df["species"] = iris.target
df.to_csv("iris.csv", index=False)
# 150 rows, 4 features (sepal_length, sepal_width, petal_length, petal_width), target 0/1/2
```

### Scaffolding + Initializing the Experiment
```bash
# Run outside of Claude Code session
uv run automl iris.csv species accuracy --goal "Classify iris species (0=setosa, 1=versicolor, 2=virginica)"
cd experiment-iris
uv sync                         # install dependencies
git init
git add .
git commit -m "initial scaffold"
```

### Invoking the Autonomous Loop
```bash
# --max-turns 30: enough for 5 drafts + 10 iterations
# --max-budget-usd 2.00: hard cost cap
# --output-format json: machine-readable result for post-run analysis
claude -p "Follow the CLAUDE.md protocol exactly. NEVER STOP until max-turns is reached." \
  --max-turns 30 \
  --max-budget-usd 2.00 \
  --allowedTools "Bash Edit Read Write" \
  --output-format json \
  2>&1 | tee baseline-run-output.json
```

### Parsing the Run Result
```bash
# Check stop reason
cat baseline-run-output.json | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['stop_reason'], r['num_turns'], r['total_cost_usd'])"

# Check results.tsv (the ground truth log)
cat results.tsv

# Check git log (committed experiments)
git log --oneline

# Check if prepare.py was modified (should be NEVER)
git diff HEAD -- prepare.py  # should be empty
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `--dangerously-skip-permissions` for autonomous mode | `--allowedTools "Bash Edit Read Write"` | Claude Code 2.x | Safer; permission denials now surfaced in JSON output |
| Unknown `--max-turns` flag | Confirmed working in v2.1.74 | Current | Usable in scripts; not listed in `--help` but functional |
| Agent must handle nested launch error | `CLAUDECODE` env var controls nesting | Always | Must unset or run from outside any CC session |

**Confirmed working (v2.1.74, verified 2026-03-11):**
- `claude -p "prompt" --max-turns N --output-format json` — works, returns JSON result
- `--allowedTools "Bash Edit Read Write"` — accepted, restricts tool use
- `--max-budget-usd N` — enforced as dollar cap
- JSON output includes `num_turns`, `stop_reason`, `total_cost_usd`, `permission_denials`

---

## Open Questions

1. **Does the agent follow the CLAUDE.md `> run.log 2>&1` redirect rule reliably?**
   - What we know: CLAUDE.md specifies it explicitly. Unit tests don't verify agent compliance.
   - What's unclear: Whether the agent interprets the instruction literally or substitutes its own approach.
   - Recommendation: This is the primary thing to observe in Phase 4. Document whether context flooding occurs.

2. **Does the agent ever attempt to edit prepare.py?**
   - What we know: CLAUDE.md says "NEVER modify prepare.py." No hard enforcement exists yet (that's Phase 5).
   - What's unclear: Whether the advisory instruction alone is sufficient.
   - Recommendation: `git diff HEAD -- prepare.py` after the run tells the truth. Phase 5 adds hard hooks regardless.

3. **Does `uv run python train.py` work in the experiment dir, or does the agent need a different invocation?**
   - What we know: train_template.py uses `from prepare import ...` (sibling import). `uv run python` should resolve this if run from the experiment dir with a `pyproject.toml`.
   - What's unclear: Whether the experiment dir's `uv sync` has been run, and whether the agent inherits the right environment.
   - Recommendation: Always run `uv sync` before invoking `claude -p`. Document if the agent runs into import errors.

4. **How many turns does the multi-draft phase consume?**
   - What we know: 3-5 drafts, each needing ~4-5 tool calls (edit, commit, run, grep, log).
   - What's unclear: The actual turn count per draft in practice.
   - Recommendation: `--max-turns 30` is the safe choice. Observe `num_turns` in the JSON output.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed in dev group) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths=["tests"] |
| Quick run command | `uv run pytest tests/ -q --ignore=tests/test_e2e.py` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements to Test Map

Phase 4 has no formal requirement IDs — it is an observational phase. However, the phase produces a FINDINGS.md that constitutes its artifact. The implicit testable conditions are:

| Observation | Test Type | Verification Command |
|-------------|-----------|---------------------|
| Scaffold CLI works on iris.csv | smoke | `uv run automl iris.csv species accuracy` exits 0 |
| Scaffolded train.py runs | smoke | `cd experiment-iris && uv run pytest tests/test_e2e.py -q` (existing slow tests) |
| Existing 111 tests still pass | regression | `uv run pytest tests/ -q` |
| FINDINGS.md exists after run | artifact check | `test -f .planning/phases/04-e2e-baseline-test/FINDINGS.md` |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -q --ignore=tests/test_e2e.py` (fast, < 5 seconds)
- **Per wave merge:** `uv run pytest tests/ -q` (full suite including slow e2e, ~20 seconds)
- **Phase gate:** Full suite green + FINDINGS.md populated before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_e2e_baseline.py` — A test that scaffolds iris.csv, runs train.py once (not via claude -p), and verifies structured output. This extends the existing `test_e2e.py` pattern with a classification target named "species".

*(The existing `test_e2e.py` uses a synthetic `sample_classification_csv` fixture with a column called "target". An iris-specific fixture using integer-labeled species verifies the actual dataset used in Phase 4.)*

---

## Sources

### Primary (HIGH confidence)
- Verified with `claude --version` and live CLI invocations, 2026-03-11 — `--max-turns`, `--max-budget-usd`, `--allowedTools`, `--output-format json` all confirmed working in v2.1.74
- `/home/tlupo/AutoML/src/automl/templates/claude.md.tmpl` — authoritative CLAUDE.md protocol text
- `/home/tlupo/AutoML/src/automl/runner.py` — regex pattern for metric extraction (`^metric_value:\s+(.+)$`)
- `/home/tlupo/AutoML/src/automl/scaffold.py` — confirms scaffold does NOT call `git init`
- `/home/tlupo/AutoML/src/automl/train_template.py` — confirms `signal.SIGALRM` timeout and structured output format

### Secondary (MEDIUM confidence)
- `.planning/research/claude-code-capabilities-research.md` — capability research from 2026-03-10 covering hooks, headless mode, `--allowedTools`, `--output-format json`

### Tertiary (LOW confidence)
- None — all claims verified against running system

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — CLI flags verified by live invocation against v2.1.74
- Architecture: HIGH — based on reading actual source code, not assumptions
- Pitfalls: HIGH — git init gap and nested session error confirmed by direct testing

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (Claude Code CLI flags change slowly; re-verify if version bumps to 3.x)
