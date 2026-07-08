from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRegistry
from maios.agents.swarm import SwarmManager


class FailingSwarmAgent(Agent):
    name = "failing"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("agent failed")


class RecoveryAgent(Agent):
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self.calls = calls

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(f"{self.name}:{context.get('task')}")
        return {
            "output": f"{self.name}:{context.get('task')}",
            "shared_memory": {"recovered_by": self.name},
        }


def test_swarm_replaces_failed_agent_and_retries_task():
    calls: list[str] = []
    registry = AgentRegistry()
    registry.register(FailingSwarmAgent(), [AgentCapability("execute")], agent_id="a-failing")
    registry.register(
        RecoveryAgent("backup", calls),
        [AgentCapability("execute")],
        agent_id="backup-1",
    )
    manager = SwarmManager(registry=registry, mission_id="mission-1")
    swarm = manager.form_swarm("recovery swarm", ["execute"], size=1)

    task = manager.allocate_task(swarm.swarm_id, "execute", {"task": "run"})

    assert task.status == "COMPLETED"
    assert task.assigned_agent_id == "a-failing"
    assert task.replacement_agent_id == "backup-1"
    assert "a-failing" in swarm.failed_agents
    assert "backup-1" in swarm.members
    assert calls == ["backup:run"]
    assert manager.shared_memory_manager.read("mission-1", "swarm", "recovered_by") == "backup"


def test_swarm_fails_task_when_no_replacement_is_available():
    registry = AgentRegistry()
    registry.register(FailingSwarmAgent(), [AgentCapability("execute")], agent_id="failing")
    manager = SwarmManager(registry=registry)
    swarm = manager.form_swarm("recovery swarm", ["execute"])

    task = manager.allocate_task(swarm.swarm_id, "execute", {"task": "run"})

    assert task.status == "FAILED"
    assert task.error == "agent failed"
    assert task.replacement_agent_id == ""


def test_swarm_marks_replacement_failure():
    registry = AgentRegistry()
    registry.register(FailingSwarmAgent(), [AgentCapability("execute")], agent_id="a-failing")
    registry.register(FailingSwarmAgent(), [AgentCapability("execute")], agent_id="b-failing")
    manager = SwarmManager(registry=registry)
    swarm = manager.form_swarm("recovery swarm", ["execute"], size=1)

    task = manager.allocate_task(swarm.swarm_id, "execute", {"task": "run"})

    assert task.status == "FAILED"
    assert task.replacement_agent_id == "b-failing"
    assert swarm.failed_agents == {"a-failing", "b-failing"}


def test_swarm_health_monitor_reports_failed_and_active_agents():
    registry = AgentRegistry()
    registry.register(FailingSwarmAgent(), [AgentCapability("execute")], agent_id="failed")
    registry.register(
        RecoveryAgent("healthy", []),
        [AgentCapability("execute")],
        agent_id="healthy",
    )
    manager = SwarmManager(registry=registry)
    swarm = manager.form_swarm("health swarm", ["execute"])
    manager.mark_failed(swarm.swarm_id, "failed")

    health = manager.monitor_health(swarm.swarm_id)

    assert health.healthy
    assert health.leader_id == "healthy"
    assert health.active_agents == ["healthy"]
    assert health.failed_agents == ["failed"]
    assert health.load_by_agent == {"healthy": 0}


def test_swarm_health_monitor_degrades_empty_swarm():
    manager = SwarmManager()
    swarm = manager.form_swarm("empty swarm", ["execute"])

    health = manager.monitor_health(swarm.swarm_id)

    assert not health.healthy
    assert swarm.status == "DEGRADED"
    assert health.active_agents == []
