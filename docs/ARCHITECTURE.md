# MAIOS Architecture

MAIOS is organized as small Python packages connected through dependency
injection. The current architecture favors testable local abstractions over
production infrastructure.

## Runtime Pipeline

```text
Goal
  -> MAIOSCore
  -> RuntimeOrchestrator
  -> PlannerAgent
  -> MemoryAgent / MemoryKernel
  -> GPTAdapter / provider
  -> ExecutorAgent
  -> QualityKernel
  -> ReflectionEngine
  -> KnowledgeStore
  -> MissionResult
```

## Core Packages

- `maios.core`: public `MAIOSCore`, `MissionResult`, and `run(goal)` API.
- `maios.agents`: planner, memory, executor, and runtime orchestrator.
- `maios.adapters`: GPT adapter and provider-based LLM integration.
- `maios.kernel`: memory, context, cognitive, executive, and quality kernels.
- `maios.knowledge`: JSON-backed knowledge store.
- `maios.retrieval`: document, chunker, retriever, embedding, and vector-store
  interfaces.
- `maios.reasoning`: iterative reasoning and tool routing.
- `maios.tools`: generic tool interface and local tool implementations.
- `maios.planning`: goal manager, task decomposer, and priority engine.
- `maios.reflection`: mission reflection and improvement reports.
- `maios.autonomous`: autonomous queue runtime and OODA-style controller.
- `maios.governance`: permissions, policies, risk classification, approvals,
  and audit logging.
- `maios.distributed`: node management, dispatch, heartbeat, and load
  balancing.
- `maios.mesh`: cognitive mesh synchronization, collaborative planning, and
  consensus.
- `maios.plugins`: dynamic plugin loading and component registration.
- `maios.service`: FastAPI service and dashboard routes.

## Extension Points

- LLM providers implement `BaseLLMProvider`.
- Tools implement `BaseTool`.
- Retrieval backends implement `EmbeddingProvider` and `VectorStore`.
- Plugins can register agents, tools, providers, and memory modules.
- Distributed and mesh transports are protocol-based and can be replaced.
- Governance policies can be added through `PolicyEngine` composition.

## Persistence

Implemented persistence is JSON-backed:

- `KnowledgeStore`
- autonomous decision history
- governance audit log
- autonomous mission history

## Constraints

- The alpha runtime is synchronous unless using the autonomous background agent.
- Distributed and mesh transports are local abstractions in this release.
- Tool execution is local and should be treated as trusted-code functionality.
