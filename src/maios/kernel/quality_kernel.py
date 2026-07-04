from maios.kernel.base import BaseKernel
from maios.runtime.models import QAResult, Status


class QualityKernel(BaseKernel):
    """Kernel that validates execution results."""

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

    def evaluate(self, outputs: list[str]) -> QAResult:
        issues = []

        if not outputs:
            issues.append("No packet outputs produced.")

        for index, output in enumerate(outputs):
            if not output or not output.strip():
                issues.append(f"Packet output is empty: {index}")

        score = 100 if not issues else max(0, 100 - (len(issues) * 25))
        status = Status.COMPLETED if score >= 70 else Status.NEEDS_REVISION

        return QAResult(status=status, score=score, issues=issues)

    def validate(self, quality_result):
        return quality_result["passed"]

    def shutdown(self):
        return True
