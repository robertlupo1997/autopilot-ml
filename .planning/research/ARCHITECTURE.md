# Architecture Patterns

**Domain:** Autonomous ML Experiment Framework (Tabular)
**Researched:** 2026-03-09

## Reference Architecture Analysis

Three frameworks were studied to extract architectural patterns. Each makes different tradeoffs between simplicity, search effectiveness, and scope.

### Autoresearch (Karpathy) -- 3-File Constraint

```
program.md    -- Human strategy document (read-only by agent)
prepare.py    -- Frozen data pipeline: loading, splitting, evaluation (read-only)
train.py      -- Mutable experiment file: model, hyperparams, training loop (agent edits)
```

**Key insight:** Radical constraint. The agent edits exactly ONE file. State lives in git (branch per run, commit on keep, reset on revert). Output goes to `run.log` to avoid flooding context. Results accumulate in `results.tsv` (untracked). The loop is: edit -> commit -> run -> grep metric -> keep/revert. No orchestration layer exists -- Claude Code IS the orchestrator via `program.md` instructions.

**What transfers directly:** File boundary pattern, git state management, run.log redirect, results.tsv tracking, program.md as domain expertise injection, "NEVER STOP" autonomous operation.

**What does NOT transfer:** Single-metric GPU training (we need configurable metrics), fixed time budget (tabular ML runs in seconds, not minutes), single-algorithm scope (we need multi-algorithm exploration).

### AIDE (Weco AI) -- Tree Search with Journal

```
agent.py       -- Orchestration: decides draft/debug/improve action
journal.py     -- Tree-structured experiment history (nodes = solutions)
interpreter.py -- Sandboxed code execution with timeout
```

**Key insight:** Three distinct modes -- Drafting (new solutions from scratch), Debugging (repair broken solutions from error logs), Improving (exactly ONE atomic change to a working solution). The tree structure enables branching: multiple improvement paths from the same parent. The journal tracks full lineage -- which solution spawned which, what changed, what scored.

**What transfers:** Multi-draft start (3-5 diverse initial solutions), atomic improvement discipline (one change per iteration), separation of draft/debug/improve modes, structured experiment journal.

**What does NOT transfer (for v1):** Full tree search (too complex for v1), two-model architecture (separate planning and coding models), LLM-as-judge metric extraction, pip-installable library structure.

### SELA (MetaGPT/Tsinghua) -- Stage-wise MCTS

```
Stages: EDA -> Preprocessing -> Feature Engineering -> Model Training
Each stage: LLM generates "insights" -> expand into implementations -> MCTS scores
```

**Key insight:** The ML pipeline is decomposed into stages with independent search at each stage. MCTS (Monte Carlo Tree Search) balances exploration vs. exploitation. Insights at each stage are independent -- you can explore feature engineering without re-searching model selection.

**What transfers (for v2+):** Stage-wise decomposition maps directly to our mutable zones concept. v1 = model stage only, v2 = model + feature stages, v3 = full pipeline stages. The insight that stages can be searched independently validates our staged mutable zones design.

**What does NOT transfer:** MCTS complexity (overkill for v1), multi-agent collaboration, UCB exploration formulas.

---

## Recommended Architecture

### Design Philosophy

Claude Code is the orchestrator. There is no separate agent framework, no Python orchestration layer, no custom state management system. The framework is a set of **files and conventions** that Claude Code operates on, not a program that runs Claude Code. This is the critical difference from AIDE/SELA -- those are Python programs that call LLMs. Ours is an LLM (Claude Code) that operates on Python files.

### System Diagram

```
                    Human
                      |
                      v
              +-- program.md --+          (domain expertise, strategy hints)
              |                |
              v                v
        Claude Code (Orchestrator)
         |        |         |
         v        v         v
    [READ-ONLY]  [MUTABLE]  [STATE]
    +---------+  +--------+ +------------+
    |prepare.py| |train.py | |results.tsv |
    |          | |         | |run.log     |
    |  - load  | | - model | |git commits |
    |  - split | | - hyper | |git branch  |
    |  - eval  | | - ensem | +------------+
    |  - metric| | - prepr*|
    +---------+ +--------+
         |           |
         v           v
    [DATASET]    [EXECUTION]
    input.csv    uv run train.py > run.log 2>&1
```

*prepr = preprocessing, unlocked in v2+

### Component Boundaries

