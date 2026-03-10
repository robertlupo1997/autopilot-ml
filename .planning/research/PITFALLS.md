# Pitfalls Research

**Domain:** Autonomous ML Experiment Framework (Claude Code as orchestrator, tabular ML)
**Researched:** 2026-03-09
**Confidence:** HIGH (grounded in project research report covering AI Scientist, AIDE, MLE-bench, SELA, ML-Agent, AutoKaggle, and autoresearch)

## Critical Pitfalls

### Pitfall 1: Silent Failures -- Code Runs but Produces Garbage

**What goes wrong:**
The agent generates code that executes without errors but produces meaningless results: a model that predicts the majority class for everything (0.50 AUC), a regression that returns the mean for all inputs, or an ensemble that accidentally ignores half its sub-models. There is no stack trace. The metric looks "reasonable" (not NaN, not zero) so the agent keeps iterating on a broken foundation. AI Scientist's evaluation found it "cannot critically assess its own results" and fails to detect methodological flaws. MLE-bench confirmed top agents routinely miss pipeline errors.

**Why it happens:**
The keep/revert loop only checks whether metric > previous_best. It has no concept of "is this metric value plausible?" or "did the model actually learn something?" A 0.51 AUC on a balanced binary classification is essentially random, but if the previous best was 0.50, the agent keeps it and iterates from there.

**How to avoid:**
1. **Sanity-check baselines**: Before the agent loop starts, compute trivial baselines (majority-class predictor, mean predictor, random predictor). Store these as floor values. Any "improvement" that doesn't meaningfully exceed the floor triggers a warning.
2. **Metric plausibility checks**: Define metric ranges in the frozen evaluation module. For AUC, flag anything below 0.55 on a balanced dataset. For RMSE, flag anything worse than predicting the mean.
3. **Prediction distribution checks**: After each experiment, verify the prediction distribution is non-degenerate -- it should not be a single value, and its variance should be non-trivial relative to the target variance.
4. **Log prediction samples**: Write a small sample of (actual, predicted) pairs to run.log so the agent can spot obvious failures like constant predictions.

**Warning signs:**
- Metric improves by tiny amounts (0.001) over many iterations without ever making a significant jump
- Agent commits describe "improvements" that seem unrelated to the metric delta
- Prediction file has suspiciously low variance

**Phase to address:**
Phase 1 (Core Loop) -- sanity baselines and prediction distribution checks must be part of the frozen evaluation module from day one.

---

### Pitfall 2: Data Leakage in Automated Pipelines

**What goes wrong:**
The agent introduces data leakage that inflates metrics during the loop, producing a model that looks excellent in experiments but fails catastrophically on truly unseen data. Common leakage vectors: fitting a scaler on train+test before splitting, using target-encoded features computed on the full dataset, or accidentally including the target column (or a proxy) as a feature. Because the agent is optimizing a metric and leakage improves it, the keep/revert loop actively selects for leaky solutions.

**Why it happens:**
In v1, the frozen data pipeline should prevent this since the agent only modifies the modeling file. But the risk escalates in v2 (feature engineering) and v3 (full pipeline) where the agent can modify preprocessing. Even in v1, if the modeling file can create new feature transformations before calling fit(), leakage can sneak in.

**How to avoid:**
1. **v1: Hard boundary enforcement.** The frozen pipeline must provide X_train, X_test, y_train, y_test as pre-split numpy arrays or DataFrames. The modeling file receives these and returns predictions. It cannot access the raw dataset.
2. **v2+: Separate fit/transform enforcement.** Feature engineering code must use fit_transform on training data only and transform on test data. Consider a code validator that checks for this pattern.
3. **Holdout set the agent never sees.** Reserve 10-15% of data as a true holdout that is never used in the experiment loop. Run final evaluation against it to detect leakage (significant gap between loop metric and holdout metric = leakage).
4. **Cross-validation in the loop.** Use k-fold CV rather than a single train/test split to make leakage harder to exploit accidentally.

**Warning signs:**
- Metric is suspiciously close to perfect (AUC > 0.99 on a non-trivial problem)
- Large gap between training metric and validation metric... in the wrong direction (validation > training)
- Sudden large jumps in metric that the agent cannot explain via the code change

