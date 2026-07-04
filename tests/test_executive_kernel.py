from maios.kernel.executive_kernel import ExecutiveKernel
from maios.runtime.plan import Plan


def test_executive_kernel_execute():
    kernel = ExecutiveKernel()

    plan = Plan(
        objective="임무 분석 및 실행",
        tasks=["정보 수집", "상황 분석", "행동 방안 작성"],
        risk="MEDIUM",
        priority="HIGH",
    )

    result = kernel.execute(plan)

    assert result["status"] == "EXECUTED"
    assert "cognitive_result" in result
    assert kernel.validate(result)
