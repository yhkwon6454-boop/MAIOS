# MAIOS Architecture

This document describes the implemented MAIOS v0.1 Alpha architecture.

## Overview

MAIOS currently consists of a single-process Python runtime that connects
mission planning, cognitive scheduling, memory, model adapters, tool routing,
reasoning, and quality evaluation.

The primary integration point is `RuntimeRunner`.

```text
Mission file
  -> load_mission
  -> MissionPlanner
  -> ExecutiveKernel
  -> MissionScheduler
  -> CognitivePacket list
  -> MemoryKernel context retrieval
  -> ReasoningEngine
  -> ModelAdapter
  -> ToolRegistry when requested
  -> QualityKernel
  -> output files
```

## Core Packages

### `maios.runtime`

Defines runtime models and execution flow:

- `Mission`, `CognitiveProcess`, `CognitivePacket`, `QAResult`,
  `ExecutionResult`
- `load_mission`
- `CognitiveProcessTree`
- `RuntimeRunner`

### `maios.planner`

Provides `MissionPlanner`, which converts an objective string into a simple
mission plan with intent, tasks, priority, and risk.

### `maios.scheduler`

Provides `MissionScheduler`, which creates a `CognitiveProcessTree` for mission
types currently represented in the code:

- `MILITARY_RESEARCH`
- `WRITING`
- `TRANSLATION`
- `GENERAL`

### `maios.kernel`

Provides kernel-level components:

- `CognitiveKernel`
- `ExecutiveKernel`
- `MemoryKernel`
- `QualityKernel`
- `BaseKernel`

These components are intentionally lightweight in v0.1 Alpha.

### `maios.adapters`

Provides model adapter implementations:

- `DummyModelAdapter` for deterministic local execution.
- `GPTAdapter` for cognitive-packet prompt construction.
- `OpenAIGPTClient` wrapper around the OpenAI Responses API.

### `maios.reasoning`

Provides `ReasoningEngine`, which supports an iterative loop:

```text
Reasoning -> Tool -> Observation -> Final Answer
```

The engine accepts any model adapter that implements:

```python
execute(packet, memory_context) -> str
```

Tool calls are selected from JSON model responses.

### `maios.tools`

Provides a generic tool system:

- `BaseTool`
- `ToolResult`
- `ToolRegistry`
- `ShellTool`
- `FileTool`
- `PythonTool`
- `GitTool`

### `maios.retrieval`

Provides provider-agnostic retrieval primitives:

- `Document`
- `Chunker`
- `EmbeddingProvider`
- `VectorStore`
- `Retriever`

No concrete vector database backend is implemented in v0.1 Alpha.

## Dependency Direction

The newer components use dependency injection where practical:

- `ReasoningEngine` receives a model adapter and `ToolRegistry`.
- `Retriever` receives an `EmbeddingProvider`, `VectorStore`, and optional
  `Chunker`.
- `MemoryKernel` can receive an injected `Retriever`.
- `RuntimeRunner` can receive injected planner, memory, adapter, reasoning
  engine, tool registry, executive kernel, quality kernel, and scheduler.

## Persistence

Runtime outputs are saved as Markdown and JSON files. Long-term retrieval
interfaces exist, but persistent vector storage is not implemented.

## Limitations

- Tool execution is local and should be treated as trusted-code functionality.
- Multi-agent orchestration is not implemented.
- Persistent memory backends are not implemented.
- The runtime is synchronous.
