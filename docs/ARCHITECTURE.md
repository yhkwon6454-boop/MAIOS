# MAIOS Architecture

MAIOS is organized as small Python packages connected through dependency
injection. The current architecture favors testable local abstractions over
production infrastructure.

## Cognitive Layer (v1.1+)

Goal pursuit runs through a phased cognitive loop on top of the runtime:

```text
User goal (maios pursue / project / research / shell)
  -> Workspace (.maios/: knowledge graph, memory store, journals, artifacts)
  -> AGIFoundation (governance gate, goal registry, evolution reports)
  -> CognitiveLoop: Observe -> Understand -> Plan -> Act -> Reflect -> Learn
       Observe    world model refresh from runtime state
       Understand world context + MemoryRecall over the knowledge graph
                  (+ optional LLM interpretation)
       Plan       ExecutiveBrain decision and planner selection
       Act        TaskExecutor (LLM deliverable), research engine,
                  or distributed/swarm/meta planners
       Reflect    ImprovementReport (optional LLM reflection)
       Learn      world transition, lessons, experience nodes
  -> GoalPursuit / ProjectPursuit records + artifacts/<id>.md
```

Key components in `maios.kernel`: `AGIFoundation`, `CognitiveLoop`,
`ExecutiveBrain`, `WorldModel`, `MemoryRecall`, `TaskExecutor`,
`CognitiveInterpreter`, `GoalDecomposer`, `DocumentIngestor`, and
`Workspace`. Every LLM-backed step degrades to a deterministic heuristic
when no provider is configured, so the whole loop is offline-testable.
Knowledge search is Hangul-aware TF-IDF over the knowledge graph.

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
- `maios.kernel`: memory, context, cognitive, executive, and quality kernels,
  plus the cognitive layer (foundation, loop, world model, recall, executor,
  interpreter, decomposer, ingestor, workspace).
- `maios.knowledge`: JSON-backed knowledge store and the persistent
  knowledge graph with Hangul-aware TF-IDF search.
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

- The v1.0 runtime is synchronous unless using the autonomous background agent.
- Distributed and mesh transports are local abstractions in this release.
- Tool execution is local and should be treated as trusted-code functionality.
