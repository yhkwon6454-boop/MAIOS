from dataclasses import dataclass, field
import os


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
    claude_model: str = field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5"))
    gemini_api_key: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    )
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-pro"))


def load_config() -> MAIOSConfig:
    return MAIOSConfig()
