from maios.kernel.base import BaseKernel


class QualityKernel(BaseKernel):
    """실행 결과를 검증하는 Kernel"""

    def initialize(self):
        return True

    def execute(self, result):
        score = 0

        if result.get("status") == "EXECUTED":
            score += 50

        if result.get("cognitive_result"):
            score += 50

        return {
            "passed": score >= 100,
            "score": score,
            "result": result,
        }

    def validate(self, quality_result):
        return quality_result["passed"]

    def shutdown(self):
        return True