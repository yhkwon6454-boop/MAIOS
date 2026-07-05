# Changelog

All notable changes to MAIOS are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows semantic versioning for release tags.

## [Unreleased]

## [1.0.0-rc1] - 2026-07-05

### Added

- Release candidate version metadata for MAIOS v1.0.
- `VERSION` file containing `1.0.0-rc1`.
- `maios --version` CLI command.
- Version command tests.

### Changed

- Package metadata now targets the MAIOS v1.0 release candidate.
- Changelog now follows Keep a Changelog structure.

## [1.0.0 Preparation] - 2026-07-05

### Added

- Release plan, security documentation, contribution guide, governance
  documentation, and release tag instructions.
- GitHub issue templates and pull request template.
- Black, Ruff, mypy, pytest-cov, pre-commit, and GitHub Actions quality gates.
- `py.typed` marker for typed package consumers.
- Stabilization coverage tests enforcing more than 95% package coverage.

### Changed

- Python package quality configuration moved into `pyproject.toml`.
- CI now runs formatting, linting, static analysis, and pytest.
- Codebase formatted with Black.
- Type hints and static-analysis compatibility improved across runtime modules.

### Fixed

- Replaced deprecated UTC timestamp usage in runtime packets.
- Preserved compatibility exports for GPT adapter provider classes.

## [0.1.0-alpha] - 2026-07-04

### Added

- `maios.run(goal)` and `MAIOSCore.run(goal)` public APIs.
- Mission models, planner, scheduler, runtime runner, and quality kernel.
- GPT adapter with provider architecture and offline mock provider.
- OpenAI, Claude, and Gemini provider classes.
- Tool adapter layer with shell, file, Python, and Git tools.
- Reasoning engine for model-directed tool routing.
- JSON-backed `KnowledgeStore`.
- Retrieval package with document, chunker, embedding-provider interface,
  vector-store interface, and retriever.
- Memory kernel with short-term memory, long-term retrieval, conversation
  history, and memory context injection.
- Reflection engine and improvement reports.
- Runtime integration and multi-agent orchestration.
- Autonomous planning, autonomous runtime queue, and autonomous controller.
- Safety and governance layer with policy checks, risk classification, approval
  gates, and audit logging.
- FastAPI REST service and web dashboard.
- Plugin manager and dynamic plugin loading.
- Distributed runtime with node management, dispatch, heartbeat checks, health
  monitoring, and load balancing.
- Cognitive mesh with memory synchronization, knowledge synchronization,
  collaborative planning, and consensus.
- Examples and tests covering implemented behavior.

### Security

- Local tool execution is powerful and should only be enabled in trusted
  environments.
- Provider credentials are read from environment-based configuration.
