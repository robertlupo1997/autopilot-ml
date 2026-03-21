# Phase 3: CLI and Integration - Research

**Researched:** 2026-03-10
**Domain:** CLI scaffolding, project generation, end-to-end integration testing
**Confidence:** HIGH

## Summary

Phase 3 is the final v1 phase: a CLI command that takes a CSV path, target column, metric, and goal description, then scaffolds a complete standalone experiment directory. The scaffolded project contains prepare.py (copied from the automl package), train.py (generated from template), program.md (rendered with dataset info), CLAUDE.md (static loop protocol), .gitignore, and pyproject.toml -- all immediately runnable with `uv run train.py`.

The architecture is straightforward: the CLI is the thin entry point, but the heavy lifting is a `scaffold` module that composes existing Phase 1/2 modules (prepare.py source, train_template.py content, templates/render_program_md, templates/render_claude_md). The generated experiment directory is fully standalone -- it does NOT depend on the automl package at runtime. prepare.py is literally copied into the experiment directory so that train.py can do `from prepare import ...` as a sibling import.

**Primary recommendation:** Use `argparse` (stdlib) for the CLI -- zero new dependencies, the command is simple (4 positional/flag arguments), and the project already avoids unnecessary external deps. Build a `scaffold.py` module that orchestrates file generation, then expose it via `[project.scripts]` entry point in pyproject.toml. The end-to-end test runs the full pipeline: scaffold -> run train.py -> verify metric output -> run a few loop iterations on a real CSV.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLI-01 | CLI command scaffolds a new experiment project from a CSV file | `scaffold.py` module creates directory, copies prepare.py, generates all files; CLI entry point calls scaffold |
| CLI-02 | CLI accepts: data path, target column, metric name, goal description | argparse with positional `data_path`, `target_column`, `metric` and optional `--goal` flag |
| CLI-03 | CLI generates: prepare.py, train.py, program.md, CLAUDE.md, .gitignore, pyproject.toml | scaffold module uses shutil.copy for prepare.py, template rendering for train.py/program.md, static copy for CLAUDE.md, string generation for .gitignore and pyproject.toml |
| CLI-04 | Generated project is immediately runnable with `uv run train.py` | Generated pyproject.toml includes scikit-learn, pandas, numpy, xgboost, lightgbm as dependencies; prepare.py is a standalone copy |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| argparse (stdlib) | - | CLI argument parsing | Zero dependencies; project explicitly avoids unnecessary external deps; command is simple (4 args) |
| shutil (stdlib) | - | Copy prepare.py source file into experiment dir | Standard library for file/directory operations |
| pathlib (stdlib) | - | Path manipulation for scaffold output | Modern path handling, already used in prepare.py |
| inspect (stdlib) | - | Get source file path of prepare.py module | Reliable way to locate installed module source |
| textwrap (stdlib) | - | Dedent multi-line strings for generated files | Clean pyproject.toml and .gitignore generation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| automl.templates | - | render_program_md(), render_claude_md() | Already built in Phase 2; reuse for scaffold |
| automl.train_template | - | Train template source content | Already built in Phase 1; read and customize for scaffold |
| automl.prepare | - | Source file to copy into experiment dir | Phase 1 frozen pipeline; copied verbatim |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| argparse | Click/Typer | Click/Typer add external dependencies for minimal benefit; this CLI has exactly one command with 4 arguments |
| shutil.copy for prepare.py | importlib.resources | importlib.resources is the "correct" way but shutil.copy from `inspect.getfile()` is simpler and more obvious |
| String generation for pyproject.toml | toml/tomllib | Write-only; tomllib (stdlib 3.11+) only reads; toml package is write-capable but overkill for a static template |

**Installation:**
```bash
# No new dependencies needed -- everything is stdlib or already in the project
```

## Architecture Patterns

### Recommended Module Structure
```
src/automl/
    __init__.py
    cli.py               # NEW: argparse entry point, calls scaffold()
    scaffold.py           # NEW: orchestrates experiment directory creation
    prepare.py            # Phase 1 (source file gets COPIED into experiment dirs)
    train_template.py     # Phase 1 (content used to generate train.py)
    runner.py             # Phase 1
    git_ops.py            # Phase 1
    experiment_logger.py  # Phase 1
    loop_helpers.py       # Phase 2
    drafts.py             # Phase 2
    templates/
        __init__.py       # Phase 2 (render_program_md, render_claude_md)
        program.md.tmpl   # Phase 2
        claude.md.tmpl    # Phase 2
```

