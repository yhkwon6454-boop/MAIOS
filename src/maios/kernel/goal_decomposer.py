from __future__ import annotations

from maios.adapters.llm_provider import BaseLLMProvider


class GoalDecomposer:
    """LLM-backed decomposition of a large objective into sequential sub-goals.

    Returns ``None`` when no provider is configured, the provider fails, or
    the objective is not worth decomposing, so callers fall back to pursuing
    the objective as a single goal.
    """

    def __init__(self, provider: BaseLLMProvider | None = None) -> None:
        self.provider = provider

    @property
    def available(self) -> bool:
        return self.provider is not None

    def decompose(self, objective: str, max_subgoals: int = 5) -> tuple[str, ...] | None:
        provider = self.provider
        if provider is None:
            return None
        limit = max(2, max_subgoals)
        prompt = (
            "You are the planning layer of an AI operating system. "
            f"Break the objective into at most {limit} sequential sub-goals, "
            "each independently executable and building on the previous ones. "
            "Output only the sub-goals, one per line, each starting with '- '.\n"
            f"Objective: {objective}"
        )
        try:
            text = provider.generate(prompt).strip()
        except Exception:
            return None
        subgoals = self._parse(text)[:limit]
        if len(subgoals) < 2:
            return None
        return tuple(subgoals)

    def synthesize(
        self,
        objective: str,
        results: list[tuple[str, str]] | tuple[tuple[str, str], ...],
    ) -> str | None:
        provider = self.provider
        if provider is None:
            return None
        sections = "\n".join(f"## {subgoal}\n{output}" for subgoal, output in results if output)
        if not sections:
            return None
        prompt = (
            "You are the synthesis layer of an AI operating system. "
            "Combine the sub-goal results below into one final, coherent "
            "deliverable for the objective. Output only the deliverable.\n"
            f"Objective: {objective}\n"
            f"Sub-goal results:\n{sections}"
        )
        try:
            text = provider.generate(prompt).strip()
        except Exception:
            return None
        return text or None

    @staticmethod
    def _parse(text: str) -> list[str]:
        subgoals: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("- ", "* ")):
                stripped = stripped[2:].strip()
            elif stripped[:2].rstrip(".").isdigit() or (
                stripped[:1].isdigit() and stripped[1:2] in {".", ")"}
            ):
                stripped = stripped.lstrip("0123456789").lstrip(".) ").strip()
            else:
                continue
            if stripped:
                subgoals.append(stripped)
        return subgoals
