from __future__ import annotations

from maios.adapters.gpt_adapter import GPTAdapter
from maios.agents import RuntimeOrchestrator
from maios.events import EventBus
from maios.runtime.models import Mission, Status


class FakeClient:
    def __init__(self) -> None:
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return f"message output {len(self.prompts)}"


def test_runtime_orchestrator_publishes_agent_messages_in_order():
    bus = EventBus()
    received = []
    bus.subscribe("*", received.append)
    client = FakeClient()
    orchestrator = RuntimeOrchestrator(
        gpt_adapter=GPTAdapter(client=client),
        event_bus=bus,
    )

    result = orchestrator.run(Mission(title="Messaging", objective="Run message bus."))

    event_types = [message.event_type for message in received]
    assert event_types[:5] == [
        "mission.started",
        "planner.started",
        "planner.completed",
        "memory.started",
        "memory.completed",
    ]
    assert "gpt.started" in event_types
    assert "gpt.completed" in event_types
    assert "executor.completed" in event_types
    assert "quality.completed" in event_types
    assert event_types[-1] == "mission.completed"
    assert result.mission.status == Status.COMPLETED
    assert result.context["trace"] == ["planner", "memory", "gpt_adapter", "executor", "quality"]
    assert bus.history == received


def test_runtime_orchestrator_event_payloads_include_stage_outputs():
    bus = EventBus()
    planner_messages = []
    quality_messages = []
    mission_messages = []
    bus.subscribe("planner.completed", planner_messages.append)
    bus.subscribe("quality.completed", quality_messages.append)
    bus.subscribe("mission.completed", mission_messages.append)

    result = RuntimeOrchestrator(
        gpt_adapter=GPTAdapter(client=FakeClient()),
        event_bus=bus,
    ).run(Mission(title="Payloads", objective="Inspect event payloads."))

    assert planner_messages[0].source == "planner"
    assert planner_messages[0].payload["plan"]["objective"] == "Inspect event payloads."
    assert quality_messages[0].source == "quality"
    assert quality_messages[0].payload["qa_result"]["score"] == 100
    assert mission_messages[0].payload == {
        "mission_id": result.mission.mission_id,
        "status": "COMPLETED",
        "qa_score": 100,
    }


def test_runtime_orchestrator_remains_backward_compatible_without_event_bus():
    result = RuntimeOrchestrator(gpt_adapter=GPTAdapter(client=FakeClient())).run(
        Mission(title="Compatible", objective="Keep old constructor working.")
    )

    assert result.mission.status == Status.COMPLETED
    assert result.final_output.startswith("# Multi-Agent Runtime Output")
