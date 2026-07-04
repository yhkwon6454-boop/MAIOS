from maios.adapters.gpt_adapter import GPTAdapter
from maios.agents import RuntimeOrchestrator
from maios.knowledge.store import KnowledgeStore
from maios.reflection import ReflectionEngine
from maios.runtime.models import Mission, QAResult, Status


class FakeClient:
    def __init__(self, outputs=None):
        self.outputs = list(outputs or ["ok", "ok", "ok", "ok"])
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        if self.outputs:
            return self.outputs.pop(0)
        return "ok"


def test_reflection_engine_reports_success_and_improvement_pattern():
    mission = Mission(title="Success Mission", objective="Complete cleanly.")
    qa_result = QAResult(status=Status.COMPLETED, score=100)
    engine = ReflectionEngine()

    report = engine.analyze(
        mission=mission,
        qa_result=qa_result,
        execution_result={"status": "EXECUTED"},
        task_outputs=["done"],
    )

    assert report.success
    assert report.score == 100
    assert report.bottlenecks == []
    assert report.improvement_points == [
        "Preserve the current execution pattern for similar missions."
    ]
    assert "Success Mission" in report.summary


def test_reflection_engine_detects_failure_bottlenecks():
    mission = Mission(title="Failure Mission", objective="Find issues.")
    qa_result = QAResult(
        status=Status.NEEDS_REVISION,
        score=50,
        issues=["Output too short"],
    )
    engine = ReflectionEngine()

    report = engine.analyze(
        mission=mission,
        qa_result=qa_result,
        execution_result={"status": "FAILED"},
        task_outputs=[""],
    )

    assert not report.success
    assert "Quality status is NEEDS_REVISION." in report.bottlenecks
    assert "QA issue: Output too short" in report.bottlenecks
    assert "Task output is empty: 0" in report.bottlenecks
    assert "Executor did not report EXECUTED status." in report.bottlenecks
    assert "Improve output quality before marking the mission complete." in report.improvement_points
    assert "Add validation before accepting empty model outputs." in report.improvement_points


def test_reflection_engine_stores_report_in_knowledge_store(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    mission = Mission(title="Stored Reflection", objective="Store report.")
    qa_result = QAResult(status=Status.COMPLETED, score=90)
    engine = ReflectionEngine(store)

    report = engine.analyze(mission, qa_result, {"status": "EXECUTED"}, ["done"])
    stored = store.get(report.report_id)

    assert stored is not None
    assert stored.document_id == report.report_id
    assert stored.metadata["memory_type"] == "reflection"
    assert stored.metadata["mission_id"] == mission.mission_id
    assert "Reflection Report" in stored.content


def test_runtime_orchestrator_invokes_reflection_engine(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    orchestrator = RuntimeOrchestrator(
        gpt_adapter=GPTAdapter(FakeClient()),
        knowledge_store=store,
    )
    mission = Mission(title="Runtime Reflection", objective="Reflect after execution.")

    result = orchestrator.run(mission)

    assert result.reflection_report is not None
    assert result.context["reflection_report"] == result.reflection_report
    assert result.reflection_report.mission_id == mission.mission_id
    assert store.exists(result.reflection_report.report_id)


def test_reflection_results_become_future_memory_context(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    orchestrator = RuntimeOrchestrator(
        gpt_adapter=GPTAdapter(FakeClient()),
        knowledge_store=store,
    )
    first = Mission(title="Alpha Reflection", objective="Complete alpha mission.")

    first_result = orchestrator.run(first)
    future_context = orchestrator.memory_agent.memory_kernel.retrieve_context(
        "Alpha Reflection",
    )

    assert first_result.reflection_report.report_id in future_context["retrieved_memory"]
    assert "memory_summary" in future_context
