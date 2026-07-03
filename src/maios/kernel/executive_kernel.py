from maios.kernel.base import BaseKernel
from maios.kernel.cognitive_kernel import CognitiveKernel
from maios.runtime.plan import Plan


class ExecutiveKernel(BaseKernel):
    """Plan 실행을 담당하는 Kernel"""

    def __init__(self):
        self.cognitive_kernel = CognitiveKernel()

    def initialize(self):
        return True

    def execute(self, plan: Plan):
        cognitive_result = self.cognitive_kernel.execute(plan)

        return {
            "objective": plan.objective,
            "tasks": plan.tasks,
            "risk": plan.risk,
            "priority": plan.priority,
            "cognitive_result": cognitive_result,
            "status": "EXECUTED",
        }

    def validate(self, result):
        return (
            result.get("status") == "EXECUTED"
            and "cognitive_result" in result
        )

    def shutdown(self):
        return True