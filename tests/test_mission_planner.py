from maios.planner.mission_planner import MissionPlanner


def test_mission_planner():

    planner = MissionPlanner()

    plan = planner.analyze("북한군 기동을 분석하라.")

    assert plan.mission == "북한군 기동을 분석하라."
    assert plan.intent == "북한군 기동을 분석하라."

    assert len(plan.tasks) == 5

    assert plan.tasks[0] == "정보 수집"
    assert plan.tasks[1] == "상황 분석"
    assert plan.tasks[2] == "행동 방안 작성"
    assert plan.tasks[3] == "위험 평가"
    assert plan.tasks[4] == "최종 권고"

    assert plan.priority == "HIGH"
    assert plan.risk == "MEDIUM"
