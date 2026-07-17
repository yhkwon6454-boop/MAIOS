# Changelog

All notable changes to MAIOS are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows semantic versioning for release tags.

## [Unreleased]

Real-LLM validation of this batch (`scripts/validate_live.py` against a live
provider) is pending an Anthropic billing issue; the cognitive-layer and
ontology work below is complete on `develop` but held back from a version
tag until that validation runs. See the project's release-plan notes for
detail. Everything remains usable today via `--llm mock` or a working
provider key.

### Added

**Search and validation**

- Term-frequency weighting in knowledge search: documents that discuss a
  query term repeatedly outrank ones that mention it once, fixing score
  saturation ties on long documents.
- `scripts/validate_live.py`: one-command end-to-end validation of the
  cognitive stack against a real LLM provider (provider connectivity,
  pursuit deliverable, ingestion + recall, research, project decomposition).
- Architecture docs now describe the cognitive layer (v1.1+).

**Ontology integration (J1/J2/J4)**

- Ontology-expanded recall: drop an RDFS/OWL `ontology.ttl` into the
  workspace (optional `rdflib` dependency) and queries expand along
  subclass, instance, and domain/range relations, so documents that share
  no surface tokens with the query are still recalled. Unavailable
  ontologies degrade silently to plain search.
- Ontology-driven governance: `governance.json` in the workspace lists
  ontology concepts whose neighborhood escalates matching objectives to
  HIGH risk, requiring human approval before execution.
- Commander's-intent alignment: specify intent (purpose, end state, key
  tasks, constraints, acceptable risks) in `intent.json` and every pursued
  goal is judged ALIGNED/CHECK/CONFLICT before execution; conflicts with
  constraints escalate to human approval. New `maios align` command and
  shell `/align`, ontology-widened matching included. J3 (automatic
  ontology-instance extraction from ingested text) remains unimplemented —
  it needs real LLM calls, so it's blocked on the same billing issue.

**Documentation**

- Korean user manual (`docs/MANUAL.ko.md`, mirrored as `docs/MANUAL.ko.html`)
  covering every command, workspace structure, governance, workflows, and
  troubleshooting.
- Research paper draft (`docs/PAPER.ko.md`, mirrored as `docs/PAPER.ko.html`
  with 7 illustrated figures) documenting the design principles,
  architecture, the real-corpus case study, and the ontology application
  study (section 7).
- Development-narrative book (`docs/BOOK_NARRATIVE.ko.md` /
  `docs/BOOK_NARRATIVE.ko.html`): a first-person essay on building MAIOS,
  covering the mission-command origins, the three real-corpus scale
  defects, the ontology-integration honesty caveats, and the Stripe/Link
  payment lockout that has stalled real-LLM validation.
- Print-ready book compilation (`docs/MAIOS_책_v1.docx`, built by
  `scripts/build_book.py`) combining the manual and paper with figures.
- Korean deliverables inventory (`docs/산출물목록.ko.md`).

### Fixed

- Paper overclaiming toned down after a red-team pass: section 6's
  real-corpus case study now explicitly states it's a single-corpus study
  (N=1) with a private, undisclosed corpus; section 7.2 now discloses that
  the demonstrated "포병⊑화력지원" relation was added to a synthetic
  control ontology for the experiment rather than present in schema v1;
  section 7 now explains why an excerpt (66 of ~180 triples) of the
  mission-command ontology was used instead of the full schema (duplicate
  Korean labels caused adapter shadowing).
- `docs/PAPER.ko.html` figure 6's arrow marker referenced figure 3's shared
  `<defs>` instead of defining its own — worked by DOM-order accident but
  broke if figures were reordered or excerpted.

## [1.3.0] - 2026-07-10

### Added

