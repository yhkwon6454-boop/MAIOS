# MAIOS Roadmap

This roadmap describes practical next steps based on the implemented v0.1 Alpha
codebase. It does not claim these features are already available.

## v0.1 Alpha: Current Foundation

Implemented:

- Mission models, loader, planner, scheduler, and runtime runner.
- Dummy and GPT model adapter abstractions.
- Reasoning engine with JSON-based tool routing.
- Tool registry and local shell/file/Python/Git tools.
- Retrieval primitives and memory integration.
- Quality evaluation.
- Unit and integration tests.
- GitHub Actions CI workflow.

## Near-Term Priorities

1. Stabilize public runtime interfaces.
2. Add stricter type coverage for kernel and runtime result objects.
3. Add concrete retrieval backends for local development.
4. Add tool safety controls before autonomous execution.
5. Expand end-to-end mission examples.
6. Improve documentation for extension points.

## Medium-Term Direction

- Formalize agent-level abstractions.
- Add persistent memory namespaces.
- Add policy and audit logging around tool execution.
- Add richer quality evaluation.
- Add structured traces for reasoning and tool calls.

## Long-Term Direction

- Multi-agent orchestration.
- Agent role specialization.
- Human approval gates.
- Persistent mission history.
- Provider-specific adapters behind stable interfaces.
