# MAIOS Design Principles

MAIOS v0.1 Alpha follows a small set of design principles visible in the current
implementation.

## 1. Provider-Agnostic Core

Core runtime logic should not depend directly on a specific model provider,
embedding provider, or vector database.

Implemented examples:

- `LLMClient`
- `ModelAdapter`
- `EmbeddingProvider`
- `VectorStore`

## 2. Dependency Injection

Components should accept collaborators through constructors where practical.

Implemented examples:

- `ReasoningEngine(model_adapter, tool_registry)`
- `Retriever(embedding_provider, vector_store, chunker)`
- `MemoryKernel(retriever)`
- `RuntimeRunner(...)`

## 3. Small Interfaces

Interfaces should expose the minimum behavior needed by the runtime.

Implemented examples:

- `BaseTool.execute(input_data)`
- `EmbeddingProvider.embed(text)`
- `VectorStore.add(...)` and `VectorStore.search(...)`

## 4. Testable Boundaries

External providers should be replaceable with fakes in tests. The implemented
test suite uses fake model clients, fake retrievers, fake tools, and fake vector
stores.

## 5. Incremental Runtime Integration

MAIOS favors incremental integration over large rewrites. New systems should
connect to existing components without removing established public APIs.

## 6. Explicit Results

Runtime components should return explicit result objects or dictionaries that
can be validated in tests.

Implemented examples:

- `ToolResult`
- `ReasoningResult`
- `QAResult`
- `ExecutionResult`
