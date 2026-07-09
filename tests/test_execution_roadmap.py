from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRole
from maios.distributed import DistributedRuntime
from maios.planning import MetaPlanner


class DemoAgent(Agent):
    name = "demo-agent"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"output": context.get("task", "done")}


def test_execution_roadmap_allocates_resources_by_priority():
    planner = MetaPlanner(total_resource_budget=10.0)
    high = planner.create_goal("High priority", urgency=1.0, impact=1.0)
    low = planner.create_goal("Low priority", urgency=0.1, impact=0.1)

    plan, roadmap = planner.plan()

    assert roadmap.plan_id == plan.plan_id
    assert roadmap.steps[0].goal_id == high.goal_id
    assert roadmap.resource_allocations[high.goal_id] > roadmap.resource_allocations[low.goal_id]
    assert sum(roadmap.resource_allocations.values()) == 10.0


def test_execution_roadmap_allocates_agents_swarms_and_runtime_nodes():
    runtime = DistributedRuntime(mission_id="roadmap")
    runtime.register_node("node-a", capacity=2)
    runtime.register_agent(
        DemoAgent(),
        [AgentCapability("research"), AgentCapability("execute")],
        agent_id="agent-1",
        primary_role=AgentRole.SPECIALIST,
    )
    planner = MetaPlanner(distributed_runtime=runtime, mission_id="roadmap")
    goal = planner.create_goal(
        "Coordinate research execution",
        required_capabilities=["research", "execute"],
    )

    roadmap = planner.allocate_resources(planner.build_strategic_plan())
    step = roadmap.steps[0]

    assert step.goal_id == goal.goal_id
    assert step.assigned_agents == ("agent-1",)
    assert step.assigned_node in {"local", "node-a"}
    assert step.swarm_id.startswith("SWARM-")
    assert roadmap.agent_allocations[goal.goal_id] == ("agent-1",)


def test_execution_roadmap_exposes_next_planned_steps():
    planner = MetaPlanner()
    planner.create_goal("First", urgency=0.9)
    planner.create_goal("Second", urgency=0.8)

    roadmap = planner.allocate_resources(planner.build_strategic_plan())

    assert len(roadmap.next_steps(limit=1)) == 1
    assert roadmap.next_steps(limit=1)[0].status == "PLANNED"