**Phase to address:**
Phase 1 (Core Loop) -- frozen pipeline design must make leakage structurally impossible in v1. Phase 2+ must add explicit leakage detection.

---

### Pitfall 3: Context Window Flooding

**What goes wrong:**
The agent's context fills with experiment logs, error traces, previous code versions, and git diffs until it loses track of the actual task. Claude Code's context window is large but finite. After 50+ experiments, the accumulated context degrades reasoning quality. The agent starts repeating ideas it already tried, ignoring relevant prior results, or making changes that contradict earlier successful strategies.

**Why it happens:**
Each experiment cycle adds: the code being modified, the execution output, the metric result, the git operation output, and the agent's own reasoning. At ~1000 tokens per cycle, 100 experiments consume 100k tokens of context -- enough to push critical information (the program.md, the evaluation function, the dataset description) out of the effective attention window.

**How to avoid:**
1. **Output redirection to run.log.** This is already planned (from autoresearch pattern). Execution output must NOT flow into the agent's context. Only the final metric value should be returned.
2. **Compact experiment history.** Maintain results.tsv as the authoritative experiment record. The agent reads this file (small, structured) rather than trying to remember all past experiments from context.
3. **Periodic context reset.** After every N experiments (e.g., 25), spawn a fresh sub-agent that reads only: program.md, current best code, results.tsv summary, and the evaluation function. This is the autoresearch "NEVER STOP" pattern -- it works because each iteration is self-contained.
4. **Structured logging, not verbose logging.** run.log captures full output for debugging. The agent sees only: metric value, pass/fail status, and a one-line description.

**Warning signs:**
- Agent starts proposing ideas it already tried (check results.tsv descriptions)
- Quality of code changes degrades over time (more syntax errors, less coherent strategies)
- Agent's reasoning becomes repetitive or contradictory
- Response latency increases significantly (sign of large context)

**Phase to address:**
Phase 1 (Core Loop) -- run.log redirect and results.tsv must be designed from the start. Context reset strategy should be implemented in the orchestrator layer.

---

### Pitfall 4: Agent Gets Stuck in Loops

**What goes wrong:**
The agent falls into a rut, trying minor variations of the same approach indefinitely. Example: it finds that XGBoost with max_depth=6 works best, then spends 100 iterations trying max_depth=5, max_depth=7, learning_rate=0.09, learning_rate=0.11, etc. -- micro-optimizations that yield diminishing returns while ignoring entirely different strategies (stacking, different algorithms, different feature subsets). ML-Agent's research explicitly identified "narrow action repetition" as a core limitation of prompt-based agents.

**Why it happens:**
LLMs are biased toward local search. Given a working solution, they tend to propose small modifications rather than radical alternatives. The keep/revert loop reinforces this: small changes that improve by 0.001 are "kept," training the agent's implicit reward signal to stay near the current solution. Without explicit exploration pressure, the agent converges prematurely.

**How to avoid:**
1. **Stagnation detection.** Track the rolling improvement rate. If the last N experiments (e.g., 10) have all been reverted or improved by less than epsilon, trigger an exploration phase.
2. **Exploration prompts.** When stagnation is detected, inject a prompt override: "The current approach has plateaued. Try a fundamentally different algorithm or strategy. Do NOT make incremental changes to the current approach."
3. **Multi-draft restarts.** The planned multi-draft start partially addresses this. Consider periodic re-drafting: after 50 linear iterations, generate 2-3 new diverse drafts and compare against the current best.
4. **Strategy tracking in results.tsv.** Add a "strategy" column (e.g., "xgboost-tuning", "lightgbm-tuning", "ensemble", "feature-selection") so the agent (and stagnation detector) can see when it has been in one strategy too long.

**Warning signs:**
- Long streaks of reverted experiments (>10 consecutive reverts)
- Experiment descriptions are nearly identical ("adjusted learning_rate", "adjusted learning_rate", "adjusted learning_rate")
- Metric has not improved in the last 20 experiments
- Agent cycles between the same 2-3 hyperparameter values

**Phase to address:**
Phase 1 (Core Loop) -- stagnation detection must be built into the orchestrator. Multi-draft start provides initial diversity. Exploration prompts are a Phase 2 enhancement.