| Component | Responsibility | Communicates With | Mutability |
|-----------|---------------|-------------------|------------|
| **program.md** | Human domain expertise, strategy hints, dataset context, known patterns, metric definition | Claude Code reads it | Human-written, agent reads only |
| **prepare.py** | Data loading, train/test split, evaluation function, metric computation | train.py imports from it | Frozen in v1. Partially mutable in v3 |
| **train.py** | Model selection, hyperparameters, ensemble strategies, preprocessing (v2+) | Imports prepare.py utilities, writes predictions | Mutable -- agent's workspace |
| **results.tsv** | Experiment history: commit hash, metric value, status, description | Claude Code appends rows | Append-only, untracked by git |
| **run.log** | Full stdout/stderr from experiment execution | Claude Code reads selectively (grep metric, tail errors) | Overwritten each run |
| **git** | State management: branch per run, commit on keep, reset on revert | Claude Code issues git commands | Managed by Claude Code |
| **input.csv** | Raw dataset | prepare.py reads it | Immutable |

### The Mutable Zone Contract

Each mutable zone has a strict interface contract with the frozen layer:

**v1 Contract (model-only):**
```python
# prepare.py PROVIDES (frozen):
X_train, X_test, y_train, y_test = load_and_split(csv_path)
score = evaluate(y_test, predictions, metric_name)

# train.py MUST (mutable):
# 1. Import X_train, X_test, y_train, y_test from prepare
# 2. Build and train a model
# 3. Generate predictions on X_test
# 4. Call evaluate() and print the result in parseable format
# 5. Complete within timeout (default: 120 seconds)
```

**v2 Contract (model + features):**
```python
# prepare.py PROVIDES (frozen):
df_train, df_test, target_col = load_raw(csv_path)
score = evaluate(y_test, predictions, metric_name)

# train.py MUST (mutable):
# 1. Import raw dataframes from prepare
# 2. Engineer features (new in v2)
# 3. Build and train a model
# 4. Generate predictions
# 5. Call evaluate() and print result
```

**v3 Contract (full pipeline):**
```python
# prepare.py PROVIDES (frozen):
csv_path, target_col, metric_name = load_config()
score = evaluate(y_test, predictions, metric_name)

# train.py MUST (mutable):
# 1. Load and clean data (new in v3)
# 2. Engineer features
# 3. Build and train a model
# 4. Generate predictions
# 5. Call evaluate() and print result
```

### Data Flow

```
1. INITIALIZATION
   Human writes program.md -> describes dataset, metric, domain context
   Human places input.csv in project directory
   Framework generates prepare.py from template (frozen after generation)
   Framework generates initial train.py (baseline)

2. MULTI-DRAFT PHASE (runs once at start)
   Claude Code generates 3-5 diverse train.py variants:
     Draft 1: XGBoost with default hyperparams
     Draft 2: LightGBM with default hyperparams
     Draft 3: RandomForest
     Draft 4: LogisticRegression / Ridge (linear baseline)
     Draft 5: (optional) simple ensemble of above

   For each draft:
     git commit train.py
     uv run train.py > run.log 2>&1
     grep metric from run.log
     log to results.tsv

   Select best-performing draft as starting point

3. LINEAR IMPROVEMENT PHASE (runs indefinitely)
   LOOP:
     Claude Code reads: program.md, train.py, results.tsv, (optionally run.log)
     Claude Code proposes ONE atomic change to train.py
     git commit
     uv run train.py > run.log 2>&1
     Extract metric from run.log

     IF metric improved:
       Log "keep" to results.tsv
       Continue from this commit (branch advances)
     ELSE:
       Log "discard" to results.tsv
       git reset --hard to previous good commit
       Continue from previous good commit

     IF crash:
       tail -n 50 run.log for error
       Attempt fix (max 2-3 retries)
       If unfixable: log "crash", revert, move on

4. METRIC EXTRACTION
   train.py prints result in fixed format:
     metric_name: 0.8543
   Claude Code extracts via:
     grep "^metric_name:" run.log
   Comparison: higher_is_better or lower_is_better (configured in prepare.py)
```

### Git State Management

