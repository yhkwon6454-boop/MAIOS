from __future__ import annotations

from typing import Any

from maios.adapters.llm_provider import BaseLLMProvider
from maios.kernel.world_model import WorldContext


class CognitiveInterpreter:
    """LLM-backed interpretation for the Understand and Reflect phases.

    Falls back to ``None`` whenever no provider is configured or the provider
    fails, so callers keep their heuristic behavior without an LLM.
    """

    def __init__(self, provider: BaseLLMProvider | None = None) -> None:
        self.provider = provider

    @property
    def available(self) -> bool:
        return self.provider is not None

    def interpret_situation(
        self,
        objective: str,
        world_context: WorldContext,
        recalled: tuple[str, ...] | list[str] = (),
    ) -> str | None:
        provider = self.provider
        if provider is None:
            return None
        predictions = ", ".join(
            f"{prediction.target}={prediction.outcome}" for prediction in world_context.predictions
        )
        memory_block = ""
        if recalled:
            memory_block = (
                "Relevant memories:\n" + "\n".join(f"- {entry}" for entry in recalled) + "\n"
            )
        prompt = (
            "You are the situational-understanding layer of an AI operating system.\n"
            f"Objective: {objective}\n"
            f"Environment risk: {world_context.environment.risk_level}\n"
            f"System state: healthy_nodes={world_context.system.healthy_nodes}, "
            f"active_agents={world_context.system.active_agents}, "
            f"failure_rate={world_context.system.failure_rate}\n"
            f"Predictions: {predictions or 'none'}\n"
            + memory_block
            + "In at most two sentences, assess the situation and name the main risk, "
            "using the memories when they are relevant."
        )
        return self._generate(provider, prompt)

    def reflect_on_outcome(
        self,
        objective: str,
        outcome: dict[str, Any],
        success: bool,
        interpretation: str | None = None,
    ) -> tuple[str, tuple[str, ...]] | None:
        provider = self.provider
        if provider is None:
            return None
        prompt = (
            "You are the reflection layer of an AI operating system.\n"
            f"Objective: {objective}\n"
            f"Outcome: {outcome}\n"
            f"Success: {success}\n"
            + (f"Earlier situation assessment: {interpretation}\n" if interpretation else "")
            + "First write a one-sentence assessment of this cycle. "
            "Then list concrete lessons as bullet lines starting with '- '."
        )
        text = self._generate(provider, prompt)
        if text is None:
            return None
        summary, lessons = self._parse_reflection(text)
        if not summary:
            return None
        return summary, lessons

    @staticmethod
    def _generate(provider: BaseLLMProvider, prompt: str) -> str | None:
        try:
            text = provider.generate(prompt).strip()
        except Exception:
            return None
        return text or None

    @staticmethod
    def _parse_reflection(text: str) -> tuple[str, tuple[str, ...]]:
        summary_lines: list[str] = []
        lessons: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(("- ", "* ")):
                lessons.append(stripped[2:].strip())
            elif not lessons:
                summary_lines.append(stripped)
        return " ".join(summary_lines), tuple(lesson for lesson in lessons if lesson)
