from dataclasses import dataclass
from time import sleep

from maios.autonomous import MAIOSAgent, MissionScheduler
from maios.core import MissionResult
from maios.reflection import ImprovementReport
from maios.runtime.models import Mission, QAResult, Status
from maios.runtime.plan import Plan


@dataclass
class FakeCore:
    calls: list[str]
    delay: float = 0.0

    def run(self, goal: str) -> MissionResult:
        if self.delay:
            sleep(self.delay)
        self.calls.append(goal)
        mission = Mission(title=goal, objective=goal, status=Status.COMPLETED)
        qa_result = QAResult(status=Status.COMPLETED, score=100)
        return MissionResult(
            goal=goal,
            mission=mission,
            plan=Plan(objective=goal),
            memory_context={},
            model_output=f"model:{goal}",
            task_outputs=[f"task:{goal}"],
            execution_result={"status": "EXECUTED"},
            qa_result=qa_result,
            reflection_report=ImprovementReport(
                mission_id=mission.mission_id,
                success=True,
                score=100,
                summary="ok",
            ),
            final_output=f"final:{goal}",
            status=Status.COMPLETED,
            knowledge_count=1,
        )


def test_mission_scheduler_queues_and_persists_history(tmp_path):
    scheduler = MissionScheduler(tmp_path / "history.json")

    record = scheduler.submit("goal one")
    running = scheduler.get_next(timeout=0)

    assert running.mission_id == record.mission_id
    assert running.status == "RUNNING"

    result = FakeCore([]).run("goal one")
    scheduler.complete(running, result)

    loaded = MissionScheduler(tmp_path / "history.json")
    history = loaded.history()
    assert len(history) == 1
    assert history[0].goal == "goal one"
    assert history[0].status == "COMPLETED"


def test_maios_agent_runs_pending_goals_synchronously():
    calls = []
    agent = MAIOSAgent(core=FakeCore(calls))
    first = agent.submit_goal("alpha")
    second = agent.submit_goal("beta")

    records = agent.run_pending()

    assert [record.mission_id for record in records] == [
        first.mission_id,
        second.mission_id,
    ]
    assert calls == ["alpha", "beta"]
    assert all(record.status == "COMPLETED" for record in records)
    assert records[0].result.final_output == "final:alpha"


def test_maios_agent_background_execution():
    calls = []
    agent = MAIOSAgent(core=FakeCore(calls), max_workers=1)
    record = agent.submit_goal("background")

    agent.start_background()
    agent.wait_until_idle()
    agent.stop_background()

    completed = agent.scheduler.get(record.mission_id)
    assert completed.status == "COMPLETED"
    assert completed.result.goal == "background"
    assert calls == ["background"]


def test_maios_agent_supports_multiple_concurrent_missions():
    calls = []

    def core_factory():
        return FakeCore(calls, delay=0.01)

    agent = MAIOSAgent(core_factory=core_factory, max_workers=3)
    records = [agent.submit_goal(f"goal {index}") for index in range(5)]

    agent.start_background()
    agent.wait_until_idle()
    agent.stop_background()

    completed = [agent.scheduler.get(record.mission_id) for record in records]
    assert sorted(calls) == [f"goal {index}" for index in range(5)]
    assert all(record.status == "COMPLETED" for record in completed)


def test_maios_agent_records_failures():
    class FailingCore:
        def run(self, goal):
            raise RuntimeError(f"failed: {goal}")

    agent = MAIOSAgent(core=FailingCore())
    record = agent.submit_goal("bad goal")

    agent.run_pending()

    failed = agent.scheduler.get(record.mission_id)
    assert failed.status == "FAILED"
    assert failed.error == "failed: bad goal"
