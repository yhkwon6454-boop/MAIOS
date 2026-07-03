from __future__ import annotations

from pathlib import Path
import json

from maios.adapters.dummy_adapter import DummyModelAdapter
from maios.kernel.quality_kernel import QualityKernel
from maios.knowledge.store import InMemoryKnowledgeStore
from maios.runtime.models import ExecutionResult, Mission, Status
from maios.scheduler.mission_scheduler import MissionScheduler


class RuntimeRunner:
    """
    Mission Scheduler 기반 실행 런타임.
    ExecutiveKernel의 초기 구현을 대체할 차세대 실행 경로다.
    """

    def __init__(self) -> None:
        self.scheduler = MissionScheduler()
        self.knowledge_store = InMemoryKnowledgeStore()
        self.adapter = DummyModelAdapter()
        self.quality_kernel = QualityKernel()

    def run(self, mission: Mission, output_dir: str | Path = "outputs") -> ExecutionResult:
        mission.status = Status.RUNNING
        tree = self.scheduler.schedule(mission)
        packets = tree.flatten_packets()

        packet_outputs: list[str] = []
        for packet in packets:
            memory_context = self.knowledge_store.retrieve(packet.required_memory)
            packet.status = Status.RUNNING
            output = self.adapter.execute(packet, memory_context)
            packet.status = Status.COMPLETED
            packet_outputs.append(output)

        qa_result = self.quality_kernel.evaluate(packet_outputs)
        mission.status = qa_result.status

        final_output = self._compose_output(mission, tree.to_dict(), packet_outputs, qa_result)
        self._save_outputs(mission, tree.to_dict(), final_output, output_dir)
        self.knowledge_store.store(mission.title, final_output)

        return ExecutionResult(
            mission=mission,
            processes=[node.process for node in tree.root_nodes],
            packets=packets,
            packet_outputs=packet_outputs,
            qa_result=qa_result,
            final_output=final_output,
        )

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
