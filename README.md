# MAIOS

MAIOS is the MUSA AI Operating System: a Python runtime for mission-oriented AI
workflows. The `v1.0.0` release stabilizes the local developer runtime that
connects planning, memory, model adapters, tool routing, multi-agent execution,
autonomous control, distributed coordination, and governance abstractions.

MAIOS is not a hosted service. Components are local Python abstractions designed
for extension and testing.

## Implemented Capabilities

- `maios.run(goal)` and `MAIOSCore.run(goal)` public APIs.
- Multi-agent runtime orchestration: planner, memory, LLM adapter, executor,
  quality, reflection, and knowledge update.
- Provider-based LLM adapter architecture with mock, OpenAI, Claude, and Gemini
  provider classes.
- JSON-backed `KnowledgeStore`, memory context injection, and keyword RAG.
- Tool adapter layer with shell, file, Python, and Git tools.
- Autonomous planning, autonomous runtime queue, and autonomous controller.
- Safety and governance layer with permission checks, risk classification,
  approval gates, and audit logging.
- Plugin manager for agents, tools, providers, and memory modules.
- Distributed runtime and cognitive mesh abstractions for multiple MAIOS nodes.
- FastAPI REST service and simple web dashboard.
- Local examples and a pytest suite covering implemented behavior.

## Installation

MAIOS targets Python 3.11 and 3.12.

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

On macOS or Linux, replace the Python executable path with
`.venv/bin/python`.

## Basic Usage

```python
import maios

result = maios.run("Summarize the current MAIOS runtime status.")
print(result.status)
print(result.final_output)
```

Run the included example:

```bash
python examples/basic_usage.py
```

## REST API

```bash
uvicorn maios.service.api:app --reload
```

Implemented endpoints:

- `GET /health`
- `POST /run`
- `GET /mission/{mission_id}`
- `GET /history`
- `GET /dashboard`

## Tests

```bash
pytest
```

At release preparation time, the local suite passes with:

```text
156 passed, 95.20% coverage
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Installation](docs/INSTALLATION.md)
- [API](docs/API.md)
- [Roadmap](docs/ROADMAP.md)
- [Quality](docs/QUALITY.md)
- [Security](docs/SECURITY.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Governance](docs/GOVERNANCE.md)
- [Release Plan](docs/RELEASE_PLAN.md)
- [Changelog](CHANGELOG.md)

## Status

`v1.0.0` is the first stable MAIOS release. Public APIs remain intentionally
small and are covered by tests, with extension points designed for providers,
tools, plugins, governance policies, and distributed transports.
