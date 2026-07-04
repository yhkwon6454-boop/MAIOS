# Changelog

All notable changes for MAIOS are tracked here.

## v0.1.0-alpha

### Added

- MAIOS core facade with `maios.run(goal)` and `MAIOSCore.run(goal)`.
- Mission models, planner, scheduler, runtime runner, and quality kernel.
- GPT adapter with provider architecture and offline mock provider.
- OpenAI, Claude, and Gemini provider classes that read configuration from the
  environment.
- Tool adapter layer with `BaseTool`, `ToolRegistry`, `ShellTool`, `FileTool`,
  `PythonTool`, and `GitTool`.
- Reasoning engine for model-directed tool routing.
- JSON-backed `KnowledgeStore`, retrieval package, chunker, document model,
  retriever, embedding-provider interface, and vector-store interface.
- Memory kernel with short-term memory, conversation history, long-term
  retrieval, and memory context injection.
- Runtime integration and multi-agent orchestration.
- Autonomous planning, runtime scheduling, autonomous controller, and decision
  history persistence.
- Reflection engine and improvement reports stored in the knowledge store.
- FastAPI REST service and simple HTML/CSS/JavaScript dashboard.
- Plugin manager with dynamic loading from a plugin directory.
- Distributed runtime with node management, task dispatch, health monitoring,
  heartbeat checks, and load balancing.
- Cognitive mesh with memory and knowledge synchronization, collaborative
  planning, and deterministic consensus.
- Governance layer with permission model, policy engine, risk classification,
  approval gates, and audit log.
- Examples for core usage, runtime integration, API, dashboard, plugins,
  distributed runtime, cognitive mesh, autonomous controller, and governance.
- GitHub Actions CI and pytest coverage for implemented behavior.

### Notes

- MAIOS is an alpha-quality developer runtime.
- Concrete vector database backends and production network transports are not
  included.
- Local shell, file, Python, and Git tools should only be enabled in trusted
  environments.
