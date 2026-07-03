from __future__ import annotations

from maios.adapters.dummy_adapter import DummyModelAdapter
from maios.kernel.cognitive_kernel import CognitiveKernel
from maios.kernel.quality_kernel import QualityKernel
from maios.knowledge.store import InMemoryKnowledgeStore
from maios.runtime.models import ExecutionResult, Mission, Status


class ExecutiveKernel:
    """
    MAIOS의 최상위 실행 통제 계층.
    Mission → Process → Packet → Adapter → QA → Output 순으로 실행한다.
    """

    def __init__(self) -> None:
        self.cognitive_kernel = CognitiveKernel()
        self.quality_kernel = QualityKernel()
        self.knowledge_store = InMemoryKnowledgeStore()
        self.model_adapter = DummyModelAdapter()

    def run(self, mission: Mission) -> ExecutionResult:
        mission.status = Status.RUNNING

        processes = self.cognitive_kernel.build_processes(mission)
        packets = self.cognitive_kernel.build_packets(mission, processes)

        packet_outputs: list[str] = []

        for packet in packets:
            memory_context = self.knowledge_store.retrieve(packet.required_memory)
            output = self.model_adapter.execute(packet, memory_context)
            packet_outputs.append(output)

        qa_result = self.quality_kernel.evaluate(packet_outputs)
        final_output = self._compose_output(mission, packet_outputs, qa_result)

        mission.status = qa_result.status
        self.knowledge_store.store(mission.title, final_output)

        return ExecutionResult(
            mission=mission,
            processes=processes,
            packets=packets,
            packet_outputs=packet_outputs,
            qa_result=qa_result,
            final_output=final_output,
        )

    def _compose_output(self, mission: Mission, outputs: list[str], qa_result) -> str:
        sections = [
            f"# MAIOS Output: {mission.title}",
            "",
            f"## Objective",
            mission.objective,
            "",
            "## Result",
            "\n\n".join(outputs),
            "",
            "## QA",
            f"- Status: {qa_result.status.value}",
            f"- Score: {qa_result.score}",
        ]

        if qa_result.issues:
            sections.append("- Issues:")
            sections.extend([f"  - {issue}" for issue in qa_result.issues])

        return "\n".join(sections)