### Pattern 1: Scaffold Module (Core Pattern)
**What:** A single `scaffold_experiment()` function that creates a complete standalone experiment directory.
**When to use:** Called by the CLI entry point; also testable independently.
**Example:**
```python
# scaffold.py
"""Scaffold a new standalone experiment project from a CSV file."""

from __future__ import annotations

import inspect
import os
import shutil
import textwrap
from pathlib import Path

from automl import prepare as prepare_module
from automl.templates import render_program_md, render_claude_md
from automl.prepare import load_data, build_preprocessor, get_baselines, get_data_summary, validate_metric


def scaffold_experiment(
    data_path: str,
    target_column: str,
    metric: str,
    goal: str = "",
    output_dir: str | None = None,
    time_budget: int = 60,
) -> Path:
    """Create a fully runnable experiment directory.

    Parameters
    ----------
    data_path : str
        Path to the CSV file.
    target_column : str
        Name of the target column.
    metric : str
        User-facing metric name (e.g., "auc", "rmse").
    goal : str
        Human-readable goal description.
    output_dir : str or None
        Directory to create. Defaults to ./experiment-<dataset_stem>.
    time_budget : int
        Per-experiment time budget in seconds.

    Returns
    -------
    Path
        The created experiment directory.
    """
    # 1. Validate inputs early
    csv_path = Path(data_path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    X, y, task = load_data(str(csv_path), target_column)
    sklearn_metric, direction = validate_metric(metric, task)

    # 2. Create output directory
    if output_dir is None:
        output_dir = f"experiment-{csv_path.stem}"
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=False)  # Fail if exists

    # 3. Copy prepare.py (the frozen pipeline)
    prepare_source = inspect.getfile(prepare_module)
    shutil.copy2(prepare_source, out / "prepare.py")

    # 4. Generate train.py from template
    _write_train_py(out, csv_path.name, target_column, metric, time_budget)

    # 5. Copy CSV into experiment dir (or symlink)
    shutil.copy2(csv_path, out / csv_path.name)

    # 6. Render program.md with data summary and baselines
    preprocessor = build_preprocessor(X)
    X_processed = preprocessor.transform(X)
    baselines = get_baselines(X_processed, y, sklearn_metric, task)
    summary = get_data_summary(X, y, task)
    program_md = render_program_md(
        dataset_name=csv_path.stem,
        goal_description=goal or f"Optimize {metric} for {target_column} prediction",
        metric_name=metric,
        direction=direction,
        data_summary=_format_summary(summary),
        baselines=_format_baselines(baselines),
    )
    (out / "program.md").write_text(program_md)

    # 7. Copy CLAUDE.md (static)
    claude_md = render_claude_md()
    (out / "CLAUDE.md").write_text(claude_md)

    # 8. Generate .gitignore
    (out / ".gitignore").write_text(_gitignore_content())

    # 9. Generate pyproject.toml
    (out / "pyproject.toml").write_text(
        _pyproject_content(csv_path.stem)
    )

    return out
```

### Pattern 2: CLI Entry Point (Thin Wrapper)
**What:** argparse-based CLI that parses arguments and calls scaffold_experiment().
**When to use:** Exposed via `[project.scripts]` in pyproject.toml.
**Example:**
```python
# cli.py
"""CLI entry point for AutoML experiment scaffolding."""

import argparse
import sys

from automl.scaffold import scaffold_experiment


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and scaffold an experiment project."""
    parser = argparse.ArgumentParser(
        prog="automl",
        description="Scaffold an autonomous ML experiment from a CSV file.",
    )
    parser.add_argument("data_path", help="Path to the CSV file")
    parser.add_argument("target_column", help="Name of the target column")
    parser.add_argument("metric", help="Evaluation metric (auc, rmse, f1, accuracy, ...)")
    parser.add_argument("--goal", default="", help="Human-readable goal description")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: experiment-<dataset>)")
    parser.add_argument("--time-budget", type=int, default=60, help="Per-experiment time budget in seconds")

    args = parser.parse_args(argv)

    try:
        out = scaffold_experiment(
            data_path=args.data_path,
            target_column=args.target_column,
            metric=args.metric,
            goal=args.goal,
            output_dir=args.output_dir,
            time_budget=args.time_budget,
        )
        print(f"Experiment scaffolded at: {out}")
        print(f"Next steps:")
        print(f"  cd {out}")
        print(f"  uv run train.py        # Run baseline experiment")
        print(f"  # Then start Claude Code and let the agent iterate")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
```

