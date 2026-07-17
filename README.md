# MAIOS

MAIOS is the MUSA AI Operating System: a Python runtime for mission-oriented AI
workflows. The `v1.0.0` release stabilized the local developer runtime that
connects planning, memory, model adapters, tool routing, multi-agent execution,
autonomous control, distributed coordination, and governance abstractions.
`v1.1.0` added a cognitive decision layer: an executive brain, a world model,
a phased cognitive loop, and a unified autonomous core with governance gating
and optional LLM-backed understanding and reflection. `v1.2.0` made that
layer a working tool: a persistent workspace with memory recall, real
LLM-backed task execution with artifacts, an interactive shell, project
decomposition, and research over accumulated knowledge. `v1.3.0` connects
it to real knowledge assets: local document ingestion (Korean included)
and Korean-aware IDF-weighted search, hardened against a real book corpus.

MAIOS is not a hosted service. Components are local Python abstractions designed
for extension and testing.

## Implemented Capabilities

- `maios.run(goal)` and `MAIOSCore.run(goal)` public APIs.
- Multi-agent runtime orchestration: planner, memory, LLM adapter, executor,
  quality, reflection, and knowledge update.
- Provider-based LLM adapter architecture with mock, OpenAI, Claude, and Gemini
  provider classes.
- JSON-backed `KnowledgeStore`, memory context injection, and keyword RAG.
- Tool adapter layer with shell, file, Python, and Git tools.
- Autonomous planning, autonomous runtime queue, and autonomous controller.
- Safety and governance layer with permission checks, risk classification,
  approval gates, and audit logging.
- Plugin manager for agents, tools, providers, and memory modules.
- Distributed runtime and cognitive mesh abstractions for multiple MAIOS nodes.
- FastAPI REST service and simple web dashboard.
- Executive brain, world model, and a cognitive loop
  (observe -> understand -> plan -> act -> reflect -> learn).
- Unified autonomous core (`AGIFoundation`) with goal pursuit,
  self-introspection, evolution reports, and governance gating. The class
  name describes the module's role in the architecture; it is an
  orchestration layer, not artificial general intelligence.
- Optional LLM-backed understanding and reflection with heuristic fallback.
- Persistent workspace (`.maios/`) with a goal-pursuit journal, project
  journal, artifacts, and memory recall feeding new goals.
- LLM task execution producing real deliverables, goal decomposition for
  multi-step projects, and research over the workspace's own knowledge.
- Interactive `maios shell` session.
- Document ingestion (`maios ingest`) for markdown, text, and HTML files,
  with Korean cp949 fallback and Hangul-aware IDF-weighted search.
- Optional ontology integration (unreleased, on `develop`): an RDFS/OWL
  adapter (`rdflib` extra) that expands memory recall with concept
  neighbors, raises governance risk for goals touching declared risk
  concepts (`governance.json`), and checks every goal against a
  commander's-intent specification (`intent.json`) with
  ALIGNED/CHECK/CONFLICT verdicts (`maios align`, shell `/align`).
- Local examples and a pytest suite covering implemented behavior.

## Installation

MAIOS targets Python 3.11 and 3.12.

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

On macOS or Linux, replace the Python executable path with
`.venv/bin/python`.

## Basic Usage

```python
import maios

result = maios.run("Summarize the current MAIOS runtime status.")
print(result.status)
print(result.final_output)
```

Run the included example:

```bash
python examples/basic_usage.py
```

## Goal Pursuit CLI

Run the full cognitive stack (governance gate, memory recall, cognitive
loop, artifacts) from one command:

```bash
maios ingest ~/books
maios pursue "Summarize the weekly report" --llm mock
maios project "Draft a three-part defense brief" --llm mock
maios research "What did we learn about drone swarms?"
maios introspect
maios shell
```

- `--capability NAME` requests capabilities (repeatable).
- `--max-cycles N` bounds retry cycles; `--max-subgoals N` bounds project
  decomposition.
- `--approve` grants human approval for high-risk goals.
- `--llm PROVIDER` enables LLM-backed understanding, execution, reflection,
  decomposition, and synthesis (`mock`, `openai`, `claude`, `gemini`; real
  providers need API keys, e.g. in a `.env` file).
- `--workspace DIR` selects the persistent workspace (default `.maios/`).

Every command prints `[memory]` stats; goals with generated output write
`artifacts/<id>.md` in the workspace. `maios ingest` accepts files or
directories (md, txt, html) and makes their content recallable and
researchable. `maios shell` keeps one session with `/ingest`, `/project`,
`/research`, `/align`, `/approve`, `/history`, `/introspect`, and `/evolve`.
See `examples/agi_foundation_demo.py` for the same flow as a script.

## REST API

```bash
uvicorn maios.service.api:app --reload
```

Implemented endpoints:

- `GET /health`
- `POST /run`
- `GET /mission/{mission_id}`
- `GET /history`
- `GET /dashboard`

## Tests

```bash
pytest
```

At release preparation time, the local suite passes with:

```text
478 passed, 95.94% coverage
```

## Documentation

- [User Manual (Korean)](docs/MANUAL.ko.md)
- [Research Paper Draft (Korean)](docs/PAPER.ko.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Installation](docs/INSTALLATION.md)
- [API](docs/API.md)
- [Roadmap](docs/ROADMAP.md)
- [Quality](docs/QUALITY.md)
- [Security](docs/SECURITY.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Governance](docs/GOVERNANCE.md)
- [Release Plan](docs/RELEASE_PLAN.md)
- [Changelog](CHANGELOG.md)

## Status

`v1.3.0` connects the cognitive tool to real knowledge assets with
document ingestion and Korean-aware search, validated against a real
book corpus. Public APIs remain intentionally small and are covered by
tests, with extension points designed for providers, tools, plugins,
governance policies, and distributed transports.
