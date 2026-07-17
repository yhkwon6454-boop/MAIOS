# Quality

MAIOS uses a local quality gate for stabilization.

## Checks

```bash
black --check src tests examples
ruff check src tests examples
mypy
pytest
```

Pytest runs package coverage (branch coverage enabled, CLI entry module
omitted) and fails below 95%.

## Pre-Commit

Install hooks with:

```bash
pre-commit install
```

The pre-commit configuration runs Black, Ruff, and mypy.

## CI

GitHub Actions runs formatting, linting, static analysis, and tests on Python
3.11 and 3.12.
