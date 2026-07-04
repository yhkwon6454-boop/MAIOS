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
        memory_context = self.memory_kernel.retrieve_context(objective)
        if "retrieved_memory" in memory_context and "mission" not in memory_context:
            memory_context["mission"] = memory_context["retrieved_memory"]

        return {
            **context,
            "memory_kernel": self.memory_kernel,
            "memory_context": memory_context,
        }
