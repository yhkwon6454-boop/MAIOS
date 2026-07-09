from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from maios.adapters.gpt_adapter import GPTAdapter, LLMClient
from maios.agents import MemoryAgent, RuntimeOrchestrator
from maios.agents.runtime_orchestrator import MultiAgentRuntimeResult
from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge.store import KnowledgeStore
from maios.reflection import ImprovementReport, ReflectionEngine
from maios.runtime.models import Mission, MissionType, Priority, QAResult, Status
from maios.runtime.plan import Plan


@dataclass
class MissionResult:
    goal: str
    mission: Mission
    plan: Plan
    memory_context: dict[str, str]
    model_output: str
    task_outputs: list[str]
    execution_result: dict
    qa_result: QAResult
    reflection_report: ImprovementReport | None
    final_output: str
    status: Status
    knowledge_count: int


class MAIOSCore:
    """Top-level MAIOS operating-system core facade."""

    def __init__(
        self,
        knowledge_store: KnowledgeStore | None = None,
        memory_kernel: MemoryKernel | None = None,
        gpt_adapter: GPTAdapter | None = None,
        reflection_engine: ReflectionEngine | None = None,
        orchestrator: RuntimeOrchestrator | None = None,
    ) -> None:
        self.knowledge_store = knowledge_store or KnowledgeStore()
        self.memory_kernel = memory_kernel or MemoryKernel(knowledge_store=self.knowledge_store)
        self.gpt_adapter = gpt_adapter or GPTAdapter(memory_kernel=self.memory_kernel)
        if getattr(self.gpt_adapter, "memory_kernel", None) is None:
            self.gpt_adapter.memory_kernel = self.memory_kernel

        self.reflection_engine = reflection_engine or ReflectionEngine(self.knowledge_store)
        self.orchestrator = orchestrator or RuntimeOrchestrator(
            memory_agent=MemoryAgent(self.memory_kernel),
            gpt_adapter=self.gpt_adapter,
            reflection_engine=self.reflection_engine,
            knowledge_store=self.knowledge_store,
        )

    @classmethod
    def with_json_store(
        cls,
        path: str | Path,
        client: LLMClient | None = None,
    ) -> MAIOSCore:
        knowledge_store = KnowledgeStore(path)
        memory_kernel = MemoryKernel(knowledge_store=knowledge_store)
        return cls(
            knowledge_store=knowledge_store,
            memory_kernel=memory_kernel,
            gpt_adapter=GPTAdapter(client=client, memory_kernel=memory_kernel),
            reflection_engine=ReflectionEngine(knowledge_store),
        )

    def run(self, goal: str) -> MissionResult:
        mission = self._create_mission(goal)
        runtime_result = self.orchestrator.run(mission)
        return self._to_mission_result(goal, runtime_result)

    def _create_mission(self, goal: str) -> Mission:
        return Mission(
            title=goal.strip() or "Untitled Goal",
            objective=goal.strip(),
            mission_type=MissionType.GENERAL,
            priority=Priority.NORMAL,
            expected_output="brief",
        )

    def _to_mission_result(
        self,
        goal: str,
        runtime_result: MultiAgentRuntimeResult,
    ) -> MissionResult:
        return MissionResult(
            goal=goal,
            mission=runtime_result.mission,
            plan=runtime_result.plan,
            memory_context=runtime_result.memory_context,
            model_output=runtime_result.model_output,
            task_outputs=runtime_result.task_outputs or [],
            execution_result=runtime_result.execution_result,
            qa_result=runtime_result.qa_result,
            reflection_report=runtime_result.reflection_report,
            final_output=runtime_result.final_output,
            status=runtime_result.mission.status,
            knowledge_count=self.knowledge_store.count(),
        )


def run(goal: str) -> MissionResult:
    return MAIOSCore().run(goal)
