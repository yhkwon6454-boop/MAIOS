from __future__ import annotations

from maios.kernel.executive_brain import DecisionContext, ExecutiveBrain, PlannerType
from maios.planning import MetaGoal


class ResearchSpy:
    def run(self, question: str) -> str:
        return question


class SwarmSpy:
    pass


def test_executive_brain_selects_meta_for_multiple_goals():
    context = DecisionContext("Balance missions")
    context.add_goal(MetaGoal("One"))
    context.add_goal(MetaGoal("Two"))

    assert ExecutiveBrain().select_planner(context) == PlannerType.META


def test_executive_brain_selects_research_when_capability_requested():
    context = DecisionContext("Investigate", requested_capabilities=("research",))
    brain = ExecutiveBrain(research_engine=ResearchSpy())

    assert brain.select_planner(context) == PlannerType.RESEARCH


def test_executive_brain_selects_swarm_before_distributed_for_capability_work():
    context = DecisionContext("Coordinate", requested_capabilities=("execute",))
    brain = ExecutiveBrain(swarm_manager=SwarmSpy(), distributed_runtime=object())

    assert brain.select_planner(context) == PlannerType.SWARM


def test_executive_brain_falls_back_to_distributed_or_direct():
    distributed_context = DecisionContext("Run remotely")
    direct_context = DecisionContext("Complete locally")

    assert (
        ExecutiveBrain(distributed_runtime=object()).select_planner(distributed_context)
        == PlannerType.DISTRIBUTED
    )
    assert ExecutiveBrain().select_planner(direct_context) == PlannerType.DIRECT


def test_executive_decision_contains_priority_order_and_rationale():
    context = DecisionContext.from_goal("Plan mission", capabilities=["plan"])
    brain = ExecutiveBrain()

    decision = brain.decide(context)

    assert decision.selected_planner == PlannerType.META
    assert decision.priority_order == (context.goals[0].goal_id,)
    assert "Selected meta planner" in decision.rationale
