from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from maios.config import MAIOSConfig, load_config


class BaseLLMProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass


class MockGPTClient(BaseLLMProvider):
    """Offline mock provider used by tests and local development."""

    name = "mock"

    def generate(self, prompt: str) -> str:
        return f"Mock GPT response: {prompt}"


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def __init__(
        self,
        config: MAIOSConfig | None = None,
        client: Any | None = None,
        model: str | None = None,
    ) -> None:
        self.config = config or load_config()
        self.model = model or self.config.openai_model

        self.client = client

    def _ensure_client(self):
        if self.client is not None:
            return
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI SDK is required for OpenAIProvider.") from exc

        api_key = self.config.openai_api_key or None
        self.client = OpenAI(api_key=api_key)

    def generate(self, prompt: str) -> str:
        self._ensure_client()
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        return self._extract_text(response)

    def _extract_text(self, response: Any) -> str:
        output_text = self._get_value(response, "output_text")
        if output_text:
            return str(output_text)

        output = self._get_value(response, "output") or []
        for item in output:
            content = self._get_value(item, "content") or []
            for part in content:
                text = self._get_value(part, "text")
                if text:
                    return str(text)

        return str(response)

    def _get_value(self, source: Any, key: str) -> Any:
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)


class ClaudeProvider(BaseLLMProvider):
    name = "claude"

    def __init__(
        self,
        config: MAIOSConfig | None = None,
        client: Any | None = None,
        model: str | None = None,
    ) -> None:
        self.config = config or load_config()
        self.model = model or self.config.claude_model

        self.client = client

    def _ensure_client(self):
        if self.client is not None:
            return
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError("Anthropic SDK is required for ClaudeProvider.") from exc

        self.client = anthropic.Anthropic(api_key=self.config.claude_api_key or None)

    def generate(self, prompt: str) -> str:
        self._ensure_client()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._extract_text(response)

    def _extract_text(self, response: Any) -> str:
        content = getattr(response, "content", None)
        if content is None and isinstance(response, dict):
            content = response.get("content")

        if isinstance(content, list):
            parts = []
            for item in content:
                text = item.get("text") if isinstance(item, dict) else getattr(item, "text", "")
                if text:
                    parts.append(str(text))
            if parts:
                return "\n".join(parts)

        return str(response)


class GeminiProvider(BaseLLMProvider):
    name = "gemini"

    def __init__(
        self,
        config: MAIOSConfig | None = None,
        client: Any | None = None,
        model: str | None = None,
    ) -> None:
        self.config = config or load_config()
        self.model = model or self.config.gemini_model

        self.client = client

    def _ensure_client(self):
        if self.client is not None:
            return
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("Google Gen AI SDK is required for GeminiProvider.") from exc

        self.client = genai.Client(api_key=self.config.gemini_api_key or None)

    def generate(self, prompt: str) -> str:
        self._ensure_client()
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        text = getattr(response, "text", None)
        if text:
            return str(text)

        if isinstance(response, dict) and response.get("text"):
            return str(response["text"])

        return str(response)


def create_llm_provider(
    config: MAIOSConfig | None = None,
    model: str | None = None,
) -> BaseLLMProvider:
    config = config or load_config()
    provider = config.model_provider.lower()

    if provider in {"mock", "offline", "dummy"}:
        return MockGPTClient()
    if provider in {"openai", "gpt"}:
        return OpenAIProvider(config=config, model=model)
    if provider in {"claude", "anthropic"}:
        return ClaudeProvider(config=config, model=model)
    if provider in {"gemini", "google"}:
        return GeminiProvider(config=config, model=model)

    raise ValueError(f"Unsupported LLM provider: {config.model_provider}")
