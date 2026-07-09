from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRole
from maios.distributed import DistributedRuntime


class DemoAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "output": f"{self.name} handled {context.get('task', 'work')}",
            "shared_memory": {self.name: context.get("task")},
        }


def main() -> None:
    runtime = DistributedRuntime(mission_id="role-demo")
    runtime.register_agent(
        DemoAgent("planner"),
        [AgentCapability("plan")],
        agent_id="planner-1",
        primary_role=AgentRole.PLANNER,
        secondary_roles=[AgentRole.COORDINATOR],
    )
    runtime.register_agent(
        DemoAgent("executor"),
        [AgentCapability("execute")],
        agent_id="executor-1",
        primary_role=AgentRole.EXECUTOR,
    )

    planner = runtime.role_manager.select_best("plan", role=AgentRole.PLANNER)
    print(f"Selected planner: {planner.agent_id if planner else 'none'}")

    task = runtime.execute_agent(
        "plan",
        {"task": "draft mission plan"},
        role=AgentRole.PLANNER,
    )
    print(f"{task.status}: {task.result['output'] if task.result else task.error}")

    runtime.reassign_role("executor-1", AgentRole.QUALITY)
    profile = runtime.role_manager.profile("executor-1")
    print(f"executor-1 reassigned to {profile.primary_role if profile else 'unknown'}")


if __name__ == "__main__":
    main()
