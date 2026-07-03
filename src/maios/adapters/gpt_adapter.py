from __future__ import annotations

from typing import Protocol
from maios.runtime.models import CognitivePacket


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class GPTAdapter:
    """
    GPT 계열 모델 어댑터.

    실제 OpenAI SDK 연동 시에는 client.generate(...) 부분을
    Responses API 호출로 교체하면 된다.
    """

    def __init__(self, client: LLMClient):
        self.client = client

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
            f"- {k}: {v}" for k, v in memory_context.items()
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
