from __future__ import annotations

from datetime import UTC, datetime, timedelta

from maios.agents import (
    AgentCapability,
    AgentRegistry,
    AgentRole,
    AgentRoleManager,
    NegotiationManager,
)
from maios.knowledge import KnowledgeGraph
from maios.planning import GoalHorizon, GoalStatus, MetaGoal, MetaPlanner
from maios.planning.meta import ExecutionRoadmap, RoadmapStep


class ResearchSpy:
    def __init__(self) -> None:
        self.questions: list[str] = []

    def run(self, question: str) -> str:
        self.questions.append(question)
        return f"report:{question}"


class AttributeOnlyImprover:
    pass


def test_meta_planner_creates_and_prioritizes_mixed_horizon_goals():
    planner = MetaPlanner(mission_id="sprint-11-4")
    long_goal = planner.create_goal(
        "Build enduring knowledge base",
        horizon=GoalHorizon.LONG_TERM,
        urgency=0.3,
        impact=0.9,
        required_capabilities=["research"],
    )
    short_goal = planner.create_goal(
        "Patch critical runtime blocker",
        horizon=GoalHorizon.SHORT_TERM,
        urgency=0.95,
        impact=0.8,
        risk=0.4,
        required_capabilities=["execute"],
    )

    ordered = planner.prioritize_goals()

    assert ordered[0] is short_goal
    assert ordered[1] is long_goal
    assert short_goal.priority_score > long_goal.priority_score


def test_meta_planner_builds_strategic_plan_and_records_metrics():
    planner = MetaPlanner(mission_id="mission-alpha")
    planner.create_goal("Immediate coordination", horizon="short_term", urgency=0.7)
    planner.create_goal("Improve doctrine", horizon="long_term", impact=0.9)

    plan = planner.build_strategic_plan()

    assert plan.mission_id == "mission-alpha"
    assert len(plan.goals) == 2
    assert set(plan.priority_order) == set(planner.goals)
    assert plan.balance_metrics["short_term_count"] == 1.0
    assert plan.balance_metrics["long_term_count"] == 1.0


def test_meta_planner_tracks_goal_progress_and_completion_metrics():
    planner = MetaPlanner()
    goal = planner.create_goal("Complete reporting", urgency=0.8)

    planner.update_goal_progress(goal.goal_id, 1.0, {"quality_score": 0.92})
    report = planner.progress_report()

    assert goal.status == GoalStatus.COMPLETED
    assert goal.completion_metrics["quality_score"] == 0.92
    assert report["completed_count"] == 1
    assert report["completion_rate"] == 1.0


def test_meta_goal_validation_and_serialization_helpers():
    deadline = datetime.now(UTC) + timedelta(hours=12)
    goal = MetaGoal("Serialize meta goal", deadline=deadline, progress=0.2)
    step = RoadmapStep(
        goal_id=goal.goal_id,
        objective=goal.objective,
        sequence=1,
        priority_score=0.5,
        capabilities=("plan",),
    )
    roadmap = ExecutionRoadmap(
        plan_id="plan-1",
        steps=(step,),
        resource_allocations={goal.goal_id: 1.0},
        agent_allocations={goal.goal_id: ("agent-1",)},
    )

    assert goal.to_dict()["deadline"] == deadline.isoformat()
    assert step.to_dict()["goal_id"] == goal.goal_id
    assert roadmap.to_dict()["agent_allocations"][goal.goal_id] == ["agent-1"]

    try:
        MetaGoal("   ")
    except ValueError as exc:
        assert "objective" in str(exc)
    else:
        raise AssertionError("Expected empty goal objective to fail.")


def test_meta_planner_empty_report_and_missing_goal_paths():
    planner = MetaPlanner()

    assert planner.progress_report()["goal_count"] == 0
    assert planner.research_goal("missing") is None
    try:
        planner.update_goal_progress("missing", 0.1)
    except KeyError as exc:
        assert "Unknown goal" in str(exc)
    else:
        raise AssertionError("Expected missing goal update to fail.")


def test_meta_planner_research_and_no_change_execution_paths():
    research = ResearchSpy()
    planner = MetaPlanner(
        research_engine=research,
        self_improvement_engine=AttributeOnlyImprover(),
    )
    goal = planner.create_goal("Research this objective")

    assert planner.research_goal(goal.goal_id) == "report:Research this objective"
    assert research.questions == ["Research this objective"]
    assert planner.apply_execution_result(goal.goal_id, {"status": "RUNNING"}) is None


def test_meta_planner_records_to_knowledge_graph_and_negotiates_without_participants():
    graph = KnowledgeGraph()
    planner = MetaPlanner(knowledge_graph=graph)
    planner.create_goal("Record goal", urgency=0.8)
    planner.create_goal("Second goal", urgency=0.7)

    plan, roadmap = planner.plan()

    assert graph.get_node(plan.plan_id) is not None
    assert graph.get_node(roadmap.roadmap_id) is not None
    assert any(edge.relationship == "part_of" for edge in graph.edges.values())


def test_meta_planner_selects_coordinator_participants_for_negotiation():
    registry = AgentRegistry()
    registry.register(
        object(),
        [AgentCapability("plan")],
        agent_id="coord-1",
        agent_type="coordinator",
    )
    role_manager = AgentRoleManager(registry)
    role_manager.assign_role("coord-1", AgentRole.COORDINATOR)
    negotiation = NegotiationManager(role_manager=role_manager)
    planner = MetaPlanner(role_manager=role_manager, negotiation_manager=negotiation)
    planner.create_goal("Balance one", urgency=0.5)
    planner.create_goal("Balance two", urgency=0.4)

    planner.build_strategic_plan()

    session = negotiation.sessions()[0]
    assert session.participants == ["coord-1"]
    assert session.proposals[0].proposer_id == "coord-1"
