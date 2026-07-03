from __future__ import annotations

from maios.runtime.models import QAResult, Status


class QualityKernel:
    """
    최소 품질검증 커널.
    실제 구현에서는 사실성, 논리성, 완전성, 위험성 검사를 별도 모듈로 분리한다.
    """

    def evaluate(self, outputs: list[str]) -> QAResult:
        issues: list[str] = []
        score = 40

        joined = "\n".join(outputs).strip()

        if not joined:
            return QAResult(status=Status.FAILED, score=0, issues=["출력 없음"])

        if len(joined) < 300:
            score -= 8
            issues.append("출력이 짧아 분석 깊이가 부족할 수 있음")

        if "근거" not in joined and "분석" not in joined:
            score -= 4
            issues.append("근거 또는 분석 표현이 부족함")

        if score >= 36:
            status = Status.COMPLETED
        elif score >= 28:
            status = Status.NEEDS_REVISION
        else:
            status = Status.FAILED

        return QAResult(status=status, score=score, issues=issues)