```
main
  |
  +-- automl/<run-tag>          (branch created per run)
        |
        +-- [baseline commit]   (initial train.py)
        +-- [draft-1 commit]    (XGBoost variant)
        +-- [draft-2 commit]    (LightGBM variant)  <- best draft selected
        |     \-- [revert to here if draft-3 worse]
        +-- [draft-3 commit]    (RandomForest) <- evaluated, reverted
        +-- [improve-1 commit]  (tune LightGBM lr) <- kept, improved
        +-- [improve-2 commit]  (add regularization) <- kept
        +-- [improve-3 commit]  (try bagging) <- reverted (no improvement)
        +-- [improve-4 commit]  (increase n_estimators) <- kept
        ...
```

**Branch naming:** `automl/<dataset>-<date>` (e.g., `automl/housing-mar9`)
**Commit messages:** Short, descriptive of what changed (e.g., "tune XGBoost learning_rate from 0.1 to 0.05")
**results.tsv is NOT committed** -- it lives as an untracked file, following autoresearch's pattern. This avoids merge conflicts and keeps the git log clean for code-only diffs.

---

## Patterns to Follow

### Pattern 1: Frozen Evaluation Boundary
**What:** The evaluation function lives in prepare.py and is NEVER modified by the agent. It takes predictions and ground truth, returns a single scalar score.
**When:** Always. This is the foundation of trustworthy autonomous experimentation.
**Why:** If the agent can modify the evaluation, it can "cheat" -- optimizing the metric function instead of the model. Autoresearch, AIDE, and MLE-bench all enforce this boundary.
```python
# prepare.py (frozen)
def evaluate(y_true, y_pred, metric="rmse"):
    """Fixed evaluation. Agent cannot modify this."""
    if metric == "rmse":
        return -np.sqrt(mean_squared_error(y_true, y_pred))  # negative so higher=better
    elif metric == "auc":
        return roc_auc_score(y_true, y_pred)
    elif metric == "f1":
        return f1_score(y_true, y_pred, average="weighted")
    # ... etc
```

### Pattern 2: Atomic Improvements (from AIDE)
**What:** Each iteration changes exactly ONE thing in train.py. Never two changes at once.
**When:** During the linear improvement phase (after multi-draft selection).
**Why:** If you change both the learning rate AND add feature scaling simultaneously, you cannot attribute the result to either change. AIDE found this discipline critical for effective search -- it prevents "improvement masking" where a good change is hidden by a simultaneous bad change.

### Pattern 3: Output Redirection (from Autoresearch)
**What:** All experiment output goes to `run.log` via `uv run train.py > run.log 2>&1`. The agent reads ONLY the metric line via grep, and only reads the full log on crash.
**When:** Every experiment execution.
**Why:** Training output can be thousands of lines. If it floods the agent's context window, the agent loses track of its strategy. Autoresearch solved this cleanly: redirect everything, grep what you need.

### Pattern 4: Simplicity Criterion (from Autoresearch)
**What:** All else being equal, simpler code is preferred. A tiny improvement that adds ugly complexity is not worth keeping. Removing code for equal performance is a win.
**When:** Every keep/revert decision.
**Why:** Without this constraint, the agent's code accumulates cruft over 100+ iterations, becoming unmaintainable and eventually breaking in subtle ways.

### Pattern 5: Multi-Draft Start (from AIDE)
**What:** Generate 3-5 completely different solutions before iterating. Different algorithms, not just different hyperparameters.
**When:** At the beginning of each run, before the linear improvement loop.
**Why:** AIDE's most impactful finding: algorithm choice often matters more than hyperparameter tuning. Starting with the wrong algorithm and iterating on hyperparameters can never reach the performance of the right algorithm with default hyperparameters.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Agent Modifies Evaluation
**What:** Letting the agent edit the metric computation or train/test split.
**Why bad:** The agent optimizes whatever it can. If it can modify the evaluation, it will find shortcuts (e.g., data leakage via test set information, metric manipulation). Every framework in the landscape enforces evaluation immutability.
**Instead:** Hard boundary in prepare.py. Agent imports evaluation function, cannot modify it.

### Anti-Pattern 2: Context Window Flooding
**What:** Letting training output stream directly into the agent's conversation.
**Why bad:** Tabular ML experiments may print feature importance tables, cross-validation folds, convergence logs -- hundreds of lines. After 10 experiments, the agent's context is overwhelmed with irrelevant log data, losing track of strategy and history.
**Instead:** Redirect to run.log, grep metric, tail on crash only.

