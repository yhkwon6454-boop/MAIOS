from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRegistry
from maios.agents.swarm import SwarmManager


class DistributionAgent(Agent):
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self.calls = calls

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        task = str(context.get("task"))
        self.calls.append(f"{self.name}:{task}")
        return {"output": f"{self.name}:{task}"}


def test_swarm_task_distribution_uses_least_loaded_agent():
    calls: list[str] = []
    registry = AgentRegistry()
    busy = registry.register(
        DistributionAgent("busy", calls),
        [AgentCapability("execute")],
        agent_id="busy",
    )
    registry.register(
        DistributionAgent("idle", calls),
        [AgentCapability("execute")],
        agent_id="idle",
    )
    busy.active_tasks = 3
    manager = SwarmManager(registry=registry)
    swarm = manager.form_swarm("distribution swarm", ["execute"])

    task = manager.allocate_task(swarm.swarm_id, "execute", {"task": "run"})

    assert task.status == "COMPLETED"
    assert task.assigned_agent_id == "idle"
    assert calls == ["idle:run"]


def test_swarm_distributes_multiple_tasks_and_tracks_history():
    calls: list[str] = []
    registry = AgentRegistry()
    registry.register(
        DistributionAgent("executor", calls),
        [AgentCapability("execute")],
        agent_id="executor-1",
    )
    manager = SwarmManager(registry=registry)
    swarm = manager.form_swarm("distribution swarm", ["execute"])

    tasks = manager.distribute_tasks(
        swarm.swarm_id,
        [
            ("execute", {"task": "one"}),
            ("execute", {"task": "two"}),
        ],
    )

    assert [task.status for task in tasks] == ["COMPLETED", "COMPLETED"]
    assert [task.task_id for task in swarm.tasks] == [task.task_id for task in tasks]
    assert calls == ["executor:one", "executor:two"]


def test_swarm_task_distribution_fails_without_capable_agent_or_replacement():
    registry = AgentRegistry()
    registry.register(
        DistributionAgent("planner", []),
        [AgentCapability("plan")],
        agent_id="planner-1",
    )
    manager = SwarmManager(registry=registry)
    swarm = manager.form_swarm("distribution swarm", ["plan"])

    task = manager.allocate_task(swarm.swarm_id, "execute", {"task": "run"})

    assert task.status == "FAILED"
    assert task.error == "No swarm agent can handle capability: execute"
