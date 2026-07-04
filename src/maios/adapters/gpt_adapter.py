from __future__ import annotations

from typing import Any, Protocol

from maios.config import MAIOSConfig, load_config
from maios.runtime.models import CognitivePacket


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class OpenAIGPTClient:
    """OpenAI Responses API client used by GPTAdapter."""

    def __init__(
        self,
        config: MAIOSConfig | None = None,
        openai_client: Any | None = None,
        model: str | None = None,
    ) -> None:
        self.config = config or load_config()
        self.model = model or self.config.openai_model

        if openai_client is not None:
            self.openai_client = openai_client
            return

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI SDK is required for OpenAIGPTClient. "
                "Install project dependencies before using the GPT adapter."
            ) from exc

        api_key = self.config.openai_api_key or None
        self.openai_client = OpenAI(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self.openai_client.responses.create(
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


class GPTAdapter:
    """Adapter that executes MAIOS cognitive packets through a GPT client."""

    def __init__(
        self,
        client: LLMClient | None = None,
        config: MAIOSConfig | None = None,
        model: str | None = None,
    ) -> None:
        self.client = client or OpenAIGPTClient(config=config, model=model)

    def execute(
        self,
        packet: CognitivePacket,
        memory_context: dict[str, str],
    ) -> str:
        prompt = self._build_prompt(packet, memory_context)
        return self.client.generate(prompt)

    def _build_prompt(
        self,
        packet: CognitivePacket,
        memory_context: dict[str, str],
    ) -> str:
        memory = "\n".join(
            f"- {key}: {value}" for key, value in memory_context.items()
        )

        return f"""
[MAIOS Cognitive Packet]

Instruction:
{packet.instruction}

Strategies:
{", ".join(packet.strategy)}

Memory:
{memory}

Output format:
{packet.output_format}

Generate the best possible response while preserving the requested reasoning strategy.
""".strip()
