from maios.kernel.base import BaseKernel
from maios.kernel.cognitive_kernel import CognitiveKernel
from maios.runtime.packet import Packet


class ExecutiveKernel(BaseKernel):
    """Packet 실행을 지휘하는 Kernel"""

    def __init__(self):
        self.cognitive_kernel = CognitiveKernel()

    def initialize(self):
        return True

    def execute(self, packet: Packet):
        cognitive_result = self.cognitive_kernel.execute(packet)

        return {
            "packet_id": packet.packet_id,
            "mission_id": packet.mission_id,
            "instruction": packet.instruction,
            "cognitive_result": cognitive_result,
            "status": "EXECUTED",
        }

    def validate(self, result):
        return (
            result.get("status") == "EXECUTED"
            and "cognitive_result" in result
        )

    def shutdown(self):
        return True