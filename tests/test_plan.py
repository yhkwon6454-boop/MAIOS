from maios.runtime.plan import Plan


def test_plan_creation():

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
        output="작전 권고",
    )

    assert plan.objective == "북한군 기동 분석"
    assert len(plan.tasks) == 5
    assert plan.risk == "HIGH"
    assert plan.priority == "URGENT"
    assert plan.output == "작전 권고"
