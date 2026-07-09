from __future__ import annotations

from maios.agents import Agent, AgentCapability
from maios.distributed import DistributedRuntime
from maios.kernel import SystemState


class NoopAgent(Agent):
    name = "noop"

    def execute(self, context):
        return {"output": "ok"}


def test_system_state_clamps_values_and_updates_from_outcomes():
    state = SystemState(
        active_missions=-1,
        healthy_nodes=-2,
        active_agents=-3,
        failed_agents=-4,
        failure_rate=2.0,
    )

    assert state.active_missions == 0
    assert state.healthy_nodes == 0
    assert state.active_agents == 0
    assert state.failed_agents == 0
    assert state.failure_rate == 1.0

    state.update_from_outcome({"status": "COMPLETED"})
    assert state.failure_rate == 0.95
    state.update_from_outcome({"status": "FAILED"})
    assert state.failure_rate == 1.0


def test_system_state_can_be_derived_from_distributed_runtime():
    runtime = DistributedRuntime()
    runtime.register_node("node-a")
    runtime.register_agent(NoopAgent(), [AgentCapability("plan")], agent_id="agent-1")
    runtime.submit_mission("queued")

    state = SystemState.from_runtime(runtime)

    assert state.healthy_nodes >= 1
    assert state.active_agents == 1
    assert "distributed" in state.planner_load
