from __future__ import annotations

from typing import Any

from maios.agents import (
    Agent,
    AgentCapability,
    AgentRegistry,
    AgentRole,
    AgentRoleManager,
    NegotiationManager,
    SharedMemoryManager,
    SwarmManager,
)
from maios.distributed import DistributedRuntime
from maios.events import EventBus
from maios.protocol import AgentProtocol


class SwarmAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name
        self.seen_context: dict[str, Any] = {}

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self.seen_context = context
        return {
            "output": f"{self.name}:{context.get('task')}",
            "shared_memory": {self.name: context.get("task")},
        }


def test_swarm_manager_forms_dynamic_swarm_and_records_state():
    registry = AgentRegistry()
    shared_memory = SharedMemoryManager()
    event_bus = EventBus()
    role_manager = AgentRoleManager(
        registry,
        shared_memory_manager=shared_memory,
        mission_id="mission-1",
    )
    registry.register(SwarmAgent("planner"), [AgentCapability("plan")], agent_id="planner-1")
    registry.register(SwarmAgent("executor"), [AgentCapability("execute")], agent_id="executor-1")
    role_manager.assign_role("planner-1", AgentRole.PLANNER)
    role_manager.assign_role("executor-1", AgentRole.EXECUTOR)
    manager = SwarmManager(
        registry=registry,
        role_manager=role_manager,
        shared_memory_manager=shared_memory,
        event_bus=event_bus,
        mission_id="mission-1",
    )

    swarm = manager.form_swarm("mission swarm", ["plan", "execute"])

    assert set(swarm.members) == {"planner-1", "executor-1"}
    assert swarm.leader_id in swarm.members
    stored = shared_memory.read("mission-1", "swarm", f"swarm:{swarm.swarm_id}")
    assert stored["name"] == "mission swarm"
    assert stored["members"] == swarm.members
    assert [message.event_type for message in event_bus.history][:2] == [
        "swarm.leader.elected",
        "swarm.formed",
    ]


def test_swarm_manager_integrates_with_negotiation_and_runtime():
    runtime = DistributedRuntime(mission_id="mission-1")
    runtime.register_agent(
        SwarmAgent("planner"),
        [AgentCapability("plan")],
        agent_id="planner-1",
        primary_role=AgentRole.PLANNER,
    )
    runtime.register_agent(
        SwarmAgent("backup"),
        [AgentCapability("plan")],
        agent_id="backup-1",
        primary_role=AgentRole.PLANNER,
    )

    swarm = runtime.form_swarm("planner swarm", ["plan"], role=AgentRole.PLANNER)
    task = runtime.allocate_swarm_task(swarm.swarm_id, "plan", {"task": "draft"})

    assert isinstance(runtime.swarm_manager.negotiation_manager, NegotiationManager)
    assert task.status == "COMPLETED"
    assert task.assigned_agent_id in {"planner-1", "backup-1"}
    assert runtime.shared_memory_manager.read("mission-1", "swarm", "plan").endswith(":draft")


def test_collaboration_manager_delegates_swarm_formation():
    runtime = DistributedRuntime()
    runtime.register_agent(
        SwarmAgent("planner"),
        [AgentCapability("plan")],
        agent_id="planner-1",
    )

    swarm = runtime.collaboration_manager.form_swarm("collab swarm", ["plan"])

    assert swarm.members == ["planner-1"]
    assert runtime.swarm_manager.swarm(swarm.swarm_id) is swarm


def test_swarm_manager_supports_protocol_backed_event_bus():
    registry = AgentRegistry()
    event_bus = EventBus(protocol=AgentProtocol())
    registry.register(SwarmAgent("planner"), [AgentCapability("plan")], agent_id="planner-1")
    manager = SwarmManager(registry=registry, event_bus=event_bus)

    swarm = manager.form_swarm("protocol swarm", ["plan"])

    assert swarm.members == ["planner-1"]
    assert [message.event_type for message in event_bus.history] == [
        "swarm.leader.elected",
        "swarm.formed",
    ]


def test_swarm_manager_lists_swarms_and_rejects_unknown_swarm():
    manager = SwarmManager()
    swarm = manager.form_swarm("empty swarm", [])

    assert manager.swarms() == [swarm]
    try:
        manager.allocate_task("missing", "plan", {})
    except KeyError as exc:
        assert "Unknown swarm" in str(exc)
    else:
        raise AssertionError("Expected missing swarm allocation to fail.")
