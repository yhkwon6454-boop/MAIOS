from __future__ import annotations

from typing import Any

from maios.agents.base import Agent
from maios.kernel.memory_kernel import MemoryKernel
from maios.runtime.models import Mission


class MemoryAgent(Agent):
    name = "memory"

    def __init__(self, memory_kernel: MemoryKernel | None = None) -> None:
        self.memory_kernel = memory_kernel or MemoryKernel()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        mission = context["mission"]
        objective = mission.objective if isinstance(mission, Mission) else str(mission)
        self.memory_kernel.remember_short_term(objective)
        memory_context = self._retrieve_memory_context(objective)

        return {
            **context,
            "memory_kernel": self.memory_kernel,
            "memory_context": memory_context,
        }

    def _retrieve_memory_context(self, objective: str) -> dict[str, str]:
        documents = self.memory_kernel.retrieve(objective, top_k=3)
        if not documents:
            return {}

        return {
            "mission": "\n".join(
                document.content if hasattr(document, "content") else str(document)
                for document in documents
            )
        }
