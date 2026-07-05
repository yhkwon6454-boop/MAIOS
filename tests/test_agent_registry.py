from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRegistry


class EchoAgent(Agent):
    def __init__(self, name: str = "echo") -> None:
        self.name = name

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {**context, "agent": self.name}


def test_agent_registry_registers_and_retrieves_agents():
    registry = AgentRegistry()
    capability = AgentCapability("plan", description="Create plans")
    agent = EchoAgent("planner")

    registration = registry.register(
        agent,
        capabilities=[capability],
        agent_id="planner-1",
        metadata={"node": "local"},
    )

    assert registration.agent is agent
    assert registration.agent_id == "planner-1"
    assert registration.agent_type == "planner"
    assert registration.capabilities == (capability,)
    assert registration.metadata == {"node": "local"}
    assert registry.get("planner-1") is registration
    assert registry.all() == [registration]


def test_agent_registry_supports_capability_and_type_discovery():
    registry = AgentRegistry()
    plan = AgentCapability("plan")
    execute = AgentCapability("execute")
    planner = registry.register(EchoAgent("planner"), [plan], agent_id="planner-1")
    executor = registry.register(EchoAgent("executor"), [execute], agent_id="executor-1")

    assert registry.discover("plan") == [planner]
    assert registry.discover(plan) == [planner]
    assert registry.discover("execute", agent_type="executor") == [executor]
    assert registry.discover("plan", agent_type="executor") == []


def test_agent_registry_supports_multiple_instances_of_same_agent_type():
    registry = AgentRegistry()
    capability = AgentCapability("memory")
    first = registry.register(
        EchoAgent("memory"),
        [capability],
        agent_id="memory-1",
        agent_type="memory",
    )
    second = registry.register(
        EchoAgent("memory"),
        [capability],
        agent_id="memory-2",
        agent_type="memory",
    )

    assert registry.discover("memory", agent_type="memory") == [first, second]


def test_agent_registry_unregisters_agents():
    registry = AgentRegistry()
    registry.register(EchoAgent(), [AgentCapability("echo")], agent_id="echo-1")

    assert registry.unregister("echo-1")
    assert registry.get("echo-1") is None
    assert not registry.unregister("missing")
