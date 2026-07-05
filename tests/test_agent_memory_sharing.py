from __future__ import annotations

from typing import Any

from maios.agents import (
    Agent,
    AgentCapability,
    AgentRegistry,
    CollaborationManager,
    SharedMemoryManager,
)


class MemoryAwareAgent(Agent):
    def __init__(self, name: str, output_key: str, output: str) -> None:
        self.name = name
        self.output_key = output_key
        self.output = output
        self.seen_context: dict[str, Any] = {}

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self.seen_context = context
        return {
            "output": self.output,
            "shared_memory": {self.output_key: self.output},
        }


def test_collaboration_manager_uses_shared_memory_manager_workspace():
    registry = AgentRegistry()
    shared_memory = SharedMemoryManager()
    planner = MemoryAwareAgent("planner", "plan", "plan ready")
    executor = MemoryAwareAgent("executor", "execution", "done")
    registry.register(planner, [AgentCapability("plan")], agent_id="planner-1")
    registry.register(executor, [AgentCapability("execute")], agent_id="executor-1")
    manager = CollaborationManager(
        registry,
        shared_memory_manager=shared_memory,
        mission_id="mission-1",
    )

    manager.remember("goal", "ship")
    manager.execute_pipeline(
        [
            ("plan", {"task": "draft"}),
            ("execute", {"task": "run"}),
        ]
    )

    assert planner.seen_context["shared_memory"] == {"goal": "ship"}
    assert executor.seen_context["shared_memory"]["plan"] == "plan ready"
    assert executor.seen_context["mission_id"] == "mission-1"
    assert executor.seen_context["shared_memory_manager"] is shared_memory
    assert shared_memory.read("mission-1", "collaboration", "execution") == "done"


def test_collaboration_manager_records_shared_memory_versions_from_agents():
    registry = AgentRegistry()
    shared_memory = SharedMemoryManager()
    first = MemoryAwareAgent("first", "status", "draft")
    second = MemoryAwareAgent("second", "status", "final")
    registry.register(first, [AgentCapability("first")], agent_id="first-1")
    registry.register(second, [AgentCapability("second")], agent_id="second-1")
    manager = CollaborationManager(
        registry,
        shared_memory_manager=shared_memory,
        mission_id="mission-1",
    )

    manager.execute_pipeline(
        [
            ("first", {"task": "one"}),
            ("second", {"task": "two"}),
        ]
    )

    versions = shared_memory.versions("mission-1", "status")
    assert [version.value for version in versions] == ["draft", "final"]
    assert [version.agent_id for version in versions] == ["first-1", "second-1"]
    assert manager.recall("status") == "final"


def test_collaboration_manager_preserves_legacy_shared_memory_dict():
    registry = AgentRegistry()
    shared_memory = SharedMemoryManager()
    registry.register(
        MemoryAwareAgent("planner", "plan", "plan ready"),
        [AgentCapability("plan")],
        agent_id="planner-1",
    )
    manager = CollaborationManager(
        registry,
        shared_memory_manager=shared_memory,
        mission_id="mission-1",
    )

    task = manager.delegate("plan", {"task": "draft"})

    assert task.status == "COMPLETED"
    assert manager.shared_memory["plan"] == "plan ready"
    assert manager.recall("plan") == "plan ready"