---

### Pitfall 5: Metric Gaming and Overfitting to Validation Set

**What goes wrong:**
MLE-bench's key finding: agents overfit to validation metrics. The agent finds strategies that exploit the specific train/test split rather than learning generalizable patterns. It might discover that a particular random seed produces a favorable split, or that a specific threshold optimizes F1 on this particular test set. The loop metric goes up, but true out-of-sample performance goes down. This is especially pernicious because it looks like progress.

**Why it happens:**
With hundreds or thousands of experiments on the same dataset, even random exploration will find configurations that happen to score well on a fixed test set by chance. This is a form of multiple hypothesis testing -- with 1000 experiments, you expect some to look significant by luck. The keep/revert loop is essentially hill-climbing on a noisy objective, and with enough iterations, it overfits to the noise.

**How to avoid:**
1. **Hidden holdout set.** Reserve data the agent never sees. Periodically evaluate the current best model on this holdout to track true generalization.
2. **Cross-validation instead of single split.** Use 5-fold CV as the loop metric. Overfitting to 5 folds simultaneously is much harder than overfitting to one split.
3. **Track generalization gap.** Monitor the difference between training metric and CV metric. A widening gap signals overfitting.
4. **Complexity penalty.** The planned "simplicity criterion" directly addresses this. Prefer simpler models unless the improvement is substantial (not just 0.001 AUC).
5. **Early stopping on overfitting.** If the hidden holdout performance degrades while the loop metric improves, halt and revert to the best holdout-performing model.

**Warning signs:**
- Loop metric improves but the improvement comes from obscure hyperparameter combinations rather than meaningful model changes
- Model complexity increases monotonically (more estimators, deeper trees, more features)
- Very high training accuracy with only slightly better validation accuracy

**Phase to address:**
Phase 1 (Core Loop) -- cross-validation should be the default metric. Hidden holdout should be part of the frozen pipeline. Complexity penalty is Phase 1 design.

---

### Pitfall 6: Git State Corruption

**What goes wrong:**
The agent's git operations leave the repository in an inconsistent state: uncommitted changes that conflict with a reset, detached HEAD, merge conflicts from botched branch operations, or corrupted working tree. When the next experiment starts, it either fails to run (error) or runs on the wrong code (silent failure -- even worse). Autoresearch uses git as its primary state management mechanism, so git corruption means experiment corruption.

**Why it happens:**
Git operations are stateful and order-dependent. If the agent runs a training script, it crashes mid-execution, and the agent then tries to git reset, there may be partially written files. If the agent forgets to stage a file before committing, the commit doesn't capture the full state. If the run.log or results.tsv is open/locked when a reset happens, the file may be in an inconsistent state.

**How to avoid:**
1. **Atomic git operations.** Wrap git add + commit in a single helper function that either succeeds completely or fails completely. Never let the agent run raw git commands.
2. **Pre-experiment git status check.** Before each experiment, verify: working tree is clean, HEAD is on the expected branch, no uncommitted changes. If any check fails, auto-recover before proceeding.
3. **Git operations are orchestrator-only.** The agent's modeling code should not interact with git at all. The orchestrator (outer loop) handles all version control. The modeling file is just Python code that runs and produces output.
4. **Branch-per-run isolation.** Each autonomous run operates on its own branch. If state is corrupted, the main branch is unaffected. Recovery = create a new branch from the last known good commit.
5. **Gitignore large/temp files.** Ensure model artifacts, __pycache__, .pyc files, and temporary data files are gitignored so they don't cause staging issues.

**Warning signs:**
- Git commands return unexpected output or errors
- `git status` shows untracked or modified files that should be clean
- Two consecutive experiments show the same code despite supposed modifications
- results.tsv and actual git history disagree on experiment count

**Phase to address:**
Phase 1 (Core Loop) -- git helper functions with safety checks are foundational infrastructure. Must be built and tested before the experiment loop runs.

---

### Pitfall 7: Over-Complexity in Generated Code