### Anti-Pattern 3: Multiple Changes Per Iteration
**What:** "Let me try a new algorithm AND new hyperparameters AND add feature scaling."
**Why bad:** Cannot attribute success/failure to any single change. If the combined result is worse, a good idea may be discarded because it was bundled with a bad idea.
**Instead:** One atomic change per commit. Test. Keep or revert. Then the next change.

### Anti-Pattern 4: Custom State Management
**What:** Building a database, JSON store, or Python object model to track experiment state.
**Why bad:** Adds complexity, introduces bugs, requires maintenance. Git already provides atomic commits, branching, resetting, full audit trail, and diff capabilities.
**Instead:** Git branches + commits + results.tsv (untracked). Proven by autoresearch at scale (100+ experiments per run).

### Anti-Pattern 5: Over-Engineering the Orchestrator
**What:** Building a Python-based orchestrator that calls Claude API, manages state, handles retries.
**Why bad:** Claude Code already IS an orchestrator. It can run commands, read files, edit files, manage git, make decisions. Building another orchestration layer on top creates unnecessary abstraction.
**Instead:** The "orchestrator" is a CLAUDE.md / program.md file that tells Claude Code what to do. The framework is files and conventions, not a program.

---

## Staged Mutable Zones -- Detailed Design

The key architectural innovation is progressive scope expansion. Each version unlocks a new "zone" the agent can modify, while keeping all prior zones and the evaluation boundary intact.

### v1: Model-Only Zone

```
FROZEN: prepare.py (load CSV, split, evaluate, feature extraction)
MUTABLE: train.py (model selection, hyperparameters, ensembles)
SCOPE: Algorithm choice, hyperparameter tuning, ensemble methods, training tricks
CONSTRAINT: Agent receives X_train/X_test as pre-processed numpy arrays
```

**Why start here:** Model selection is the highest-leverage intervention for tabular ML (AIDE research confirms this). It is also the safest -- the agent cannot corrupt data or introduce leakage when it only touches model code. This proves the experiment loop works before expanding scope.

### v2: Model + Feature Zone

```
FROZEN: prepare.py (load CSV, split, evaluate)
MUTABLE: train.py (model selection + feature engineering + preprocessing)
SCOPE: Everything in v1, plus: feature creation, feature selection, scaling, encoding, imputation
CONSTRAINT: Agent receives raw dataframes, must produce predictions
NEW RISK: Feature leakage (fitting scalers on test data), expensive feature computation
```

**Why second:** Feature engineering is the second-highest-leverage intervention. But it introduces leakage risk -- the agent must learn to fit transformers on train only and apply to test. This requires the experiment loop to be proven reliable first.

### v3: Full Pipeline Zone

```
FROZEN: evaluate() function only
MUTABLE: Everything else (loading, cleaning, splitting, features, model, post-processing)
SCOPE: Full pipeline control including data cleaning, custom splits, custom preprocessing
CONSTRAINT: Agent must produce predictions that evaluate() can score
NEW RISK: Train/test leakage via custom splits, data corruption, very long experiment times
```

**Why last:** Full pipeline control is highest risk. The agent could introduce subtle data leakage via custom cross-validation, or corrupt the dataset via aggressive cleaning. This should only be unlocked after the agent has proven disciplined at lower scopes.

---

## File Structure

```
project-root/
  |-- program.md            # Human strategy document
  |-- prepare.py            # Frozen data pipeline (generated from template)
  |-- train.py              # Mutable experiment file (agent edits this)
  |-- input.csv             # Raw dataset (immutable)
  |-- results.tsv           # Experiment log (untracked by git)
  |-- run.log               # Last experiment output (untracked by git)
  |-- .gitignore            # Ignores results.tsv, run.log, __pycache__, etc.
  |-- pyproject.toml        # Dependencies: scikit-learn, xgboost, lightgbm, pandas, numpy
  |-- CLAUDE.md             # Claude Code instructions (points to program.md, defines loop)
```

**CLAUDE.md** is the "meta-orchestrator" -- it tells Claude Code how to operate:
- Read program.md for domain context
- Read train.py for current state
- Read results.tsv for experiment history
- Follow the multi-draft + linear improvement loop
- Never modify prepare.py
- Never stop unless interrupted

This is where the autoresearch `program.md` pattern meets Claude Code's native `CLAUDE.md` convention.

---

## Template System

The framework needs templates to generate prepare.py and initial train.py for any given dataset. These are NOT the agent's workspace -- they are the scaffolding that creates the agent's workspace.

