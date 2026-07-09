from __future__ import annotations

from maios.planning import GoalHorizon, MetaPlanner


def main() -> None:
    planner = MetaPlanner(mission_id="meta-demo", total_resource_budget=10.0)
    planner.create_goal(
        "Stabilize the current autonomous runtime",
        horizon=GoalHorizon.SHORT_TERM,
        urgency=0.9,
        impact=0.8,
        risk=0.4,
        required_capabilities=["execute", "quality"],
    )
    doctrine_goal = planner.create_goal(
        "Build a reusable mission-planning knowledge base",
        horizon=GoalHorizon.LONG_TERM,
        urgency=0.35,
        impact=0.95,
        required_capabilities=["research", "remember"],
    )

    plan, roadmap = planner.plan()
    print("Strategic priority order:")
    for goal in plan.goals:
        print(f"- {goal.goal_id}: {goal.objective} ({goal.priority_score:.2f})")

    print("\nInitial roadmap:")
    for step in roadmap.steps:
        print(
            f"- #{step.sequence} {step.objective}: "
            f"resource={step.resource_share:.2f}, agents={list(step.assigned_agents)}"
        )

    replanned = planner.apply_execution_result(
        doctrine_goal.goal_id,
        {"status": "FAILED", "error": "source coverage gap"},
    )
    if replanned is not None:
        print("\nReplanned roadmap after execution feedback:")
        for step in replanned.steps:
            print(f"- #{step.sequence} {step.objective}: {step.priority_score:.2f}")

    print("\nProgress report:")
    print(planner.progress_report())


if __name__ == "__main__":
    main()
