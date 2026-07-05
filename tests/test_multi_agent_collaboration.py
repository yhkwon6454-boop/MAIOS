from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRegistry, CollaborationManager


class CollaborativeAgent(Agent):
    def __init__(self, name: str, output_key: str, output: str) -> None:
        self.name = name
        self.output_key = output_key
        self.output = output
        self.seen_memory: dict[str, Any] = {}

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self.seen_memory = dict(context.get("shared_memory", {}))
        return {
            self.output_key: self.output,
            "output": self.output,
            "shared_memory": {self.output_key: self.output},
        }


class ReviewAgent(Agent):
    def __init__(self, name: str, decision: str) -> None:
        self.name = name
        self.decision = decision

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"decision": self.decision, "output": self.decision}


def test_collaborative_execution_pipeline_shares_memory_between_agents():
    registry = AgentRegistry()
    planner = CollaborativeAgent("planner", "plan", "plan ready")
    executor = CollaborativeAgent("executor", "execution", "execution done")
    registry.register(planner, [AgentCapability("plan")], agent_id="planner-1")
    registry.register(executor, [AgentCapability("execute")], agent_id="executor-1")
    manager = CollaborationManager(registry)

    result = manager.execute_pipeline(
        [
            ("plan", {"task": "plan mission"}),
            ("execute", {"task": "execute mission"}),
        ]
    )

    assert [task.status for task in result.tasks] == ["COMPLETED", "COMPLETED"]
    assert executor.seen_memory["plan"] == "plan ready"
    assert result.shared_memory["plan"] == "plan ready"
    assert result.shared_memory["execution"] == "execution done"
    assert [agent.agent_id for agent in result.team] == ["planner-1", "executor-1"]


def test_collaborative_execution_pipeline_reports_conflicts():
    registry = AgentRegistry()
    registry.register(
        ReviewAgent("reviewer-a", "approve"),
        [AgentCapability("review")],
        agent_id="reviewer-a",
    )
    registry.register(
        ReviewAgent("reviewer-b", "reject"),
        [AgentCapability("second_review")],
        agent_id="reviewer-b",
    )
    manager = CollaborationManager(registry)

    result = manager.execute_pipeline(
        [
            ("review", {"task": "review"}),
            ("second_review", {"task": "review again"}),
        ]
    )

    assert len(result.conflicts) == 2
    assert {conflict.key for conflict in result.conflicts} == {"decision", "output"}
    assert manager.recall("decision") == "approve"


def test_collaboration_manager_keeps_backward_compatible_agent_execution_contract():
    registry = AgentRegistry()
    agent = CollaborativeAgent("memory", "context", "remembered")
    registry.register(agent, [AgentCapability("remember")], agent_id="memory-1")
    manager = CollaborationManager(registry)

    task = manager.delegate("remember", {"task": "load context"})

    assert task.result["context"] == "remembered"
    assert agent.seen_memory == {}
