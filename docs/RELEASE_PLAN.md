# MAIOS v1.0.0 Release Plan

This document is the release checklist for MAIOS v1.0.0.

## Release Scope

MAIOS v1.0.0 includes the implemented local runtime foundation:

- Core `maios.run(goal)` and `MAIOSCore` APIs.
- Multi-agent runtime orchestration.
- Memory, retrieval, knowledge store, and reflection.
- Provider-based LLM adapter architecture.
- Tool registry and local tool adapters.
- Autonomous controller.
- Safety and governance layer.
- Distributed runtime and cognitive mesh abstractions.
- FastAPI service and web dashboard.
- Plugin architecture.

## Release Checklist

- [x] Confirm `pyproject.toml` version is set to `1.0.0`.
- [x] Confirm `src/maios/__init__.py` exposes `__version__ = "1.0.0"`.
- [x] Confirm `VERSION` contains `1.0.0`.
- [x] Run `black --check src tests examples`.
- [x] Run `ruff check src tests examples`.
- [x] Run `mypy src`.
- [x] Run `pytest`.
- [x] Confirm test coverage remains above 95%.
- [x] Review `README.md` and `docs/` for version accuracy.
- [ ] Review `LICENSE` and copyright owner.
- [ ] Confirm no secrets, generated private outputs, or local artifacts are staged.
- [x] Confirm GitHub issue templates and pull request template are present.
- [x] Confirm GitHub release workflow is present.
- [ ] Create and push the `v1.0.0` tag.
- [ ] Create the GitHub release from the tag.

## LICENSE Review Note

The repository currently uses the MIT License. Before tagging `v1.0.0`, the
maintainer should confirm:

- The copyright holder is correct.
- Third-party dependencies are compatible with MIT distribution.
- Generated files, private documents, credentials, and local runtime outputs are
  excluded from the release.

## Release Tag Instructions

After all checks pass on `develop`:

```bash
git status
git log --oneline -5
git tag -a v1.0.0 -m "MAIOS v1.0.0"
git push origin develop
git push origin v1.0.0
```

Pushing the `v1.0.0` tag runs the GitHub release workflow. The workflow runs
the quality gate and creates the GitHub release from `RELEASE_NOTES.md`.

## Release Notes Draft

MAIOS v1.0.0 stabilizes the local AI operating-system runtime with core mission
execution, multi-agent orchestration, memory and retrieval, provider-based LLM
adapters, tools, autonomous control, governance, distributed runtime
abstractions, plugin loading, API service, dashboard, and quality gates.

Quality baseline:

- Black formatting.
- Ruff linting.
- mypy static analysis.
- Pytest suite with coverage threshold above 95%.