### Pattern 3: Generated pyproject.toml for Standalone Experiments
**What:** The scaffolded experiment directory needs its own pyproject.toml so `uv run train.py` resolves dependencies.
**When to use:** Every scaffolded project.
**Example:**
```python
def _pyproject_content(dataset_name: str) -> str:
    return textwrap.dedent(f"""\
        [project]
        name = "experiment-{dataset_name}"
        version = "0.1.0"
        description = "AutoML experiment"
        requires-python = ">=3.11"
        dependencies = [
            "scikit-learn>=1.5",
            "pandas>=2.0",
            "numpy>=2.0",
            "xgboost",
            "lightgbm",
        ]
    """)
```

### Pattern 4: Entry Point Registration
**What:** Register `automl` command via pyproject.toml `[project.scripts]`.
**When to use:** So users can run `automl data.csv target auc` from anywhere.
**Example (in the framework's pyproject.toml):**
```toml
[project.scripts]
automl = "automl.cli:main"
```

### Anti-Patterns to Avoid
- **Making the experiment dir depend on the automl package:** The experiment directory must be standalone. prepare.py is COPIED, not imported from the package. This is a locked decision from Phase 1: `[01-03]: train_template.py uses sibling imports`.
- **Using Jinja2 for template rendering:** Already decided against in Phase 2. String.format() and simple replacement are sufficient.
- **Generating train.py with hardcoded absolute paths:** train.py should reference `data.csv` (the local copy) not `/abs/path/to/original.csv`. The CSV is copied into the experiment dir.
- **Forgetting to copy the CSV:** The experiment dir must be self-contained. The CSV must be in the experiment directory alongside prepare.py and train.py.
- **Using `uv run python train.py` in generated CLAUDE.md:** The CLAUDE.md template already has the correct command. No changes needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI argument parsing | Custom sys.argv parser | argparse (stdlib) | Handles help text, type validation, error messages automatically |
| File copying | Manual open/read/write | shutil.copy2 | Preserves metadata, handles edge cases |
| Module source location | Hardcoded paths | inspect.getfile(module) | Works regardless of install method (editable, wheel, etc.) |
| Data summary formatting | Custom print logic | Reuse prepare.get_data_summary() | Already implemented and tested in Phase 1 |
| Template rendering | Custom template engine | Reuse automl.templates.render_*() | Already implemented and tested in Phase 2 |
| Dependency specification | Inline script metadata | pyproject.toml in experiment dir | Standard approach; uv resolves from pyproject.toml |

**Key insight:** Phase 3 is primarily COMPOSITION. Almost all the building blocks exist (prepare.py, train_template.py, templates, git_ops). The CLI just orchestrates calling them and writing files to a new directory.

## Common Pitfalls

### Pitfall 1: prepare.py Import Breaks When Copied
**What goes wrong:** prepare.py imports from sklearn/pandas which are not installed in the experiment's venv.
**Why it happens:** The experiment dir has its own pyproject.toml but dependencies haven't been resolved yet.
**How to avoid:** The generated pyproject.toml MUST list all of prepare.py's dependencies (scikit-learn, pandas, numpy). When the user runs `uv run train.py`, uv automatically creates a venv and installs dependencies from pyproject.toml.
**Warning signs:** `ModuleNotFoundError: No module named 'sklearn'` on first `uv run train.py`.

### Pitfall 2: train.py Template Has Wrong Config Values
**What goes wrong:** The generated train.py still has placeholder values like `CSV_PATH = "data.csv"` pointing to wrong filename, or wrong metric/target.
**Why it happens:** The template substitution didn't replace all configuration variables.
**How to avoid:** The train_template.py has clearly marked config section at the top (CSV_PATH, TARGET_COLUMN, METRIC, TIME_BUDGET). The scaffold must read the template content as a string and replace these values before writing.
**Warning signs:** `KeyError: 'target'` because the column name doesn't match.

### Pitfall 3: Experiment Directory Already Exists
**What goes wrong:** scaffold_experiment overwrites an existing experiment directory, destroying previous results.
**Why it happens:** No existence check before creating the directory.
**How to avoid:** Use `mkdir(exist_ok=False)` so it raises FileExistsError. Let the user explicitly choose a different name with `--output-dir`.
**Warning signs:** Silent data loss.

### Pitfall 4: CSV Path Resolution
**What goes wrong:** User passes a relative path like `../data/file.csv` and the copy fails or copies to wrong location.
**Why it happens:** Path resolution is tricky when CWD changes.
**How to avoid:** Resolve the CSV path to absolute with `Path(data_path).resolve()` BEFORE creating the experiment directory. Copy using the resolved absolute path.
**Warning signs:** FileNotFoundError during scaffold, or empty/wrong CSV in experiment dir.

### Pitfall 5: Missing Build System in Generated pyproject.toml
**What goes wrong:** `uv run train.py` fails because the generated pyproject.toml lacks a `[build-system]` section.
**Why it happens:** uv may require a build system for project mode.
**How to avoid:** The generated pyproject.toml should be minimal but valid. For `uv run script.py`, having just `[project]` with dependencies should be sufficient since uv treats scripts differently from packages. Test this explicitly.
**Warning signs:** uv errors about missing build backend.

### Pitfall 6: train.py Config Replacement Breaks Code
**What goes wrong:** String replacement in train_template.py content accidentally replaces something other than the config variables.
**Why it happens:** Using naive string replace on Python source code.
**How to avoid:** The config section in train_template.py has exact patterns: `CSV_PATH = "data.csv"`, `TARGET_COLUMN = "target"`, etc. Use line-by-line replacement or regex targeting these exact assignment patterns.
**Warning signs:** SyntaxError when running the generated train.py.

## Code Examples

### Complete Scaffold Flow
```python
# What scaffold_experiment does, step by step:

# 1. Validate the CSV and metric
csv_path = Path(data_path).resolve()
X, y, task = load_data(str(csv_path), target_column)
sklearn_metric, direction = validate_metric(metric, task)

# 2. Create the output directory
out = Path(output_dir)
out.mkdir(parents=True, exist_ok=False)

# 3. Copy prepare.py (frozen pipeline source)
import inspect
from automl import prepare as prepare_module
shutil.copy2(inspect.getfile(prepare_module), out / "prepare.py")

# 4. Generate train.py with correct config values
template = Path(inspect.getfile(train_template_module)).read_text()
# Replace config values in the template
content = template.replace('CSV_PATH = "data.csv"', f'CSV_PATH = "{csv_path.name}"')
content = content.replace('TARGET_COLUMN = "target"', f'TARGET_COLUMN = "{target_column}"')
content = content.replace('METRIC = "accuracy"', f'METRIC = "{metric}"')
content = content.replace(f'TIME_BUDGET = 60', f'TIME_BUDGET = {time_budget}')
(out / "train.py").write_text(content)

# 5. Copy CSV
shutil.copy2(csv_path, out / csv_path.name)

# 6-9. Render program.md, CLAUDE.md, .gitignore, pyproject.toml
# (see Pattern 1 above)
```

### Generated .gitignore Content
```python
def _gitignore_content() -> str:
    return textwrap.dedent("""\
        results.tsv
        run.log
        __pycache__/
        *.pyc
        .venv/
    """)
```

### Data Summary Formatting for program.md
```python
def _format_summary(summary: dict) -> str:
    """Format get_data_summary() output for program.md."""
    lines = [
        f"- **Shape:** {summary['shape'][0]} rows x {summary['shape'][1]} columns",
        f"- **Missing values:** {summary['missing']}",
        f"- **Column types:** {summary['dtypes']}",
    ]
    dist = summary["target_distribution"]
    if isinstance(dist, dict) and "mean" in dist:
        lines.append(f"- **Target (regression):** mean={dist['mean']:.4f}, std={dist['std']:.4f}, range=[{dist['min']:.4f}, {dist['max']:.4f}]")
    else:
        lines.append(f"- **Target classes:** {dist}")
    return "\n".join(lines)


def _format_baselines(baselines: dict) -> str:
    """Format get_baselines() output for program.md."""
    lines = []
    for name, scores in baselines.items():
        lines.append(f"- **{name}:** {scores['score']:.6f} (+/- {scores['std']:.6f})")
    return "\n".join(lines)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Click/Typer for all CLIs | argparse for simple CLIs, Click/Typer for complex | Always true | No external dependency for a 4-argument command |
| cookiecutter for project scaffolding | Direct file generation for small templates | Project decision | cookiecutter is overkill for 6 files with simple substitution |
| pip install + requirements.txt | uv + pyproject.toml | 2024-2025 | uv handles venv creation, dependency resolution, and script execution in one tool |

## Open Questions

1. **Should the CSV be copied or symlinked?**
   - What we know: The experiment dir must be standalone and self-contained.
   - What's unclear: Large CSVs (100MB+) waste disk space when copied. Symlinks break if the original moves.
   - Recommendation: COPY for v1. Simplicity and portability trump disk savings. Large dataset handling is a v2 concern.

2. **Should scaffold run prepare.py to pre-populate data summary in program.md?**
   - What we know: program.md has data_summary and baselines placeholders. render_program_md() accepts these as strings.
   - What's unclear: Running prepare.py during scaffold adds latency (CV for baselines takes seconds). But it provides better program.md content.
   - Recommendation: YES, run the pipeline during scaffold. The user waits once during setup (a few seconds), and gets a fully populated program.md. The data summary and baselines are computed using the existing prepare.py functions (load_data, build_preprocessor, get_baselines, get_data_summary).

3. **Entry point name: `automl` vs `automl-init` vs `automl scaffold`?**
   - What we know: The CLI has exactly one command (scaffold). No subcommands needed for v1.
   - What's unclear: If we use `automl`, it conflicts with any existing `automl` on PyPI.
   - Recommendation: Use `automl` as the entry point name. It's the project name, it's clear, and PyPI conflicts don't matter since this is a local tool. The command reads naturally: `automl data.csv target_col auc`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already installed in dev deps) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-01 | CLI scaffolds experiment project from CSV | integration | `uv run pytest tests/test_scaffold.py::test_scaffold_creates_all_files -x` | No -- Wave 0 |
| CLI-02 | CLI accepts data_path, target_column, metric, goal | unit | `uv run pytest tests/test_cli.py::test_cli_argument_parsing -x` | No -- Wave 0 |
| CLI-03 | Generates prepare.py, train.py, program.md, CLAUDE.md, .gitignore, pyproject.toml | integration | `uv run pytest tests/test_scaffold.py::test_scaffold_file_contents -x` | No -- Wave 0 |
| CLI-04 | Generated project is runnable with `uv run train.py` | integration | `uv run pytest tests/test_scaffold.py::test_scaffolded_project_runs -x` | No -- Wave 0 |

### End-to-End Test (Success Criterion 3)
| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| CLI scaffold + loop runs on real dataset + improves beyond baseline | e2e | `uv run pytest tests/test_e2e.py::test_scaffold_and_loop -x` | No -- Wave 0 |

Note: The e2e test is complex -- it requires Claude Code to actually run the loop. For automated testing, a simplified version tests: scaffold -> run train.py -> verify metric output -> verify structured output format. The "improves beyond baseline" criterion requires running multiple iterations which is better verified manually or in a longer integration test.

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_scaffold.py` -- covers CLI-01, CLI-03, CLI-04 (scaffold function, file generation, runnable output)
- [ ] `tests/test_cli.py` -- covers CLI-02 (argument parsing, error handling)
- [ ] `tests/test_e2e.py` -- covers end-to-end success criterion (scaffold + run + verify output)
- [ ] Test fixture: small CSV file for scaffold testing (can reuse from conftest.py if suitable)

## Sources

### Primary (HIGH confidence)
- Phase 1 source code (prepare.py, train_template.py, runner.py) -- all APIs verified by reading actual implementation
- Phase 2 source code (templates/__init__.py, program.md.tmpl, claude.md.tmpl, drafts.py, loop_helpers.py) -- all APIs verified
- Python argparse docs -- stdlib CLI parsing, well-documented and stable
- Python shutil docs -- stdlib file operations
- uv docs (https://docs.astral.sh/uv/guides/projects/) -- pyproject.toml and script execution

### Secondary (MEDIUM confidence)
- uv entry points behavior -- verified via multiple sources that `[project.scripts]` works with uv after install

### Tertiary (LOW confidence)
- None -- all findings derived from existing codebase and official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib, no new dependencies
- Architecture: HIGH -- composition of existing Phase 1/2 modules; patterns directly from codebase
- Pitfalls: HIGH -- identified from concrete code review (train_template config format, prepare.py dependencies)
- Integration: MEDIUM -- end-to-end test with uv may have edge cases around venv creation timing

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain, mature tools)
