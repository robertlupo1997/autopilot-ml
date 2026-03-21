# Contributing to mlforge

Thanks for your interest in contributing to mlforge. This guide covers everything you need to get started.

## Getting Started

1. Fork the repo at [github.com/robertlupo1997/autopilot-ml](https://github.com/robertlupo1997/autopilot-ml).
2. Clone your fork and install dependencies:

```bash
git clone https://github.com/<your-username>/autopilot-ml.git
cd autopilot-ml
uv sync
```

3. Verify the test suite passes:

```bash
uv run pytest -x -q
```

You should see 617+ tests pass. If anything fails on a fresh clone, open an issue.

## Development Workflow

- Create a feature branch from `main`.
- Write tests for every new feature or bug fix.
- Run the full test suite before submitting your PR.
- Keep pull requests focused: one feature or fix per PR.
- Write a clear PR description explaining what changed and why.

## Code Style

- **Python 3.11+** features are welcome (match statements, `X | Y` type unions, `tomllib`, etc.).
- No linter is enforced yet, but keep your code clean and consistent with the surrounding style.
- **Type hints** are encouraged on all function signatures.
- **Docstrings** are expected on public functions and classes.

## Architecture Overview

mlforge is organized around a plugin-based engine that orchestrates autonomous ML experiments.

| Layer | Location | Purpose |
|-------|----------|---------|
| Engine | `engine.py` | Orchestrates the experiment loop (scaffold, run, evaluate, iterate) |
| Plugins | `plugins.py` | Define domain-specific behavior (tabular, deep learning, fine-tuning) |
| Templates | `templates/` | Render CLAUDE.md protocol files and train.py scaffolds via Jinja2 |
| Intelligence | `intelligence/` | Diagnostics, multi-draft exploration, stagnation detection |
| CLI | `cli.py` | Entry point and argument parsing |

To add a new domain, implement the `DomainPlugin` protocol and register it in `scaffold.py`. The engine handles the rest.

## Testing

```bash
uv run pytest -x -q              # All tests
uv run pytest tests/mlforge/ -q  # mlforge package tests only
uv run pytest -k "test_cli" -q   # Specific test pattern
```

All new code must include tests. If you are fixing a bug, add a regression test that fails without your fix.

## What We Are Looking For

- **Bug fixes** with reproduction steps and regression tests.
- **New domain plugins** that extend mlforge to new ML problem types.
- **Improved diagnostics** in the intelligence layer.
- **Better protocol templates** that help Claude produce stronger experiments.
- **Documentation improvements** of any kind.

## Reporting Issues

Use [GitHub Issues](https://github.com/robertlupo1997/autopilot-ml/issues). Please include:

- What you expected to happen.
- What actually happened.
- Steps to reproduce the problem.
- Your mlforge version (`git rev-parse --short HEAD`).
- Python version and operating system.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
