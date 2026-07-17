# Installation

MAIOS `v1.3.0` targets Python 3.11 and 3.12.

## Local Development

```bash
git clone https://github.com/yhkwon6454-boop/MAIOS.git
cd MAIOS
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

On macOS or Linux:

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .[dev]
```

## Optional Provider Credentials

Offline tests use the mock provider and do not require API keys.

Provider classes read credentials from environment-based configuration. Set only
the keys for providers you intend to use.

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
```

## Verify Installation

```bash
pytest
python examples/basic_usage.py
```

## Run the API

```bash
uvicorn maios.service.api:app --reload
```

Open `http://127.0.0.1:8000/dashboard` for the built-in dashboard.
