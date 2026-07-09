from maios.adapters.gpt_adapter import GPTAdapter
from maios.agents import RuntimeOrchestrator
from maios.planning import GoalManager, PriorityEngine, TaskDecomposer
from maios.runtime.models import Mission, Status


class FakeClient:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return f"output {len(self.prompts)}"


def test_task_decomposer_creates_executable_tasks():
    tasks = TaskDecomposer().decompose("Build a mission brief")

    assert len(tasks) == 4
    assert tasks[0].description == "Understand goal: Build a mission brief"
    assert all(task.status == "PENDING" for task in tasks)
    assert tasks[0].priority > tasks[-1].priority


def test_goal_manager_creates_goal_with_prioritized_tasks():
    manager = GoalManager()

    goal = manager.create_goal("Analyze mission")

    assert goal.status == "READY"
    assert goal.objective == "Analyze mission"
    assert len(goal.tasks) == 4
    assert goal.tasks[0].priority == 90


def test_priority_engine_reprioritizes_from_feedback():
    tasks = TaskDecomposer().decompose("Test feedback")
    low_task = tasks[-1]

    reordered = PriorityEngine().reprioritize(
        tasks,
        {low_task.task_id: "blocked, retry needed"},
    )

    assert reordered[0] is low_task
    assert low_task.priority == 100
    assert low_task.status == "PENDING"


def test_goal_manager_next_and_complete_task():
    manager = GoalManager()
    goal = manager.create_goal("Execute goal")

    task = manager.next_task(goal)
    assert task.status == "RUNNING"

    manager.complete_task(goal, task, feedback="done")

    assert task.status == "COMPLETED"
    assert task.priority == 40


def test_runtime_orchestrator_executes_dynamic_task_queue():
    client = FakeClient()
    orchestrator = RuntimeOrchestrator(gpt_adapter=GPTAdapter(client))
    mission = Mission(title="Autonomous Mission", objective="Plan autonomous work.")

    result = orchestrator.run(mission)

    assert result.mission.status == Status.COMPLETED
    assert len(result.task_outputs) == 4
    assert result.model_output == "output 4"
    assert len(client.prompts) == 4
    assert "Current task: Understand goal: Plan autonomous work." in client.prompts[0]
    assert all(task.status == "COMPLETED" for task in result.context["goal"].tasks)


def test_runtime_orchestrator_reprioritizes_failed_task_feedback():
    class EmptyThenSuccessClient:
        def __init__(self):
            self.prompts = []

        def generate(self, prompt):
            self.prompts.append(prompt)
            if len(self.prompts) == 1:
                return ""
            return "recovered"

    client = EmptyThenSuccessClient()
    orchestrator = RuntimeOrchestrator(gpt_adapter=GPTAdapter(client))
    mission = Mission(title="Feedback Mission", objective="Handle feedback.")

    result = orchestrator.run(mission)

    assert result.qa_result.score == 100
    assert "retry" in result.context["goal"].tasks[0].feedback
    assert len(result.task_outputs) == 5
