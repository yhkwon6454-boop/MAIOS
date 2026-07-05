# MAIOS v1.0.0

MAIOS v1.0.0 is the first stable release of the MUSA AI Operating System local
runtime.

## Highlights

- Core `maios.run(goal)` and `MAIOSCore` public APIs.
- Multi-agent runtime orchestration.
- Memory, retrieval, knowledge store, and reflection loops.
- Provider-based LLM adapter architecture.
- Local tool adapter layer.
- Autonomous controller and autonomous mission queue.
- Safety and governance layer with audit logging.
- Distributed runtime and cognitive mesh abstractions.
- Plugin architecture.
- FastAPI REST service and web dashboard.
- Black, Ruff, mypy, pytest, and coverage quality gates.

## Quality

- `black --check src tests examples`
- `ruff check src tests examples`
- `mypy src`
- `pytest`
- Coverage threshold: 95%

## Installation

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

## Version Check

```bash
maios --version
```

Expected output:

```text
1.0.0
```

## Security Notes

MAIOS includes local tools that can execute shell commands, Python code, Git
commands, and file operations. Enable tools, plugins, and autonomous execution
only in trusted environments with appropriate governance policies.

## Tag

Release tag: `v1.0.0`
