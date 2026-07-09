import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import find_dotenv, load_dotenv


@dataclass
class MAIOSConfig:
    model_provider: str = field(
        default_factory=lambda: os.getenv(
            "MAIOS_MODEL_PROVIDER",
            os.getenv("MAIOS_MODEL", "mock"),
        )
    )
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-5"))
    claude_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    claude_model: str = field(
        default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
    )
    gemini_api_key: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    )
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-pro"))


def load_config(env_file: str | Path | None = None) -> MAIOSConfig:
    """Build the runtime config, loading a `.env` file first when present.

    Values already set in the process environment always win over `.env`.
    """
    if env_file is not None:
        load_dotenv(env_file, override=False)
    else:
        found = find_dotenv(usecwd=True)
        if found:
            load_dotenv(found, override=False)
    return MAIOSConfig()
