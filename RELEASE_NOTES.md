# MAIOS v1.3.0

MAIOS v1.3.0 connects the cognitive layer to real knowledge assets:
local documents become part of the knowledge graph, Korean text is now a
first-class citizen in search, and the whole pipeline was validated and
hardened against a real book corpus.

## Highlights

- Document ingestion: `maios ingest <path>` (and `/ingest` in the shell)
  reads markdown, text, and HTML files - including Korean cp949 files -
  into the knowledge graph. Ingested documents feed memory recall and are
  cited as research sources.
- Korean-aware search: Hangul bigram tokenization with IDF weighting.
  Previously Korean text was invisible to search.
- Real-corpus hardening: a 33-file book corpus ingests in under a second;
  repeat research queries stay stable instead of snowballing; stored
  records are compacted and capped.

```bash
maios ingest ~/books
maios research "드론 전쟁과 우크라이나 교훈"
maios shell
```

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
1.3.0
```

## Security Notes

MAIOS includes local tools that can execute shell commands, Python code, Git
commands, and file operations. Enable tools, plugins, autonomous execution,
and goal pursuit only in trusted environments with appropriate governance
policies. Ingested documents and workspace directories are stored in plain
files - treat them accordingly.

## Tag

Release tag: `v1.3.0`
