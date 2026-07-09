from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRole
from maios.distributed import DistributedRuntime


class DemoSwarmAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        task = context.get("task", "work")
        return {
            "output": f"{self.name} completed {task}",
            "shared_memory": {self.name: task},
        }


def main() -> None:
    runtime = DistributedRuntime(mission_id="swarm-demo")
    runtime.register_agent(
        DemoSwarmAgent("planner"),
        [AgentCapability("plan")],
        agent_id="planner-1",
        primary_role=AgentRole.PLANNER,
        secondary_roles=[AgentRole.COORDINATOR],
    )
    runtime.register_agent(
        DemoSwarmAgent("executor-a"),
        [AgentCapability("execute")],
        agent_id="executor-a",
        primary_role=AgentRole.EXECUTOR,
    )
    runtime.register_agent(
        DemoSwarmAgent("executor-b"),
        [AgentCapability("execute")],
        agent_id="executor-b",
        primary_role=AgentRole.EXECUTOR,
    )

    swarm = runtime.form_swarm("launch swarm", ["plan", "execute"])
    tasks = runtime.swarm_manager.distribute_tasks(
        swarm.swarm_id,
        [
            ("plan", {"task": "draft launch plan"}),
            ("execute", {"task": "run launch checklist"}),
        ],
    )
    health = runtime.swarm_manager.monitor_health(swarm.swarm_id)

    print(f"{swarm.swarm_id}: leader={swarm.leader_id} healthy={health.healthy}")
    for task in tasks:
        print(f"{task.task_id}: {task.status} by {task.assigned_agent_id}")


if __name__ == "__main__":
    main()
