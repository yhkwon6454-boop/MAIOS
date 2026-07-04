# Contributing to MAIOS

Thank you for contributing to MAIOS. This project is currently in v0.1 Alpha, so
the most valuable contributions are small, well-tested changes that preserve
existing public APIs.

## Development Setup

```bash
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest
```

## Running Tests

```bash
pytest
```

All tests must pass before a change is merged.

## Contribution Guidelines

- Keep changes focused.
- Preserve existing public APIs unless a breaking change is explicitly accepted.
- Add or update tests for behavioral changes.
- Prefer dependency injection over hard-coded provider construction.
- Keep provider-specific code behind adapter or interface boundaries.
- Do not add network-dependent tests to the default test suite.
- Do not document unimplemented features as available.

## Code Style

The current codebase uses straightforward Python with dataclasses, protocols,
and small classes. Follow the existing style:

- Keep abstractions small.
- Prefer explicit names.
- Avoid unnecessary framework dependencies.
- Keep tests readable and deterministic.

## Pull Request Checklist

- Tests pass with `pytest`.
- New behavior is covered by tests.
- Documentation is updated if public behavior changes.
- No secrets, tokens, or generated private data are committed.
