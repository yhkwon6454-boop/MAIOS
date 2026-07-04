# Changelog

All notable changes for MAIOS v0.1 Alpha are summarized here.

## 0.1.0-alpha

### Added

- Mission runtime models and simple mission loading.
- Mission planner and mission scheduler.
- Cognitive, executive, memory, and quality kernels.
- Dummy model adapter.
- GPT adapter and OpenAI client wrapper.
- Generic tool interface, registry, and local tools.
- Reasoning engine with model-directed tool routing.
- Retrieval package with document, chunker, embedding provider interface, vector
  store interface, and retriever.
- Runtime integration pipeline.
- Example mission files and runtime integration example.
- Pytest suite covering unit and integration behavior.
- GitHub Actions CI workflow for push and pull request checks.

### Notes

- MAIOS v0.1 Alpha is an early developer release.
- Concrete vector database backends are not included.
- Multi-agent orchestration is not included.
- Tool execution is local and should be used only in trusted environments.
