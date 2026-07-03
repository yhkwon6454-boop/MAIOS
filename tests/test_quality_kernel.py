from maios.kernel.executive_kernel import ExecutiveKernel
from maios.kernel.quality_kernel import QualityKernel
from maios.runtime.plan import Plan


def test_quality_kernel():
    plan = Plan(
        objective="적의 기동 분석",
        tasks=["정보 수집", "상황 분석", "위험 평가"],
        risk="HIGH",
        priority="URGENT",
    )

    executive = ExecutiveKernel()
    execution = executive.execute(plan)

    quality = QualityKernel()
    result = quality.execute(execution)

    assert result["passed"]
    assert result["score"] == 100
    assert quality.validate(result)