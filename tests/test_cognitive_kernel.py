from maios.kernel.cognitive_kernel import CognitiveKernel
from maios.runtime.plan import Plan


def test_cognitive_kernel_execute():

    plan = Plan(
        objective="북한군 기동 분석",
        tasks=[
            "정보 수집",
            "기동 분석",
            "COA 작성",
            "위험도 평가",
            "최종 권고",
        ],
        risk="HIGH",
        priority="URGENT",
    )

    kernel = CognitiveKernel()

    result = kernel.execute(plan)

    assert result["status"] == "THINK_COMPLETE"
    assert result["objective"] == "북한군 기동 분석"
    assert result["risk"] == "HIGH"
    assert kernel.validate(result)