```
templates/
  |-- prepare.py.jinja       # Template for frozen pipeline
  |-- train.py.jinja          # Template for initial model file
  |-- program.md.jinja        # Template for strategy document
  |-- CLAUDE.md.jinja         # Template for Claude Code instructions
  |-- .gitignore.template     # Standard gitignore
  |-- pyproject.toml.template # Standard dependencies
```

**Generation flow:**
```
User provides: input.csv, target_column, metric, task_type (classification/regression)
                           |
                           v
              Framework reads CSV header, infers dtypes
                           |
                           v
              Renders prepare.py from template (frozen)
              Renders train.py baseline (mutable)
              Renders program.md with dataset context
              Renders CLAUDE.md with loop instructions
                           |
                           v
              git init, git add, git commit "initial setup"
              git checkout -b automl/<tag>
                           |
                           v
              Claude Code starts autonomous loop
```

---

## Build Order (Dependencies)

The following build order reflects component dependencies. Each layer requires the prior layer to function.

### Layer 1: Core Pipeline (no dependencies)
1. **prepare.py template** -- data loading, splitting, evaluation function
2. **train.py template** -- baseline model (e.g., default XGBoost)
3. **.gitignore, pyproject.toml** -- standard project scaffolding

These are pure Python files with no framework code. They can be tested immediately with `uv run train.py`.

### Layer 2: Orchestration Instructions (depends on Layer 1)
4. **CLAUDE.md template** -- the experiment loop instructions for Claude Code
5. **program.md template** -- structured format for domain expertise

These define HOW Claude Code operates on the Layer 1 files. They are markdown documents, not code.

### Layer 3: Project Scaffolding CLI (depends on Layers 1-2)
6. **Initialization script** -- takes CSV + config, renders templates, initializes git
7. **Dataset analysis** -- infer column types, detect class imbalance, suggest metric

This is the only "real code" in the framework -- a CLI that sets up a new experiment project. After setup, the CLI is no longer needed; Claude Code takes over.

### Layer 4: Multi-Draft Logic (depends on Layers 1-3)
8. **Draft generation** -- logic to create 3-5 diverse initial train.py variants
9. **Draft evaluation** -- run each, parse metrics, select best
10. **Draft-to-linear transition** -- set up git state for linear improvement from best draft

This can be encoded in CLAUDE.md instructions (telling Claude Code how to do multi-draft) OR as a helper script. Encoding it in CLAUDE.md keeps the framework simpler.

### Layer 5: Enhancements (depends on Layers 1-4, build in any order)
11. **Results analysis** -- summary statistics, best/worst experiments, convergence plots
12. **v2 templates** -- prepare.py and train.py for feature engineering scope
13. **v3 templates** -- prepare.py and train.py for full pipeline scope
14. **Benchmark harness** -- run framework against known datasets, compare to baselines

---

## Scalability Considerations

| Concern | At 10 experiments | At 100 experiments | At 1000 experiments |
|---------|-------------------|--------------------|--------------------|
| **results.tsv size** | Trivial (10 rows) | Fine (100 rows, agent can read all) | May need agent to read only last N rows + best result |
| **Git history** | Trivial | Fine (100 commits on branch) | Git handles this well, but agent should not read full log |
| **Context window** | No pressure | Agent reads program.md + train.py + recent results = fine | Agent needs selective reading: current train.py + best result + last 10 results |
| **Experiment time** | Minutes | ~1 hour (at 30s/experiment) | ~8 hours (overnight run) |
| **Idea exhaustion** | Not an issue | Agent may start repeating | Agent needs "NEVER STOP" + explicit encouragement to try radical ideas |

**Key scaling insight from autoresearch:** At 100+ experiments, the agent's main risk is running out of ideas and making tiny, meaningless changes. The program.md should include "if stuck, try X" suggestions to keep the agent productive during long runs.

---

## Sources

- Autoresearch source code: `/tmp/autoresearch/program.md`, `prepare.py`, `train.py` (HIGH confidence -- direct reading)
- Research report: `Autonomous_ML_Agents_Research_Report.docx` (HIGH confidence -- comprehensive landscape analysis)
- AIDE architecture: Inferred from research report + training data knowledge of WecoAI/aideml (MEDIUM confidence)
- SELA architecture: Inferred from research report + arXiv:2410.17238 description (MEDIUM confidence)
- Staged mutable zones design: Original synthesis from research findings (HIGH confidence -- well-supported by evidence)
