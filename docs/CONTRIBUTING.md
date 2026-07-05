# Contributing

MAIOS accepts focused, well-tested changes that preserve existing public APIs.

## Development Setup

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

On macOS or Linux, use `.venv/bin/python`.

## Quality Gate

Run the same checks used by CI:

```bash
black --check src tests examples
ruff check src tests examples
mypy
pytest
```

Coverage must remain above 95%.

## Pre-Commit

```bash
pre-commit install
```

The configured hooks run Black, Ruff, and mypy.

## Guidelines

- Keep changes focused and reviewable.
- Preserve public APIs unless a breaking change is explicitly accepted.
- Use dependency injection for providers, tools, stores, transports, and policy
  managers.
- Keep tests offline and deterministic.
- Update documentation for public behavior changes.
- Do not document unimplemented features as available.
- Do not commit secrets or local generated outputs.

## Pull Request Expectations

- Explain the change and why it is needed.
- Link related issues when applicable.
- Include tests for changed behavior.
- Confirm the full quality gate passes.
