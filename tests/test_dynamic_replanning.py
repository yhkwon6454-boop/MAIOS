from __future__ import annotations

from maios.planning import GoalStatus, MetaPlanner


class ImprovementSpy:
    def __init__(self) -> None:
        self.history = []

    def analyze_execution_history(self, history):
        self.history.append(list(history))
        return None


def test_dynamic_replanning_reorders_after_execution_failure():
    planner = MetaPlanner()
    stable = planner.create_goal("Stable mission", urgency=0.7, impact=0.7)
    failing = planner.create_goal("Weak mission", urgency=0.2, impact=0.2, risk=0.0)
    initial = planner.allocate_resources(planner.build_strategic_plan())

    replanned = planner.apply_execution_result(
        failing.goal_id,
        {"status": "FAILED", "error": "blocked dependency"},
    )

    assert replanned is not None
    assert initial.roadmap_id != replanned.roadmap_id
    assert failing.status == GoalStatus.BLOCKED
    assert replanned.steps[0].goal_id in {stable.goal_id, failing.goal_id}
    assert failing.priority_score > 0.2


def test_dynamic_replanning_removes_completed_goals_from_roadmap():
    planner = MetaPlanner()
    completed = planner.create_goal("Finish now", urgency=1.0, impact=1.0)
    remaining = planner.create_goal("Continue next", urgency=0.5, impact=0.5)

    replanned = planner.apply_execution_result(
        completed.goal_id,
        {"status": "COMPLETED", "progress_delta": 1.0},
    )

    assert replanned is not None
    assert completed.status == GoalStatus.COMPLETED
    assert [step.goal_id for step in replanned.steps] == [remaining.goal_id]


def test_dynamic_replanning_sends_execution_feedback_to_improvement_engine():
    spy = ImprovementSpy()
    planner = MetaPlanner(self_improvement_engine=spy)
    goal = planner.create_goal("Observe feedback")

    planner.apply_execution_result(goal.goal_id, {"status": "FAILED", "error": "timeout"})

    assert spy.history == [[{"status": "FAILED", "error": "timeout"}]]
