from __future__ import annotations

from typing import Any

import pytest

from maios.agents import (
    Agent,
    AgentCapability,
    AgentRegistry,
    AgentRole,
    AgentRoleManager,
    SharedMemoryManager,
)


class RoleAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"output": self.name, "shared_memory": {self.name: context.get("task")}}


def test_agent_role_manager_assigns_profiles_and_syncs_registry_metadata():
    registry = AgentRegistry()
    registry.register(
        RoleAgent("planner"),
        [AgentCapability("plan")],
        agent_id="planner-1",
        agent_type="worker",
    )
    manager = AgentRoleManager(registry)

    profile = manager.assign_role(
        "planner-1",
        AgentRole.PLANNER,
        secondary_roles=[AgentRole.COORDINATOR],
    )

    registration = registry.get("planner-1")
    assert profile.primary_role == AgentRole.PLANNER
    assert profile.has_role(AgentRole.COORDINATOR)
    assert registration.metadata["primary_role"] == "planner"
    assert registration.metadata["secondary_roles"] == ["coordinator"]


def test_agent_role_manager_records_profiles_in_shared_memory():
    registry = AgentRegistry()
    shared_memory = SharedMemoryManager()
    registry.register(
        RoleAgent("memory"),
        [AgentCapability("remember")],
        agent_id="memory-1",
    )
    manager = AgentRoleManager(
        registry,
        shared_memory_manager=shared_memory,
        mission_id="mission-1",
    )

    manager.assign_role("memory-1", AgentRole.MEMORY)

    stored = shared_memory.read(
        "mission-1",
        "role_manager",
        "agent_profile:memory-1",
    )
    assert stored["primary_role"] == "memory"
    assert stored["capabilities"] == ["remember"]


def test_agent_role_manager_unregisters_profiles_without_unregistering_agent():
    registry = AgentRegistry()
    registry.register(RoleAgent("observer"), [AgentCapability("observe")], agent_id="agent-1")
    manager = AgentRoleManager(registry)
    manager.assign_role("agent-1", AgentRole.OBSERVER)

    manager.unregister("agent-1")

    assert registry.get("agent-1") is not None
    assert manager.profile("agent-1").primary_role == "observer"


def test_agent_role_manager_adds_and_removes_secondary_roles():
    registry = AgentRegistry()
    registry.register(
        RoleAgent("specialist"),
        [AgentCapability("analyze")],
        agent_id="specialist-1",
        agent_type="specialist",
    )
    manager = AgentRoleManager(registry)

    added = manager.add_secondary_role("specialist-1", AgentRole.QUALITY)
    duplicate = manager.add_secondary_role("specialist-1", AgentRole.QUALITY)
    removed = manager.remove_secondary_role("specialist-1", AgentRole.QUALITY)

    assert added.primary_role == "specialist"
    assert duplicate.secondary_roles == (AgentRole.QUALITY,)
    assert removed.secondary_roles == ()


def test_agent_role_manager_exposes_profiles_and_metadata_fallback():
    registry = AgentRegistry()
    registry.register(
        RoleAgent("legacy"),
        [AgentCapability("legacy")],
        agent_id="legacy-1",
        agent_type="legacy",
        metadata={
            "primary_role": "specialist",
            "secondary_roles": ["observer"],
            "role_metadata": {"source": "legacy"},
        },
    )
    manager = AgentRoleManager(registry)

    profile = manager.profile("legacy-1")

    assert profile.primary_role == "specialist"
    assert profile.secondary_roles == ("observer",)
    assert profile.metadata == {"source": "legacy"}
    assert manager.profiles() == [profile]
    assert manager.profile("missing") is None


def test_agent_role_manager_raises_for_unknown_agents_and_profiles():
    manager = AgentRoleManager(AgentRegistry())

    with pytest.raises(KeyError, match="Unknown agent"):
        manager.assign_role("missing", AgentRole.PLANNER)

    with pytest.raises(KeyError, match="Unknown agent profile"):
        manager.remove_secondary_role("missing", AgentRole.PLANNER)