**What goes wrong:**
The agent generates increasingly baroque modeling code: custom loss functions, exotic ensemble architectures, 500-line preprocessing pipelines with 20 nested transformers. AI Scientist was characterized as producing work resembling "an unmotivated undergraduate rushing to meet a deadline" -- technically functional but lacking coherence. Complex code is harder to debug, more likely to contain subtle bugs, and harder for the agent to reason about in subsequent iterations.

**Why it happens:**
LLMs default to showing off their knowledge. Given a prompt to "improve" a model, they tend to add complexity rather than simplify. Each iteration adds a layer, a transformer, a postprocessing step. The keep/revert loop doesn't penalize complexity -- it only checks if the metric improved. A 500-line solution that scores 0.001 better than a 50-line solution is "kept."

**How to avoid:**
1. **Enforce the simplicity criterion.** The planned "improvements must justify their complexity cost" rule should be operationalized. Measure complexity as lines of code, number of hyperparameters, or number of model components. Require improvements to clear a threshold relative to added complexity.
2. **Single-file constraint.** Autoresearch's key insight: one file. The agent cannot create new modules, import custom utilities, or build framework abstractions. Everything lives in one modeling file. This naturally caps complexity.
3. **Code length limits.** Hard cap the modeling file at N lines (e.g., 200 for v1). If the agent generates code exceeding this, reject it before execution.
4. **Explicit prompt instructions.** Include in program.md: "Prefer simple, readable solutions. A 10-line improvement is better than a 100-line improvement with the same metric gain. Never use custom loss functions or exotic architectures unless explicitly needed."

**Warning signs:**
- Modeling file grows monotonically across experiments
- Agent introduces abstractions (classes, utilities, helper functions) when flat procedural code would suffice
- Experiment descriptions mention multiple simultaneous changes ("added custom loss, ensemble wrapper, and feature selector")
- Code contains try/except blocks that silently swallow errors

**Phase to address:**
Phase 1 (Core Loop) -- single-file constraint and code length limits are design decisions. Simplicity criterion is a Phase 1 scoring/evaluation rule.

---

### Pitfall 8: Claude Code Orchestrator-Specific Failures

**What goes wrong:**
Claude Code as the orchestrator introduces its own failure modes distinct from the ML domain: (a) permission prompts that block autonomous operation (file write, bash execution), (b) tool call failures that the agent doesn't recover from gracefully, (c) the agent interpreting tool output incorrectly (e.g., treating a warning as an error), (d) sub-agent spawning failures or communication issues, (e) rate limiting or API failures during long autonomous runs.

**Why it happens:**
Claude Code is designed for interactive use with human oversight. Using it as an autonomous orchestrator for hundreds of experiments pushes it outside its primary design envelope. The "NEVER STOP" pattern requires sustained operation without human intervention, but Claude Code's safety features (permission prompts, timeout limits) are designed to keep a human in the loop.

**How to avoid:**
1. **Pre-authorize all needed operations.** Before starting the autonomous loop, establish that all necessary file operations, bash commands, and git operations are pre-approved. Use CLAUDE.md or allowed-tools configuration.
2. **Robust error handling in the orchestrator loop.** Every tool call (bash, file read/write, git) must have explicit error handling. If a tool fails, log the failure, skip that experiment, and continue to the next.
3. **Heartbeat mechanism.** Log a timestamp to a heartbeat file every N experiments. If the heartbeat stops updating, something went wrong. A separate watchdog process can alert or restart.
4. **Graceful degradation on API failures.** If a Claude API call fails (rate limit, timeout), implement exponential backoff and retry. After M retries, save state and halt cleanly rather than corrupting the experiment.
5. **Test the full loop end-to-end before long runs.** Run 10 experiments supervised before starting a 1000-experiment overnight run.

**Warning signs:**
- Agent pauses waiting for permission approval during autonomous operation
- Experiments slow down significantly over time (rate limiting or context bloat)
- Agent produces error messages about tool failures but continues with incorrect state
- Sub-agent spawning stops working silently

**Phase to address:**
Phase 1 (Core Loop) -- Claude Code integration and the autonomous operation mode must be tested early. Permission pre-authorization is a setup/configuration concern.

---

### Pitfall 9: Multi-Draft Selection Bias

