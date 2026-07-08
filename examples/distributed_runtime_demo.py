from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability
from maios.distributed import DistributedRuntime


class DemoAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        task = context.get("task", "work")
        return {
            "output": f"{self.name} completed {task}",
            "shared_memory": {self.name: task},
        }


def main() -> None:
    runtime = DistributedRuntime(mission_id="demo-mission")
    runtime.register_node("node-a", capacity=2)
    runtime.register_node("node-b", capacity=2)
    runtime.register_agent(
        DemoAgent("planner"),
        [AgentCapability("plan")],
        agent_id="planner-1",
        node_id="node-a",
    )
    runtime.register_agent(
        DemoAgent("executor"),
        [AgentCapability("execute")],
        agent_id="executor-1",
        node_id="node-b",
    )

    tasks = runtime.execute_agent_tasks(
        [
            ("plan", {"task": "draft distributed plan"}),
            ("execute", {"task": "run distributed plan"}),
        ]
    )

    for task in tasks:
        print(f"{task.task_id}: {task.status} by {task.agent_id}")
        print(task.result["output"] if task.result else task.error)


if __name__ == "__main__":
    main()
