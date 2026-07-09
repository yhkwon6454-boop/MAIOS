from __future__ import annotations

from typing import Protocol

from maios.adapters.llm_provider import (
    BaseLLMProvider,
    ClaudeProvider,
    GeminiProvider,
    MockGPTClient,
    OpenAIProvider,
    create_llm_provider,
)
from maios.config import MAIOSConfig
from maios.kernel.memory_kernel import MemoryKernel
from maios.runtime.models import CognitivePacket

__all__ = [
    "ClaudeProvider",
    "GPTAdapter",
    "GeminiProvider",
    "LLMClient",
    "MockGPTClient",
    "OpenAIGPTClient",
    "OpenAIProvider",
]


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str: ...


class OpenAIGPTClient(OpenAIProvider):
    def __init__(
        self,
        config: MAIOSConfig | None = None,
        openai_client=None,
        model: str | None = None,
    ) -> None:
        super().__init__(config=config, client=openai_client, model=model)


class GPTAdapter:
    """Adapter that executes MAIOS cognitive packets through an LLM provider."""

    def __init__(
        self,
        client: LLMClient | None = None,
        config: MAIOSConfig | None = None,
        model: str | None = None,
        memory_kernel: MemoryKernel | None = None,
    ) -> None:
        self.initialized = False
        self.client = client or self._default_client(config=config, model=model)
        self.memory_kernel = memory_kernel

    def initialize(self):
        self.initialized = True
        return True

    def generate(self, prompt: str, memory_context: dict[str, str] | None = None) -> str:
        if not self.initialized:
            self.initialize()

        final_prompt = self._inject_memory(prompt, memory_context)
        return self.client.generate(final_prompt)

    def validate(self, result):
        return isinstance(result, str) and bool(result.strip())

    def shutdown(self):
        self.initialized = False
        return True

    def execute(
        self,
        packet: CognitivePacket,
        memory_context: dict[str, str],
    ) -> str:
        prompt = self._build_prompt(packet, memory_context)
        return self.generate(prompt, memory_context=memory_context)

    def _inject_memory(
        self,
        prompt: str,
        memory_context: dict[str, str] | None = None,
    ) -> str:
        if self.memory_kernel is None:
            return prompt

        return self.memory_kernel.inject_context(
            prompt,
            memory_context=memory_context,
        )

    def _default_client(
        self,
        config: MAIOSConfig | None = None,
        model: str | None = None,
    ) -> BaseLLMProvider:
        return create_llm_provider(config=config, model=model)

    def _build_prompt(
        self,
        packet: CognitivePacket,
        memory_context: dict[str, str],
    ) -> str:
        memory = "\n".join(f"- {key}: {value}" for key, value in memory_context.items())

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
