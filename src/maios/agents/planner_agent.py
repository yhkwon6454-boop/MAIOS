from __future__ import annotations

from typing import Any

from maios.agents.base import Agent
from maios.planner.mission_planner import MissionPlanner
from maios.runtime.models import Mission
from maios.runtime.plan import Plan


class PlannerAgent(Agent):
    name = "planner"

    def __init__(self, mission_planner: MissionPlanner | None = None) -> None:
        self.mission_planner = mission_planner or MissionPlanner()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        mission = context["mission"]
        objective = mission.objective if isinstance(mission, Mission) else str(mission)
        mission_plan = self.mission_planner.analyze(objective)
        execution_plan = Plan(
            objective=mission_plan.intent,
            tasks=mission_plan.tasks,
            risk=mission_plan.risk,
            priority=mission_plan.priority,
            output=getattr(mission, "expected_output", ""),
        )

        return {
            **context,
            "mission_plan": mission_plan,
            "execution_plan": execution_plan,
        }
