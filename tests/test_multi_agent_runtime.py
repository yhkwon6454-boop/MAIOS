from maios.adapters.gpt_adapter import GPTAdapter
from maios.agents import (
    Agent,
    ExecutorAgent,
    MemoryAgent,
    PlannerAgent,
    RuntimeOrchestrator,
)
from maios.kernel.memory_kernel import MemoryKernel
from maios.runtime.models import Mission, Status


class FakeClient:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return "multi-agent model output"


class TraceAgent(Agent):
    def __init__(self, name, key):
        self.name = name
        self.key = key

    def execute(self, context):
        return {**context, self.key: True}


def test_planner_agent_creates_execution_plan():
    mission = Mission(title="Plan Mission", objective="Plan the mission.")
    context = PlannerAgent().execute({"mission": mission, "trace": []})

    assert context["mission_plan"].mission == "Plan the mission."
    assert context["execution_plan"].objective == "Plan the mission."
    assert len(context["execution_plan"].tasks) == 5


def test_memory_agent_records_and_retrieves_mission_memory():
    memory_kernel = MemoryKernel()
    agent = MemoryAgent(memory_kernel)
    mission = Mission(title="Memory Mission", objective="Remember mission context.")

    context = agent.execute({"mission": mission, "trace": []})

    assert memory_kernel.session_memory == ["Remember mission context."]
    assert "mission" in context["memory_context"]
    assert "Remember mission context." in context["memory_context"]["mission"]


def test_executor_agent_uses_execution_plan():
    mission = Mission(title="Execute Mission", objective="Execute.")
    context = PlannerAgent().execute({"mission": mission, "trace": []})
    context = ExecutorAgent().execute(context)

    assert context["execution_result"]["status"] == "EXECUTED"
    assert context["execution_result"]["objective"] == "Execute."


def test_runtime_orchestrator_executes_full_multi_agent_pipeline():
    client = FakeClient()
    adapter = GPTAdapter(client)
    orchestrator = RuntimeOrchestrator(gpt_adapter=adapter)
    mission = Mission(title="Orchestrated Mission", objective="Coordinate agents.")

    result = orchestrator.run(mission)

    assert result.mission.status == Status.COMPLETED
    assert result.model_output == "multi-agent model output"
    assert result.qa_result.score == 100
    assert result.execution_result["status"] == "EXECUTED"
    assert result.context["trace"] == [
        "planner",
        "memory",
        "gpt_adapter",
        "executor",
        "quality",
    ]
    assert "Mission: Orchestrated Mission" in client.prompts[0]
    assert "Coordinate agents." in client.prompts[0]


def test_runtime_orchestrator_accepts_injected_agents():
    client = FakeClient()
    orchestrator = RuntimeOrchestrator(
        planner_agent=TraceAgent("planner", "planned"),
        memory_agent=TraceAgent("memory", "memorized"),
        gpt_adapter=GPTAdapter(client),
        executor_agent=TraceAgent("executor", "executed"),
    )
    mission = Mission(title="Injected Mission", objective="Use injected agents.")
    initial_context = {
        "execution_plan": PlannerAgent().execute({"mission": mission, "trace": []})[
            "execution_plan"
        ],
        "memory_context": {},
        "execution_result": {"status": "EXECUTED"},
    }

    orchestrator.planner_agent.execute = lambda context: {
        **context,
        **initial_context,
        "planned": True,
    }

    result = orchestrator.run(mission)

    assert result.context["planned"]
    assert result.context["memorized"]
    assert result.context["executed"]
    assert result.context["trace"] == [
        "planner",
        "memory",
        "gpt_adapter",
        "executor",
        "quality",
    ]
