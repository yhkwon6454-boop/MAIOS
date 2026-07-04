from __future__ import annotations

from maios.adapters.gpt_adapter import GPTAdapter
from maios.core import MAIOSCore
from maios.distributed import DistributedRuntime


class DemoClient:
    def generate(self, prompt):
        return "distributed demo output"


def main() -> None:
    runtime = DistributedRuntime()
    runtime.register_node("node-a", core=MAIOSCore(gpt_adapter=GPTAdapter(DemoClient())))
    runtime.register_node("node-b", core=MAIOSCore(gpt_adapter=GPTAdapter(DemoClient())))

    mission = runtime.execute_mission("Run a distributed MAIOS demo mission.")
    print(f"{mission.mission_id}: {mission.status} on {mission.assigned_node}")
    print(mission.result.final_output)


if __name__ == "__main__":
    main()
