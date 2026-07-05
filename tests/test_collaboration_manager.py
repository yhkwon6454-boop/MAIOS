from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRegistry, CollaborationManager


class TeamAgent(Agent):
    def __init__(self, name: str, output: str) -> None:
        self.name = name
        self.output = output

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            **context,
            "output": self.output,
            "shared_memory": {self.name: self.output},
        }


def test_collaboration_manager_forms_dynamic_teams_by_capability():
    registry = AgentRegistry()
    planner = registry.register(
        TeamAgent("planner", "plan"),
        [AgentCapability("plan")],
        agent_id="planner-1",
    )
    memory = registry.register(
        TeamAgent("memory", "context"),
        [AgentCapability("remember")],
        agent_id="memory-1",
    )
    registry.register(
        TeamAgent("executor", "done"),
        [AgentCapability("execute")],
        agent_id="executor-1",
    )
    manager = CollaborationManager(registry)

    team = manager.form_team(["plan", "remember"])

    assert team == [planner, memory]


def test_collaboration_manager_can_include_all_matching_instances():
    registry = AgentRegistry()
    first = registry.register(
        TeamAgent("memory-a", "a"),
        [AgentCapability("remember")],
        agent_id="memory-a",
        agent_type="memory",
    )
    second = registry.register(
        TeamAgent("memory-b", "b"),
        [AgentCapability("remember")],
        agent_id="memory-b",
        agent_type="memory",
    )
    manager = CollaborationManager(registry)

    assert manager.form_team(["remember"], include_all_instances=True) == [first, second]


def test_collaboration_manager_delegates_tasks_and_updates_shared_memory():
    registry = AgentRegistry()
    registry.register(
        TeamAgent("planner", "plan ready"),
        [AgentCapability("plan")],
        agent_id="planner-1",
    )
    manager = CollaborationManager(registry)
    manager.remember("goal", "ship")

    task = manager.delegate("plan", {"task": "draft"})

    assert task.status == "COMPLETED"
    assert task.agent_id == "planner-1"
    assert task.result["shared_memory"]["planner"] == "plan ready"
    assert task.context["shared_memory"] == {"goal": "ship"}
    assert manager.recall("planner") == "plan ready"
    assert manager.recall("plan") == "plan ready"


def test_collaboration_manager_detects_and_resolves_conflicts():
    manager = CollaborationManager()
    results = [
        {"agent_id": "a", "decision": "approve", "confidence": 0.8},
        {"agent_id": "b", "decision": "reject", "confidence": 0.8},
        {"agent_id": "c", "decision": "approve", "confidence": 0.8},
    ]

    conflicts = manager.detect_conflicts(results)
    resolved = manager.resolve_conflicts(conflicts)

    assert len(conflicts) == 1
    assert conflicts[0].key == "decision"
    assert resolved[0].resolved_value == "approve"
    assert resolved[0].strategy == "majority"
    assert manager.recall("decision") == "approve"


def test_collaboration_manager_supports_consensus_voting():
    manager = CollaborationManager()

    result = manager.vote(
        proposal="approve",
        votes={"planner": "approve", "memory": "approve", "executor": "reject"},
    )

    assert result.decision == "approve"
    assert result.approved
    assert not result.tie
    assert manager.recall("last_consensus") is result


def test_collaboration_manager_detects_tied_consensus():
    manager = CollaborationManager()

    result = manager.vote(
        proposal="approve",
        votes={"planner": "approve", "executor": "reject"},
    )

    assert result.decision == "approve"
    assert not result.approved
    assert result.tie


def test_collaboration_manager_handles_empty_votes():
    manager = CollaborationManager()

    result = manager.vote(proposal="approve", votes={})

    assert result.decision is None
    assert not result.approved
    assert result.votes == {}
