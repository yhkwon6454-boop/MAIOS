from __future__ import annotations

from maios.adapters.gpt_adapter import GPTAdapter
from maios.core import MAIOSCore
from maios.mesh import CognitiveMesh


class DemoClient:
    def generate(self, prompt):
        return "cognitive mesh demo output"


def build_core() -> MAIOSCore:
    return MAIOSCore(gpt_adapter=GPTAdapter(DemoClient()))


def main() -> None:
    mesh = CognitiveMesh()
    mesh.register_node("node-a", core=build_core(), capacity=2)
    mesh.register_node("node-b", core=build_core(), capacity=2)

    mesh.nodes["node-a"].core.memory_kernel.remember_short_term("shared mesh context")
    mesh.nodes["node-a"].core.memory_kernel.remember_long_term(
        "cognitive mesh stores shared operational knowledge",
        {"source": "demo"},
    )

    result = mesh.execute_mission("Run a collaborative cognitive mesh mission.")
    print(result.final_output)
    print(mesh.knowledge_status())


if __name__ == "__main__":
    main()
