import json

from maios.reasoning import ReasoningEngine
from maios.runtime.models import CognitivePacket
from maios.tools import BaseTool, ToolRegistry, ToolResult


class SequenceModelAdapter:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def execute(self, packet, memory_context):
        self.calls.append((packet, memory_context))
        return self.responses.pop(0)


class AddTool(BaseTool):
    name = "add"
    description = "Add two numbers."

    def execute(self, input_data):
        value = input_data["a"] + input_data["b"]
        return ToolResult(success=True, output=str(value), metadata={"value": value})


def test_reasoning_engine_routes_tool_and_returns_final_answer():
    registry = ToolRegistry()
    registry.register(AddTool())
    model = SequenceModelAdapter(
        [
            json.dumps(
                {
                    "type": "tool",
                    "reasoning": "Need arithmetic.",
                    "tool": "add",
                    "input": {"a": 2, "b": 3},
                }
            ),
            json.dumps({"type": "final", "final_answer": "The answer is 5."}),
        ]
    )
    engine = ReasoningEngine(model, registry)
    packet = CognitivePacket(process_id="P-1", instruction="What is 2 + 3?")

    result = engine.execute(packet, {"context": "math"})

    assert result.completed
    assert result.iterations == 2
    assert result.final_answer == "The answer is 5."
    assert [step.phase for step in result.steps] == [
        "reasoning",
        "tool",
        "observation",
        "final_answer",
    ]
    assert result.steps[1].tool_name == "add"
    assert result.steps[1].tool_input == {"a": 2, "b": 3}
    assert result.steps[2].observation.output == "5"
    assert model.calls[0][1] == {"context": "math"}


def test_reasoning_engine_includes_observation_in_next_prompt():
    registry = ToolRegistry()
    registry.register(AddTool())
    model = SequenceModelAdapter(
        [
            '{"tool": "add", "input": {"a": 7, "b": 4}, "reasoning": "calculate"}',
            '{"final_answer": "11"}',
        ]
    )
    engine = ReasoningEngine(model, registry)
    packet = CognitivePacket(process_id="P-1", instruction="Add numbers.")

    result = engine.execute(packet)

    assert result.final_answer == "11"
    second_prompt = model.calls[1][0].instruction
    assert "Observation: 11" in second_prompt
    assert "Available tools: add" in second_prompt


def test_reasoning_engine_treats_plain_text_as_final_answer():
    model = SequenceModelAdapter(["Plain final answer."])
    engine = ReasoningEngine(model, ToolRegistry())
    packet = CognitivePacket(process_id="P-1", instruction="Answer directly.")

    result = engine.execute(packet)

    assert result.completed
    assert result.iterations == 1
    assert result.final_answer == "Plain final answer."
    assert result.steps[0].phase == "final_answer"


def test_reasoning_engine_records_missing_tool_observation():
    model = SequenceModelAdapter(
        [
            '{"type": "tool", "tool": "missing", "input": {}, "reasoning": "try tool"}',
            '{"type": "final", "final_answer": "Tool was unavailable."}',
        ]
    )
    engine = ReasoningEngine(model, ToolRegistry())
    packet = CognitivePacket(process_id="P-1", instruction="Use a tool.")

    result = engine.execute(packet)

    assert result.completed
    assert not result.steps[2].observation.success
    assert result.steps[2].observation.error == "Tool not found: missing"
    assert result.final_answer == "Tool was unavailable."


def test_reasoning_engine_stops_at_iteration_limit():
    registry = ToolRegistry()
    registry.register(AddTool())
    model = SequenceModelAdapter(
        [
            '{"type": "tool", "tool": "add", "input": {"a": 1, "b": 1}}',
            '{"type": "tool", "tool": "add", "input": {"a": 2, "b": 2}}',
        ]
    )
    engine = ReasoningEngine(model, registry, max_iterations=2)
    packet = CognitivePacket(process_id="P-1", instruction="Keep going.")

    result = engine.execute(packet)

    assert not result.completed
    assert result.iterations == 2
    assert result.final_answer == "Reasoning stopped before a final answer was produced."
