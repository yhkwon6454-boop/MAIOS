from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRegistry, AgentRole, AgentRoleManager


class CapabilityAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"output": self.name}


def test_capability_matching_requires_all_requested_capabilities():
    registry = AgentRegistry()
    registry.register(
        CapabilityAgent("planner"),
        [AgentCapability("plan"), AgentCapability("summarize")],
        agent_id="planner-1",
    )
    registry.register(
        CapabilityAgent("executor"),
        [AgentCapability("execute")],
        agent_id="executor-1",
    )
    manager = AgentRoleManager(registry)
    manager.assign_role("planner-1", AgentRole.PLANNER)
    manager.assign_role("executor-1", AgentRole.EXECUTOR)

    matches = manager.select_agents(["plan", "summarize"])

    assert [match.agent_id for match in matches] == ["planner-1"]


def test_capability_matching_accepts_agent_capability_objects():
    registry = AgentRegistry()
    capability = AgentCapability("remember", input_types=("text",))
    registry.register(CapabilityAgent("memory"), [capability], agent_id="memory-1")
    manager = AgentRoleManager(registry)
    manager.assign_role("memory-1", AgentRole.MEMORY)

    match = manager.select_best(capability, role=AgentRole.MEMORY)

    assert match.agent_id == "memory-1"


def test_capability_matching_prefers_primary_role_over_secondary_role():
    registry = AgentRegistry()
    first = registry.register(
        CapabilityAgent("primary"),
        [AgentCapability("review")],
        agent_id="primary-1",
    )
    second = registry.register(
        CapabilityAgent("secondary"),
        [AgentCapability("review")],
        agent_id="secondary-1",
    )
    manager = AgentRoleManager(registry)
    manager.assign_role("secondary-1", AgentRole.EXECUTOR, secondary_roles=[AgentRole.QUALITY])
    manager.assign_role("primary-1", AgentRole.QUALITY)
    first.active_tasks = 2

    matches = manager.select_agents(["review"], role=AgentRole.QUALITY)

    assert matches == [first, second]


def test_capability_matching_limits_results_after_ranking():
    registry = AgentRegistry()
    registry.register(CapabilityAgent("a"), [AgentCapability("plan")], agent_id="a")
    registry.register(CapabilityAgent("b"), [AgentCapability("plan")], agent_id="b")
    manager = AgentRoleManager(registry)
    manager.assign_role("a", AgentRole.PLANNER)
    manager.assign_role("b", AgentRole.PLANNER)

    matches = manager.select_agents(["plan"], role=AgentRole.PLANNER, limit=1)

    assert [match.agent_id for match in matches] == ["a"]
