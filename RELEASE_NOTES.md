# MAIOS v1.2.0

MAIOS v1.2.0 turns the v1.1.0 cognitive layer into a working tool: memory
that persists and is actually recalled, an Act phase that produces real
deliverables, an interactive shell, project decomposition, and research
over accumulated knowledge.

## Highlights

- Persistent workspace (`.maios/`): knowledge graph, long-term memory,
  pursuit and project journals, and artifacts survive across runs.
- Memory recall: each new goal retrieves relevant experiences, reflections,
  concepts, and evidence from earlier work and feeds them into the
  understanding and execution prompts, together with accumulated lessons.
- Real execution: with an LLM provider, the Act phase performs the
  objective and writes the deliverable to `artifacts/<id>.md`.
- Interactive shell:

```bash
maios shell
maios> Summarize the weekly report
maios> /project Draft a three-part defense brief
maios> /research What did we learn about drone swarms?
maios> /evolve
```

- Goal decomposition: `maios project <objective>` splits a large objective
  into sequential sub-goals, chains their outputs, and synthesizes one
  final deliverable.
- Research over memory: `maios research <question>` runs the research
  engine against the workspace's own knowledge graph and emits a report
  artifact that becomes a source for future research.
- `.env` files now load correctly, and `.env.example` is a real template.

## Quality

- `black --check src tests examples`
- `ruff check src tests examples`
- `mypy src`
- `pytest`
- Coverage threshold: 95%

## Installation

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

## Version Check

```bash
maios --version
```

Expected output:

```text
1.2.0
```

## Security Notes

MAIOS includes local tools that can execute shell commands, Python code, Git
commands, and file operations. Enable tools, plugins, autonomous execution,
and goal pursuit only in trusted environments with appropriate governance
policies. Workspace directories store everything the system reads and
produces in plain files - treat them accordingly.

## Tag

Release tag: `v1.2.0`
