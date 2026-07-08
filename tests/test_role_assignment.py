from __future__ import annotations

from typing import Any

from maios.agents import (
    Agent,
    AgentCapability,
    AgentRegistry,
    AgentRole,
    AgentRoleManager,
    CollaborationManager,
    SharedMemoryManager,
)
from maios.distributed import DistributedRuntime


class AssignmentAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name
        self.seen_context: dict[str, Any] = {}

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self.seen_context = context
        return {
            "output": self.name,
            "shared_memory": {self.name: context.get("task")},
        }


def test_role_manager_supports_runtime_role_reassignment():
    registry = AgentRegistry()
    registry.register(
        AssignmentAgent("worker"),
        [AgentCapability("plan"), AgentCapability("execute")],
        agent_id="agent-1",
    )
    manager = AgentRoleManager(registry)
    manager.assign_role("agent-1", AgentRole.PLANNER)

    profile = manager.reassign_role("agent-1", AgentRole.EXECUTOR)

    assert profile.primary_role == AgentRole.EXECUTOR
    assert manager.select_best("execute", role=AgentRole.EXECUTOR).agent_id == "agent-1"
    assert manager.select_best("plan", role=AgentRole.PLANNER) is None


def test_role_manager_supports_primary_and_secondary_roles():
    registry = AgentRegistry()
    registry.register(
        AssignmentAgent("hybrid"),
        [AgentCapability("plan")],
        agent_id="hybrid-1",
    )
    manager = AgentRoleManager(registry)
    manager.assign_role(
        "hybrid-1",
        AgentRole.PLANNER,
        secondary_roles=[AgentRole.QUALITY],
    )

    assert manager.select_best("plan", role=AgentRole.PLANNER).agent_id == "hybrid-1"
    assert manager.select_best("plan", role=AgentRole.QUALITY).agent_id == "hybrid-1"
    assert (
        manager.select_best(
            "plan",
            role=AgentRole.QUALITY,
            include_secondary_roles=False,
        )
        is None
    )


def test_collaboration_manager_uses_role_aware_team_selection():
    registry = AgentRegistry()
    shared_memory = SharedMemoryManager()
    role_manager = AgentRoleManager(
        registry,
        shared_memory_manager=shared_memory,
        mission_id="mission-1",
    )
    planner = registry.register(
        AssignmentAgent("planner"),
        [AgentCapability("plan")],
        agent_id="planner-1",
        agent_type="planner",
    )
    registry.register(
        AssignmentAgent("backup"),
        [AgentCapability("plan")],
        agent_id="backup-1",
        agent_type="backup",
    )
    role_manager.assign_role("planner-1", AgentRole.PLANNER)
    role_manager.assign_role("backup-1", AgentRole.OBSERVER)
    manager = CollaborationManager(
        registry,
        shared_memory_manager=shared_memory,
        role_manager=role_manager,
        mission_id="mission-1",
    )

    team = manager.form_team(["plan"], role=AgentRole.PLANNER)

    assert team == [planner]


def test_collaboration_manager_can_delegate_by_role():
    registry = AgentRegistry()
    role_manager = AgentRoleManager(registry)
    registry.register(
        AssignmentAgent("planner"),
        [AgentCapability("plan")],
        agent_id="planner-1",
        agent_type="planner",
    )
    registry.register(
        AssignmentAgent("observer"),
        [AgentCapability("plan")],
        agent_id="observer-1",
        agent_type="observer",
    )
    role_manager.assign_role("planner-1", AgentRole.PLANNER)
    role_manager.assign_role("observer-1", AgentRole.OBSERVER)
    manager = CollaborationManager(registry, role_manager=role_manager)

    task = manager.delegate("plan", {"task": "draft"}, role=AgentRole.PLANNER)

    assert task.agent_id == "planner-1"
    assert task.status == "COMPLETED"


def test_distributed_runtime_assigns_and_reassigns_roles():
    runtime = DistributedRuntime(mission_id="mission-1")
    runtime.register_agent(
        AssignmentAgent("executor"),
        [AgentCapability("execute")],
        agent_id="executor-1",
        primary_role=AgentRole.EXECUTOR,
    )

    task = runtime.execute_agent(
        "execute",
        {"task": "run"},
        role=AgentRole.EXECUTOR,
    )
    profile = runtime.reassign_role("executor-1", AgentRole.QUALITY)

    assert task.status == "COMPLETED"
    assert task.agent_id == "executor-1"
    assert profile.primary_role == AgentRole.QUALITY
    stored = runtime.shared_memory_manager.read(
        "mission-1",
        "role_manager",
        "agent_profile:executor-1",
    )
    assert stored["primary_role"] == "quality"


def test_distributed_runtime_unregistration_keeps_role_profiles_in_sync():
    runtime = DistributedRuntime(mission_id="mission-1")
    runtime.register_agent(
        AssignmentAgent("planner"),
        [AgentCapability("plan")],
        agent_id="planner-1",
        node_id="node-a",
        primary_role=AgentRole.PLANNER,
    )

    assert runtime.unregister_node("node-a")
    assert runtime.agent_registry.get("planner-1") is None
    assert runtime.role_manager.profile("planner-1") is None
    assert not runtime.unregister_node("missing")


def test_distributed_runtime_role_helpers_raise_for_unknown_agents():
    runtime = DistributedRuntime()

    try:
        runtime.assign_role("missing", AgentRole.PLANNER)
    except KeyError as exc:
        assert "Unknown agent" in str(exc)
    else:
        raise AssertionError("Expected role assignment to fail for missing agent.")
