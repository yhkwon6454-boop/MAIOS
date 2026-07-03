from dataclasses import dataclass
import os


@dataclass
class MAIOSConfig:
    model_provider: str = os.getenv("MAIOS_MODEL", "mock")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5")


def load_config() -> MAIOSConfig:
    return MAIOSConfig()