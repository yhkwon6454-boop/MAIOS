from dataclasses import dataclass

from maios.core import MissionResult
from maios.distributed import (
    DistributedRuntime,
    HealthMonitor,
    InMemoryTransport,
    MissionScheduler,
    NodeManager,
    TaskDispatcher,
)
from maios.reflection import ImprovementReport
from maios.runtime.models import Mission, QAResult, Status
from maios.runtime.plan import Plan


@dataclass
class FakeCore:
    name: str
    calls: list[str]

    def run(self, goal: str) -> MissionResult:
        self.calls.append(f"{self.name}:{goal}")
        mission = Mission(title=goal, objective=goal, status=Status.COMPLETED)
        return MissionResult(
            goal=goal,
            mission=mission,
            plan=Plan(objective=goal),
            memory_context={},
            model_output=f"{self.name} output",
            task_outputs=[f"{self.name} task"],
            execution_result={"status": "EXECUTED"},
            qa_result=QAResult(status=Status.COMPLETED, score=100),
            reflection_report=ImprovementReport(
                mission_id=mission.mission_id,
                success=True,
                score=100,
                summary="ok",
            ),
            final_output=f"{self.name}:{goal}",
            status=Status.COMPLETED,
            knowledge_count=1,
        )


def test_node_manager_registers_heartbeat_and_selects_least_loaded_node():
    manager = NodeManager()
    node_a = manager.register_node("a", capacity=1)
    node_b = manager.register_node("b", capacity=3)
    node_b.active_tasks = 1

    manager.heartbeat("a")

    assert manager.get("a") is node_a
    assert node_a.healthy
    assert manager.select_node() is node_b


def test_health_monitor_marks_stale_nodes_unhealthy():
    manager = NodeManager()
    node = manager.register_node("stale")
    node.last_heartbeat = 0
    monitor = HealthMonitor(manager, timeout_seconds=0.001)

    health = monitor.check()

    assert health == {"stale": False}
    assert not node.healthy


def test_task_dispatcher_executes_on_selected_node():
    calls = []
    manager = NodeManager()
    transport = InMemoryTransport()
    node = manager.register_node("node-a", capacity=1)
    transport.register_core("node-a", FakeCore("node-a", calls))
    dispatcher = TaskDispatcher(manager, transport)

    selected, result = dispatcher.dispatch("distributed goal")

    assert selected is node
    assert result.final_output == "node-a:distributed goal"
    assert calls == ["node-a:distributed goal"]
    assert node.active_tasks == 0


def test_mission_scheduler_tracks_queue_and_history():
    scheduler = MissionScheduler()

    mission = scheduler.submit("queued goal")
    next_mission = scheduler.next()

    assert next_mission is mission
    assert scheduler.pending_count() == 0
    scheduler.fail(mission, "no node")
    assert scheduler.get(mission.mission_id).status == "FAILED"
    assert scheduler.history() == [mission]


def test_distributed_runtime_executes_remote_mission():
    calls = []
    runtime = DistributedRuntime()
    runtime.register_node("node-a", core=FakeCore("node-a", calls))

    mission = runtime.execute_mission("remote goal")

    assert mission.status == "COMPLETED"
    assert mission.assigned_node == "node-a"
    assert mission.result.final_output == "node-a:remote goal"
    assert calls == ["node-a:remote goal"]


def test_distributed_runtime_load_balances_across_nodes():
    calls = []
    runtime = DistributedRuntime()
    node_a = runtime.register_node("node-a", core=FakeCore("node-a", calls), capacity=1)
    node_b = runtime.register_node("node-b", core=FakeCore("node-b", calls), capacity=3)
    node_b.active_tasks = 2

    first = runtime.execute_mission("first")
    node_a.active_tasks = 1
    second = runtime.execute_mission("second")

    assert first.assigned_node == "node-b"
    assert second.assigned_node == "node-b"
    assert "node-b:first" in calls
    assert "node-b:second" in calls


def test_distributed_runtime_fails_when_no_healthy_nodes_available():
    runtime = DistributedRuntime()
    runtime.register_node("node-a", core=FakeCore("node-a", []))
    runtime.node_manager.get("node-a").healthy = False

    mission = runtime.execute_mission("unassigned")

    assert mission.status == "FAILED"
    assert mission.error == "No healthy MAIOS nodes available."


def test_distributed_runtime_runs_pending_missions():
    calls = []
    runtime = DistributedRuntime()
    runtime.register_node("node-a", core=FakeCore("node-a", calls))
    first = runtime.submit_mission("one")
    second = runtime.submit_mission("two")

    missions = runtime.run_pending()

    assert [mission.mission_id for mission in missions] == [
        first.mission_id,
        second.mission_id,
    ]
    assert all(mission.status == "COMPLETED" for mission in missions)
    assert calls == ["node-a:one", "node-a:two"]
