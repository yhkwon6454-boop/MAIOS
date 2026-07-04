# MAIOS

MAIOS is an experimental AI operating-system runtime for mission-oriented work.
The v0.1 Alpha codebase provides a small, test-covered Python foundation for
planning missions, scheduling cognitive packets, routing model output through
tools, using retrieval-backed memory, and producing runtime outputs.

This release is intentionally minimal. It implements local abstractions and
offline-testable components; it does not provide a production autonomous agent
or hosted service.

## Implemented Capabilities

- Mission loading from simple YAML or JSON files.
- Mission planning through `MissionPlanner`.
- Cognitive process scheduling for writing, translation, military research, and
  general missions.
- Runtime execution through `RuntimeRunner`.
- Model adapter abstraction with a dummy adapter and an OpenAI Responses API
  client wrapper.
- Reasoning loop support for model-directed tool calls.
- Tool registry with shell, file, Python, and Git tools.
- Short-term memory and provider-agnostic long-term retrieval interfaces.
- Chunking, document, embedding-provider, vector-store, and retriever
  abstractions.
- Quality evaluation for runtime packet outputs.
- Pytest test suite and GitHub Actions CI workflow.

## Installation

MAIOS requires Python 3.12 according to the package metadata.

```bash
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest
```

The CI workflow also tests Python 3.11 for compatibility.

## Running Tests

```bash
pytest
```

At the time this documentation was generated, the local suite passed with:

```text
46 passed, 2 warnings
```

## Running an Example Mission

```bash
python -m maios.cli examples/writing_project.yaml
```

Or run the integration example:

```bash
python examples/runtime_integration.py
```

Runtime outputs are written under `outputs/` by default.

## Repository Layout

```text
src/maios/adapters/    Model adapter implementations
src/maios/kernel/      Cognitive, executive, memory, and quality kernels
src/maios/planner/     Mission planning
src/maios/reasoning/   Iterative reasoning engine
src/maios/retrieval/   RAG interfaces and retrieval primitives
src/maios/runtime/     Mission models, loading, tree, and runner
src/maios/scheduler/   Mission-to-process scheduling
src/maios/tools/       Tool interface, registry, and local tools
tests/                 Unit and integration tests
examples/              Example mission files and runtime example
```

## Status

MAIOS v0.1 Alpha is a developer-oriented foundation. Public interfaces are still
small and may evolve, but existing tests are intended to protect current API
behavior during incremental development.
