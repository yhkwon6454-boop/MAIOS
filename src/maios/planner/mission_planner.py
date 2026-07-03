from dataclasses import dataclass
from typing import List


@dataclass
class MissionPlan:
    mission: str
    intent: str
    tasks: List[str]
    priority: str
    risk: str


class MissionPlanner:
    """
    MAIOS Mission Planner

    사용자의 임무를 분석하여
    실행 가능한 계획으로 변환한다.
    """

    def analyze(self, mission: str) -> MissionPlan:

        intent = self._extract_intent(mission)

        tasks = self._build_tasks(intent)

        priority = self._determine_priority(intent)

        risk = self._assess_risk(intent)

        return MissionPlan(
            mission=mission,
            intent=intent,
            tasks=tasks,
            priority=priority,
            risk=risk,
        )

    def _extract_intent(self, mission: str) -> str:
        return mission.strip()

    def _build_tasks(self, intent: str) -> List[str]:
        return [
            "정보 수집",
            "상황 분석",
            "행동 방안 작성",
            "위험 평가",
            "최종 권고",
        ]

    def _determine_priority(self, intent: str) -> str:
        return "HIGH"

    def _assess_risk(self, intent: str) -> str:
        return "MEDIUM"