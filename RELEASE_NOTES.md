# MAIOS v1.1.0

MAIOS v1.1.0 adds a cognitive decision layer on top of the v1.0.0 local
runtime: executive decision making, a world model, a phased cognitive loop,
and a unified autonomous core with governance gating and optional LLM-backed
understanding and reflection.

## Highlights

- Executive Brain: goal prioritization, planner selection, runtime control,
  and failure-driven learning escalation.
- World Model: environment, user, and system state with transitions,
  predictions, and world-context building for decisions.
- Cognitive Loop: Observe -> Understand -> Plan -> Act -> Reflect -> Learn
  as one repeatable cycle across the executive and learning layers.
- `AGIFoundation`: single entry point for goal pursuit, self-introspection,
  and evolution reports. Despite the class name, this is an orchestration
  layer for autonomous workflows, not artificial general intelligence.
- Governance gating on goal pursuit: blocked keywords and risk-based human
  approval before any cycle executes.
- Cognitive Interpreter: optional LLM-backed Understand and Reflect phases
  via the existing mock, OpenAI, Claude, and Gemini providers, with heuristic
  fallback when no provider is available.
- New CLI commands:

```bash
maios pursue "Summarize the weekly report" [--capability NAME] [--max-cycles N] [--approve] [--llm PROVIDER]
maios introspect [--llm PROVIDER]
```

- End-to-end demo: `examples/agi_foundation_demo.py`.

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
1.1.0
```

## Security Notes

MAIOS includes local tools that can execute shell commands, Python code, Git
commands, and file operations. Enable tools, plugins, autonomous execution,
and goal pursuit only in trusted environments with appropriate governance
policies.

## Tag

Release tag: `v1.1.0`