- Document ingestion: `maios ingest` and the shell `/ingest` command read
  local markdown, text, and HTML files into the knowledge graph as
  document nodes - split on headings or paragraphs, HTML tags stripped,
  cp949 fallback for Korean files, deterministic node ids so re-ingesting
  updates instead of duplicating. Ingested documents are recalled during
  cognition and cited as research sources.
- Korean-aware search: tokenization emits Hangul character bigrams, and
  semantic scores weight terms by inverse document frequency with cached
  per-node token sets. Previously Korean text was invisible to search.
- `KnowledgeGraph.bulk()` context manager for mass inserts and an
  `auto_link` flag on `add_node`.

### Fixed

- Real-corpus scaling failures: bulk ingest no longer persists per node or
  auto-links quadratically; outcomes are compacted before being stored in
  world transitions, experiences, and long-term memory, stopping records
  from re-ingesting themselves and snowballing; research source collection
  prefers documents over the system's own activity records; node content
  is capped; `semantic_search` no longer scores every node twice.

## [1.2.0] - 2026-07-09

### Added

- Persistent workspace (`.maios/` by default): knowledge graph, long-term
  memory store, goal-pursuit journal, and project journal survive across
  runs and are restored on startup. CLI gains `--workspace`.
- LLM task executor: the Act phase performs the objective (summary, draft,
  translation) instead of echoing it; deliverables are recorded on the
  pursuit and written to `artifacts/<id>.md`, with echo fallback.
- Interactive shell: `maios shell` runs a persistent session where every
  line becomes a goal, with `/project`, `/research`, `/approve`,
  `/history`, `/introspect`, and `/evolve` commands.
- Memory recall: the Understand phase searches the knowledge graph for
  relevant experiences, reflections, concepts, and evidence; recalled
  entries and lessons from previous pursuits flow into the understanding
  and execution prompts.
- Goal decomposition: `maios project` breaks a large objective into
  sequential sub-goals, chains each sub-goal's output into the next, and
  synthesizes one final deliverable.
- Research integration: workspace foundations wire a `ResearchEngine`
  backed by a `KnowledgeGraphSourceCollector`, so `maios research` and
  research-capability goals investigate accumulated knowledge and emit
  report artifacts.

### Fixed

- `load_config` now actually loads `.env` files (python-dotenv was declared
  but never called), and `.env.example` is a real environment template.
  The original Korean vision statement moved to `docs/VISION.ko.md`.

## [1.1.0] - 2026-07-09

### Added

- Executive Brain: top-level decision engine with goal prioritization,
  planner selection, runtime control, and learning escalation.
- World Model: environment, user, and system state with state transitions,
  outcome prediction, and world-context building for executive decisions.
- Cognitive Loop: Observe -> Understand -> Plan -> Act -> Reflect -> Learn
  cycle wiring the executive, world model, reflection, and learning layers.
- AGI Foundation: unified autonomous core (`AGIFoundation`) with goal pursuit,
  self-introspection (`SelfModel`), evolution reports, and governance gating
  (blocked keywords, risk-based human approval).
- Cognitive Interpreter: optional LLM-backed understanding and reflection
  using the existing provider adapters, with heuristic fallback when no
  provider is configured or a provider call fails.
- CLI commands: `maios pursue <objective>` (with `--capability`,
  `--max-cycles`, `--approve`, `--llm`) and `maios introspect [--llm]`.
- End-to-end example `examples/agi_foundation_demo.py`.

### Changed

- `ExecutiveBrain.decide` reuses a world context already built during the
  Understand phase instead of rebuilding it.
- `ExecutiveBrain` exposes public `act` and `learn` methods used by the
  cognitive loop phases.

## [1.0.0] - 2026-07-05

### Added

- `RELEASE_NOTES.md` for the final v1.0.0 release.
- GitHub release workflow for `v*` tags.
- Final release tag instructions for `v1.0.0`.

### Changed

- Promoted package version from `1.0.0-rc1` to `1.0.0`.
- Updated package, CLI, API metadata, README, and docs for the final release.

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
