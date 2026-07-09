from __future__ import annotations

from typing import Any

from maios.adapters.llm_provider import BaseLLMProvider


class TaskExecutor:
    """LLM-backed direct task execution for the Act phase.

    Produces the actual deliverable for an objective (summary, draft,
    translation, analysis). Returns ``None`` when no provider is configured
    or the provider fails, so the caller falls back to echo behavior.
    """

    def __init__(self, provider: BaseLLMProvider | None = None) -> None:
        self.provider = provider

    @property
    def available(self) -> bool:
        return self.provider is not None

    def execute(
        self,
        objective: str,
        *,
        interpretation: str | None = None,
        capabilities: tuple[str, ...] | list[str] = (),
        recalled: tuple[str, ...] | list[str] = (),
        lessons: tuple[str, ...] | list[str] = (),
    ) -> dict[str, Any] | None:
        provider = self.provider
        if provider is None:
            return None
        memory_block = ""
        if recalled:
            memory_block = (
                "Relevant memories from earlier work:\n"
                + "\n".join(f"- {entry}" for entry in recalled)
                + "\n"
            )
        lessons_block = ""
        if lessons:
            lessons_block = (
                "Lessons from previous pursuits:\n"
                + "\n".join(f"- {lesson}" for lesson in lessons)
                + "\n"
            )
        prompt = (
            "You are the execution layer of an AI operating system. "
            "Perform the objective directly and output only the deliverable "
            "(no preamble, no meta commentary).\n"
            f"Objective: {objective}\n"
            + (f"Requested capabilities: {', '.join(capabilities)}\n" if capabilities else "")
            + (f"Situation assessment: {interpretation}\n" if interpretation else "")
            + memory_block
            + lessons_block
        )
        try:
            output = provider.generate(prompt).strip()
        except Exception:
            return None
        if not output:
            return None
        return {
            "status": "COMPLETED",
            "planner": "direct",
            "output": output,
            "generated": True,
        }
