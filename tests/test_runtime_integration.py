import json

from maios.kernel.memory_kernel import MemoryKernel
from maios.runtime.loader import load_mission
from maios.runtime.models import Mission, MissionType, Status
from maios.runtime.runner import RuntimeRunner
from maios.tools import BaseTool, ToolRegistry, ToolResult


class SequenceModelAdapter:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def execute(self, packet, memory_context):
        self.calls.append((packet, memory_context))
        if self.responses:
            return self.responses.pop(0)
        return json.dumps({"type": "final", "final_answer": "fallback final"})


class CaptureTool(BaseTool):
    name = "capture"
    description = "Return a captured value."

    def __init__(self):
        self.inputs = []

    def execute(self, input_data):
        self.inputs.append(input_data)
        return ToolResult(success=True, output=f"captured:{input_data['value']}")


def test_runtime_runner_executes_default_pipeline(tmp_path):
    mission = Mission(
        title="Runtime Integration",
        objective="Produce an integrated mission output.",
        mission_type=MissionType.WRITING,
        expected_output="brief",
    )
    runner = RuntimeRunner()

    result = runner.run(mission, output_dir=tmp_path)

    assert result.mission.status == Status.COMPLETED
    assert len(result.packets) == 3
    assert len(result.packet_outputs) == 3
    assert result.qa_result.score == 100
    assert "# MAIOS Runtime Output: Runtime Integration" in result.final_output
    assert (tmp_path / f"{mission.mission_id}.md").exists()
    assert (tmp_path / f"{mission.mission_id}.tree.json").exists()
    assert len(runner.memory_kernel.session_memory) == 1
    assert len(runner.memory_kernel.long_term_memory) == 4


def test_runtime_runner_routes_reasoning_through_tool_registry(tmp_path):
    tool = CaptureTool()
    registry = ToolRegistry()
    registry.register(tool)
    model = SequenceModelAdapter(
        [
            json.dumps(
                {
                    "type": "tool",
                    "reasoning": "Need capture tool.",
                    "tool": "capture",
                    "input": {"value": "alpha"},
                }
            ),
            json.dumps({"type": "final", "final_answer": "Tool result handled."}),
            json.dumps({"type": "final", "final_answer": "Second packet."}),
            json.dumps({"type": "final", "final_answer": "Third packet."}),
        ]
    )
    mission = Mission(
        title="Tool Mission",
        objective="Use a tool during runtime.",
        mission_type=MissionType.GENERAL,
    )
    runner = RuntimeRunner(adapter=model, tool_registry=registry)

    result = runner.run(mission, output_dir=tmp_path)

    assert result.mission.status == Status.COMPLETED
    assert result.packet_outputs == [
        "Tool result handled.",
        "Second packet.",
        "Third packet.",
    ]
    assert tool.inputs == [{"value": "alpha"}]
    assert "Observation: captured:alpha" in model.calls[1][0].instruction


def test_runtime_runner_uses_memory_retrieval_context(tmp_path):
    model = SequenceModelAdapter(
        [
            json.dumps({"type": "final", "final_answer": "memory aware"}),
            json.dumps({"type": "final", "final_answer": "done"}),
            json.dumps({"type": "final", "final_answer": "final"}),
        ]
    )
    memory = MemoryKernel()
    memory.remember_short_term("mission context from memory")
    mission = Mission(
        title="Memory Mission",
        objective="Use memory.",
        mission_type=MissionType.GENERAL,
    )
    runner = RuntimeRunner(adapter=model, memory_kernel=memory)

    runner.run(mission, output_dir=tmp_path)

    first_memory_context = model.calls[0][1]
    assert "mission" in first_memory_context
    assert "mission context from memory" in first_memory_context["mission"]


def test_runtime_example_mission_loads_and_runs(tmp_path):
    mission = load_mission("examples/writing_project.yaml")
    runner = RuntimeRunner()

    result = runner.run(mission, output_dir=tmp_path)

    assert result.mission.status == Status.COMPLETED
    assert result.final_output