**What goes wrong:**
The multi-draft start (3-5 diverse initial solutions) sounds good in theory, but in practice the "best" draft is selected based on a single evaluation on a single split. This is noisy. The draft that wins the initial comparison may not be the best foundation for iterative improvement. A draft that scores 0.82 initially might plateau at 0.85, while a draft that scored 0.80 might have reached 0.90 with iteration (because it was a simpler, more improvable architecture).

**Why it happens:**
Evaluating "which starting point has the most improvement potential" is a much harder problem than "which starting point currently scores highest." AIDE addresses this with tree search (exploring multiple branches simultaneously), but v1's design explicitly chooses linear iteration on the single best draft to keep things simple.

**How to avoid:**
1. **Use CV for draft selection, not a single split.** Reduces noise in the initial comparison.
2. **Run a few iterations on each draft before selecting.** Instead of picking the best draft at iteration 0, run 5 iterations on each draft and pick the one with the best score at iteration 5. This tests improvability, not just initial quality.
3. **Keep runner-up drafts.** If the selected draft stagnates (pitfall 4), switch to the next-best draft rather than staying stuck.
4. **Ensure true diversity.** Explicitly require drafts to use different algorithm families (tree-based, linear, kernel, ensemble). Reject drafts that are just hyperparameter variants of the same algorithm.

**Warning signs:**
- All drafts use variations of the same algorithm (e.g., all gradient boosters)
- The winning draft was only marginally better than alternatives
- Linear iteration on the winning draft quickly plateaus

**Phase to address:**
Phase 1 (Core Loop) -- draft generation and selection logic. The "keep runner-up drafts" strategy is a Phase 2 enhancement.

---

### Pitfall 10: Inadequate Experiment Logging

**What goes wrong:**
The results.tsv captures metric and status but not enough information to learn from failed experiments. When the agent (or human reviewer) looks at the history, they see "attempt 47: reverted, AUC=0.78" but not what was tried, why it was expected to work, or what error occurred. The experiment history becomes a meaningless list of numbers. Post-run analysis (understanding what worked and why) becomes impossible.

**Why it happens:**
Logging is unsexy. The temptation is to capture just the metric and move on. But without structured metadata, the experiment history is useless for: (a) the agent learning from its own failures, (b) humans understanding what happened overnight, (c) debugging why a promising approach failed.

**How to avoid:**
1. **Rich results.tsv schema.** Capture: commit_hash, timestamp, metric_value, status (keep/revert), strategy_category, description, code_diff_summary, error_type (if failed), duration_seconds.
2. **Force the agent to explain each experiment.** Before running, the agent writes a one-line hypothesis. After running, it writes a one-line conclusion. Both go into results.tsv.
3. **Diff capture.** Store the git diff for each experiment (or at least reference the commit hash that contains it). This enables post-run analysis of what code changes correlated with improvements.
4. **Summary generation.** After every N experiments, generate a brief summary: "Best so far: XGBoost with max_depth=8, AUC=0.87. Last 10 experiments explored ensemble strategies with no improvement."

**Warning signs:**
- results.tsv has many rows but descriptions are empty or generic ("tried something")
- After an overnight run, a human cannot understand what was explored
- Agent proposes experiments it already tried because the history is not informative enough

