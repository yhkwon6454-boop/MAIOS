from __future__ import annotations

from typing import Any

from maios.agents.base import Agent
from maios.kernel.executive_kernel import ExecutiveKernel


class ExecutorAgent(Agent):
    name = "executor"

    def __init__(self, executive_kernel: ExecutiveKernel | None = None) -> None:
        self.executive_kernel = executive_kernel or ExecutiveKernel()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        execution_result = self.executive_kernel.execute(context["execution_plan"])

        return {
            **context,
            "execution_result": execution_result,
        }
