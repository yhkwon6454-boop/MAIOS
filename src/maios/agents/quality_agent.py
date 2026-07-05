from __future__ import annotations

from typing import Any

from maios.agents.base import Agent
from maios.kernel.quality_kernel import QualityKernel


class QualityAgent(Agent):
    name = "quality"

    def __init__(self, quality_kernel: QualityKernel | None = None) -> None:
        self.quality_kernel = quality_kernel or QualityKernel()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        model_output = context.get("model_output", "")
        qa_result = self.quality_kernel.evaluate([model_output])
        return {
            **context,
            "qa_result": qa_result,
        }