**Phase to address:**
Phase 1 (Core Loop) -- results.tsv schema design is foundational. Must be specified before the first experiment runs.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Single train/test split instead of CV | 3-5x faster experiments | Overfitting to the specific split, unreliable metrics | Never for the keep/revert decision metric. Acceptable for initial draft filtering only. |
| No hidden holdout set | Uses all available data for training | Cannot detect overfitting to the loop; no ground truth for generalization | Never -- always reserve a holdout, even a small one (5-10%). |
| Hardcoded metric parsing (grep/regex) | Avoids LLM-as-judge complexity | Breaks when output format changes; fragile to whitespace, encoding | Acceptable in v1 if the output format is frozen in the evaluation module. |
| No code length limit | Agent has full creative freedom | Complexity creep; unmaintainable code; harder for agent to reason about | Never for v1 -- enforce a cap. Relax in v2 if monitoring shows the agent self-regulates. |
| Raw git commands instead of helper functions | Faster to implement initially | Git state corruption; inconsistent error handling; no recovery logic | Never -- wrap from day one. The cost is 1-2 hours upfront vs. debugging corrupted state overnight. |
| No timeout on experiment execution | Simple implementation | A single experiment hangs forever, blocking the entire loop | Never -- always set a timeout (e.g., 5 minutes for traditional ML). |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Claude Code + Git | Letting the agent run arbitrary git commands | Provide git helper functions (commit, reset, branch) that enforce invariants. Agent never runs raw git. |
| Claude Code + Bash execution | Not capturing stderr separately from stdout | Redirect stderr to run.log, capture only the metric line from stdout. Return structured result to agent. |
| Claude Code + File I/O | Agent modifies files outside the mutable zone | Enforce file-level permissions: agent can only write to the modeling file. All other files are read-only to the agent. |
| scikit-learn + Pandas | Agent creates a pipeline that silently converts DataFrame to numpy, losing column names | Standardize on numpy arrays in the frozen pipeline interface. DataFrames only in preprocessing (frozen). |
| XGBoost/LightGBM + Random seeds | Agent discovers that a specific random_state scores better and "locks in" to it | Force random_state=42 (or similar fixed seed) in the frozen pipeline. Agent cannot change the seed. |
| results.tsv + Git | results.tsv gets merge conflicts on reset/revert | Append-only design. Never revert results.tsv -- it tracks all experiments including reverted ones. Exclude from git reset scope. |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Agent trains full dataset every iteration | Each experiment takes minutes instead of seconds | Use a fast subsample (10-20% of data) for exploration, full dataset only for final validation | Datasets > 100k rows |
| Agent builds massive ensembles | Prediction time grows linearly with ensemble size | Cap ensemble members (e.g., max 5 models in a stack) | Ensemble > 10 models |
| Agent imports heavy libraries each run | Python startup time dominates experiment time | Pre-import common libraries in the evaluation harness | When experiments < 5 seconds each |
| Context window grows unboundedly | Claude API calls get slower, more expensive, less accurate | Periodic context reset (fresh sub-agent with minimal context) | After ~50 experiments |
| Agent runs grid search inside a single experiment | One "experiment" takes 30 minutes and 1000 CPU-minutes | Prohibit internal grid search in program.md. Each experiment = one configuration. | Always -- the outer loop IS the search. |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Agent generates code with `eval()` or `exec()` | Arbitrary code execution from LLM-generated strings | Static analysis check on generated code before execution. Ban eval/exec in the mutable file. |
| Agent installs packages via pip during experiments | Supply chain attack; dependency conflicts; non-reproducible environments | Freeze dependencies in pyproject.toml. Agent cannot run pip/uv install. All libraries pre-installed. |
| Agent reads files outside the project directory | Data exfiltration; accidental modification of system files | Sandbox the execution environment. Restrict file access to the project directory. |
| Agent writes to program.md or frozen pipeline files | Agent modifies its own instructions or evaluation criteria | File-level write protection enforced by the orchestrator, not just by prompt instructions. |
| Secrets in git history | API keys, credentials committed to experiment branch | .gitignore secrets files. No environment variables in the modeling file. |

## "Looks Done But Isn't" Checklist

