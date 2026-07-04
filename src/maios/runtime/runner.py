from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from maios.adapters.dummy_adapter import DummyModelAdapter
from maios.kernel.executive_kernel import ExecutiveKernel
from maios.kernel.memory_kernel import MemoryKernel
from maios.kernel.quality_kernel import QualityKernel
from maios.planner.mission_planner import MissionPlanner
from maios.reasoning import ReasoningEngine
from maios.runtime.models import ExecutionResult, Mission, Status
from maios.runtime.plan import Plan
from maios.scheduler.mission_scheduler import MissionScheduler
from maios.tools import ToolRegistry


class RuntimeRunner:
    """Runtime pipeline that composes planning, memory, reasoning, and QA."""

    def __init__(
        self,
        mission_planner: MissionPlanner | None = None,
        memory_kernel: MemoryKernel | None = None,
        adapter: Any | None = None,
        reasoning_engine: ReasoningEngine | None = None,
        tool_registry: ToolRegistry | None = None,
        executive_kernel: ExecutiveKernel | None = None,
        quality_kernel: QualityKernel | None = None,
        scheduler: MissionScheduler | None = None,
    ) -> None:
        self.mission_planner = mission_planner or MissionPlanner()
        self.memory_kernel = memory_kernel or MemoryKernel()
        self.adapter = adapter or DummyModelAdapter()
        self.tool_registry = tool_registry or ToolRegistry()
        self.reasoning_engine = reasoning_engine or ReasoningEngine(
            self.adapter,
            self.tool_registry,
        )
        self.executive_kernel = executive_kernel or ExecutiveKernel()
        self.quality_kernel = quality_kernel or QualityKernel()
        self.scheduler = scheduler or MissionScheduler()

    def run(self, mission: Mission, output_dir: str | Path = "outputs") -> ExecutionResult:
        mission.status = Status.RUNNING
        self._prepare_mission(mission)

        tree = self.scheduler.schedule(mission)
        packets = tree.flatten_packets()

        packet_outputs: list[str] = []
        for packet in packets:
            memory_context = self._build_memory_context(packet.required_memory)
            packet.status = Status.RUNNING
            reasoning_result = self.reasoning_engine.execute(packet, memory_context)
            packet.status = Status.COMPLETED
            packet_outputs.append(reasoning_result.final_answer)
            self.memory_kernel.remember_long_term(
                reasoning_result.final_answer,
                {
                    "mission_id": mission.mission_id,
                    "packet_id": packet.packet_id,
                    "memory_type": "packet_output",
                },
            )

        qa_result = self.quality_kernel.evaluate(packet_outputs)
        mission.status = qa_result.status

        tree_dict = tree.to_dict()
        final_output = self._compose_output(mission, tree_dict, packet_outputs, qa_result)
        self._save_outputs(mission, tree_dict, final_output, output_dir)
        self.memory_kernel.remember_long_term(
            final_output,
            {
                "mission_id": mission.mission_id,
                "title": mission.title,
                "memory_type": "final_output",
            },
        )

        return ExecutionResult(
            mission=mission,
            processes=[node.process for node in tree.root_nodes],
            packets=packets,
            packet_outputs=packet_outputs,
            qa_result=qa_result,
            final_output=final_output,
        )

    def _prepare_mission(self, mission: Mission) -> None:
        mission_plan = self.mission_planner.analyze(mission.objective)
        execution_plan = Plan(
            objective=mission_plan.intent,
            tasks=mission_plan.tasks,
            risk=mission_plan.risk,
            priority=mission_plan.priority,
            output=mission.expected_output,
        )
        self.executive_kernel.execute(execution_plan)
        self.memory_kernel.remember_short_term(mission.objective)

    def _build_memory_context(self, memory_keys: list[str]) -> dict[str, str]:
        context: dict[str, str] = {}

        for key in memory_keys:
            documents = self.memory_kernel.retrieve(key, top_k=3)
            if documents:
                context[key] = "\n".join(
                    document.content if hasattr(document, "content") else str(document)
                    for document in documents
                )

        return context

    def _compose_output(self, mission: Mission, tree_dict: dict, outputs: list[str], qa_result) -> str:
        return "\n".join(
            [
                f"# MAIOS Runtime Output: {mission.title}",
                "",
                "## Objective",
                mission.objective,
                "",
                "## Cognitive Process Tree",
                "```json",
                json.dumps(tree_dict, ensure_ascii=False, indent=2),
                "```",
                "",
                "## Packet Outputs",
                "\n\n".join(outputs),
                "",
                "## QA Result",
                f"- Status: {qa_result.status.value}",
                f"- Score: {qa_result.score}",
                *[f"- Issue: {issue}" for issue in qa_result.issues],
            ]
        )

    def _save_outputs(self, mission: Mission, tree_dict: dict, final_output: str, output_dir: str | Path) -> None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        (output_dir / f"{mission.mission_id}.md").write_text(final_output, encoding="utf-8")
        (output_dir / f"{mission.mission_id}.tree.json").write_text(
            json.dumps(tree_dict, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
