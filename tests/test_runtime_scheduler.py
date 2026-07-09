from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRegistry, RuntimeScheduler


class RecordingAgent(Agent):
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self.calls = calls

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(f"{self.name}:{context['task']}")
        return {**context, "handled_by": self.name}


class FailingAgent(Agent):
    name = "failing"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(f"failed {context['task']}")


def test_runtime_scheduler_dispatches_to_agent_by_capability():
    calls: list[str] = []
    registry = AgentRegistry()
    registry.register(
        RecordingAgent("planner", calls),
        [AgentCapability("plan")],
        agent_id="planner-1",
    )
    scheduler = RuntimeScheduler(registry)

    task = scheduler.dispatch("plan", {"task": "build"})

    assert task.status == "COMPLETED"
    assert task.agent_id == "planner-1"
    assert task.result == {"task": "build", "handled_by": "planner"}
    assert calls == ["planner:build"]
    assert scheduler.history == [task]


def test_runtime_scheduler_selects_less_busy_matching_agent_instance():
    calls: list[str] = []
    registry = AgentRegistry()
    first = registry.register(
        RecordingAgent("executor-a", calls),
        [AgentCapability("execute")],
        agent_id="executor-a",
        agent_type="executor",
    )
    registry.register(
        RecordingAgent("executor-b", calls),
        [AgentCapability("execute")],
        agent_id="executor-b",
        agent_type="executor",
    )
    first.active_tasks = 2
    scheduler = RuntimeScheduler(registry)

    task = scheduler.dispatch("execute", {"task": "run"}, agent_type="executor")

    assert task.agent_id == "executor-b"
    assert task.result["handled_by"] == "executor-b"
    assert first.active_tasks == 2


def test_runtime_scheduler_records_agent_failures_without_leaking_active_tasks():
    registry = AgentRegistry()
    registration = registry.register(
        FailingAgent(),
        [AgentCapability("execute")],
        agent_id="failing-1",
    )
    scheduler = RuntimeScheduler(registry)

    task = scheduler.dispatch("execute", {"task": "bad"})

    assert task.status == "FAILED"
    assert task.error == "failed bad"
    assert task.result is None
    assert registration.active_tasks == 0


def test_runtime_scheduler_raises_when_no_agent_supports_capability():
    scheduler = RuntimeScheduler(AgentRegistry())

    try:
        scheduler.dispatch(AgentCapability("reflect"), {"task": "review"})
    except RuntimeError as exc:
        assert str(exc) == "No registered agent supports capability: reflect"
    else:
        raise AssertionError("Expected missing capability dispatch to fail.")


def test_runtime_scheduler_dispatches_many_tasks():
    calls: list[str] = []
    registry = AgentRegistry()
    registry.register(
        RecordingAgent("memory", calls),
        [AgentCapability("remember")],
        agent_id="memory-1",
    )
    scheduler = RuntimeScheduler(registry)

    tasks = scheduler.dispatch_many(
        [
            ("remember", {"task": "one"}),
            ("remember", {"task": "two"}),
        ]
    )

    assert [task.status for task in tasks] == ["COMPLETED", "COMPLETED"]
    assert [task.result["handled_by"] for task in tasks if task.result] == [
        "memory",
        "memory",
    ]
    assert calls == ["memory:one", "memory:two"]
