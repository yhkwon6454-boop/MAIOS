from __future__ import annotations

from maios.kernel import DecisionContext
from maios.planning import GoalHorizon, MetaGoal


def test_decision_context_from_goal_normalizes_capabilities_and_goal():
    context = DecisionContext.from_goal(
        "Coordinate operation",
        urgency=0.9,
        impact=0.8,
        risk=0.3,
        capabilities=["plan", "execute"],
        mission_id="mission-1",
    )

    assert context.mission_id == "mission-1"
    assert context.requested_capabilities == ("plan", "execute")
    assert context.goals[0].objective == "Coordinate operation"
    assert context.goals[0].horizon == GoalHorizon.SHORT_TERM


def test_decision_context_tracks_failures_and_repeated_mistakes():
    context = DecisionContext("Recover service")

    context.record_outcome({"status": "FAILED", "error": "timeout"})
    context.record_outcome({"status": "BLOCKED", "error": "timeout"})
    context.record_outcome({"status": "COMPLETED"})

    assert context.failure_count() == 2
    assert context.repeated_mistakes() == ("timeout",)


def test_decision_context_serializes_goals_and_rejects_empty_objective():
    context = DecisionContext("Build plan", requested_capabilities=("plan",))
    context.add_goal(MetaGoal("Secondary goal", horizon="long_term"))

    data = context.to_dict()

    assert data["objective"] == "Build plan"
    assert data["requested_capabilities"] == ["plan"]
    assert data["goals"][0]["objective"] == "Secondary goal"
    try:
        DecisionContext("   ")
    except ValueError as exc:
        assert "objective" in str(exc)
    else:
        raise AssertionError("Expected empty decision objective to fail.")
