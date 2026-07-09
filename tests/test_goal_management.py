from __future__ import annotations

from maios.planning import GoalHorizon, GoalStatus, MetaPlanner


def test_goal_model_supports_long_term_and_short_term_goals():
    planner = MetaPlanner()
    short_goal = planner.create_goal("Stabilize current mission", horizon="short_term")
    long_goal = planner.create_goal("Build institutional memory", horizon="long_term")

    assert short_goal.horizon == GoalHorizon.SHORT_TERM
    assert long_goal.horizon == GoalHorizon.LONG_TERM
    assert short_goal.status == GoalStatus.PROPOSED
    assert long_goal.goal_id != short_goal.goal_id


def test_goal_dependencies_reduce_priority_until_dependency_completes():
    planner = MetaPlanner()
    foundation = planner.create_goal("Prepare foundation", urgency=0.2, impact=0.2)
    dependent = planner.create_goal(
        "Exploit foundation",
        urgency=0.8,
        impact=0.8,
        dependencies=[foundation.goal_id],
    )
    blocked_score = dependent.priority_score

    planner.update_goal_progress(foundation.goal_id, 1.0)
    planner.prioritize_goals()

    assert dependent.priority_score > blocked_score


def test_goal_records_failed_execution_as_blocked_and_raises_priority():
    planner = MetaPlanner()
    goal = planner.create_goal("Recover failed mission", urgency=0.4, risk=0.1)
    old_score = goal.priority_score

    planner.apply_execution_result(
        goal.goal_id,
        {"status": "FAILED", "error": "agent unavailable"},
        replan=False,
    )

    assert goal.status == GoalStatus.BLOCKED
    assert goal.risk > 0.1
    assert goal.priority_score > old_score
    assert goal.execution_results[-1]["error"] == "agent unavailable"