- [ ] **Experiment loop works:** Often missing timeout handling -- verify what happens when an experiment hangs for 10 minutes.
- [ ] **Git state management works:** Often missing recovery from dirty state -- verify what happens when an experiment crashes mid-execution before commit.
- [ ] **Output redirection works:** Often missing stderr capture -- verify that Python tracebacks go to run.log, not agent context.
- [ ] **results.tsv is append-only:** Often missing on git reset -- verify that reverting an experiment does NOT delete the results.tsv row.
- [ ] **Multi-draft generates diverse solutions:** Often all drafts are XGBoost variants -- verify at least 3 different algorithm families.
- [ ] **Simplicity criterion is enforced:** Often just a prompt instruction with no teeth -- verify that a complex solution with a tiny improvement is actually rejected.
- [ ] **Frozen pipeline is actually frozen:** Often the agent can still modify it via creative workarounds -- verify that importing and monkey-patching the evaluation function fails.
- [ ] **"NEVER STOP" actually never stops:** Often the agent stops after hitting an unexpected error -- verify with a 50-experiment stress test.
- [ ] **Metric parsing is robust:** Often breaks on scientific notation or extra whitespace -- verify with edge-case outputs.
- [ ] **Stagnation detection fires:** Often the threshold is too lenient -- verify it triggers after a reasonable number of no-improvement experiments.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Silent failure (garbage predictions) | LOW | Revert to last known-good commit. Add prediction distribution check. Re-run from that point. |
| Data leakage detected | HIGH | Discard all experiment results after the leaky commit. Fix the pipeline. Restart from scratch -- all metrics are unreliable. |
| Context window flooded | LOW | Spawn fresh sub-agent with minimal context (program.md, current best code, results.tsv). Continue from where it left off. |
| Agent stuck in loop | LOW | Trigger exploration prompt. Or: manually select a different draft/strategy and restart linear iteration. |
| Metric gaming / overfitting | MEDIUM | Evaluate current best on hidden holdout. If holdout performance is significantly worse, revert to the commit with best holdout performance and add CV to the loop metric. |
| Git state corrupted | MEDIUM | Identify last known-good commit from results.tsv. Create new branch from that commit. Manually verify working tree is clean. Resume. |
| Over-complex generated code | LOW | Revert to last simple version that performed well. Tighten code length limit. Add complexity penalty to the evaluation. |
| Claude Code orchestrator failure | MEDIUM | Check heartbeat file for last successful experiment. Resume from that commit. Review tool failure logs to prevent recurrence. |
| Multi-draft selection bias | MEDIUM | After stagnation on selected draft, switch to runner-up draft and run 20 iterations. Compare best results. |
| Inadequate logging | LOW | Retroactively enrich results.tsv by replaying git history (diff per commit). Fix schema going forward. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Silent failures | Phase 1: Core Loop | Sanity baselines computed before first experiment; prediction distribution check passes on known-good and known-bad models |
| Data leakage | Phase 1: Frozen Pipeline Design | Agent receives pre-split arrays only; hidden holdout exists and is never exposed to agent code |
| Context flooding | Phase 1: Orchestrator Design | run.log redirect works; agent context stays under 50k tokens after 50 experiments |
| Stuck in loops | Phase 1: Orchestrator Design + Phase 2: Enhanced Search | Stagnation detector triggers on synthetic test (20 no-improvement experiments) |
| Metric gaming | Phase 1: Evaluation Design | CV is default metric; hidden holdout shows <2% gap from loop metric after 100 experiments |
| Git corruption | Phase 1: Infrastructure | Git helper functions pass stress test (100 rapid commit/reset cycles with simulated crashes) |
| Over-complexity | Phase 1: Constraints Design | Code length limit enforced; oversized code is rejected before execution |
| Claude Code failures | Phase 1: Orchestrator Design | 50-experiment stress test completes without human intervention |
| Multi-draft bias | Phase 1: Draft Logic + Phase 2: Enhancement | Drafts span 3+ algorithm families; runner-up preservation implemented |
| Inadequate logging | Phase 1: Schema Design | results.tsv schema includes all required columns; post-run analysis produces meaningful summary |

## Sources

- Autonomous ML Agents Research Report (project file: `Autonomous_ML_Agents_Research_Report.docx`) -- comprehensive landscape analysis covering AI Scientist, AIDE, MLE-bench, SELA, ML-Agent, AutoKaggle, and autoresearch
- AI Scientist evaluation: 42% experiment failure rate, inability to self-assess results (Sakana AI, arXiv:2504.08066)
- MLE-bench findings: agents overfit to validation metrics, miss pipeline errors (OpenAI, arXiv:2410.07095)
- AIDE architecture: tree search, atomic improvements, separation of concerns (Weco AI, arXiv:2502.13138)
- ML-Agent: narrow action repetition as core agent limitation (arXiv:2505.23723)
- Autoresearch: single-file constraint, git state management, run.log redirect pattern (Karpathy, github.com/karpathy/autoresearch)
- AutoKaggle: 85% valid submission rate vs. AIDE's lower rate, unit testing emphasis (arXiv:2410.20424)

---
*Pitfalls research for: Autonomous ML Experiment Framework (Claude Code orchestrator, tabular ML)*
*Researched: 2026-03-09*
