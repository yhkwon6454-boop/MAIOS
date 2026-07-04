import maios
from maios.adapters.gpt_adapter import GPTAdapter
from maios.core import MAIOSCore, MissionResult
from maios.knowledge.store import KnowledgeStore
from maios.runtime.models import Status


class FakeClient:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return f"core output {len(self.prompts)}"


def test_maios_core_runs_complete_operating_system_pipeline():
    client = FakeClient()
    core = MAIOSCore(gpt_adapter=GPTAdapter(client=client))

    result = core.run("Build a core mission result.")

    assert isinstance(result, MissionResult)
    assert result.goal == "Build a core mission result."
    assert result.status == Status.COMPLETED
    assert result.mission.objective == "Build a core mission result."
    assert result.plan.objective == "Build a core mission result."
    assert result.model_output == "core output 4"
    assert len(result.task_outputs) == 4
    assert result.execution_result["status"] == "EXECUTED"
    assert result.qa_result.score == 100
    assert result.reflection_report is not None
    assert result.reflection_report.success
    assert result.knowledge_count >= 1
    assert len(client.prompts) == 4


def test_maios_run_public_api_returns_mission_result():
    result = maios.run("Run public MAIOS API.")

    assert isinstance(result, MissionResult)
    assert result.status == Status.COMPLETED
    assert result.final_output.startswith("# Multi-Agent Runtime Output")
    assert result.reflection_report is not None


def test_maios_core_shares_knowledge_between_reflection_and_memory(tmp_path):
    client = FakeClient()
    core = MAIOSCore.with_json_store(tmp_path / "knowledge.json", client=client)

    first = core.run("Capture reusable reflection knowledge.")
    context = core.memory_kernel.retrieve_context(first.reflection_report.report_id)

    assert first.reflection_report.report_id in context["retrieved_memory"]
    assert KnowledgeStore(tmp_path / "knowledge.json").exists(first.reflection_report.report_id)


def test_maios_core_allows_injected_components():
    store = KnowledgeStore()
    client = FakeClient()
    adapter = GPTAdapter(client=client)
    core = MAIOSCore(knowledge_store=store, gpt_adapter=adapter)

    result = core.run("Use injected components.")

    assert result.knowledge_count == store.count()
    assert adapter.memory_kernel is core.memory_kernel
