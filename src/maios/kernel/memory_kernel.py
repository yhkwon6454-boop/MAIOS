from maios.kernel.base import BaseKernel


class MemoryKernel(BaseKernel):
    """Memory를 관리하는 Kernel"""

    def __init__(self):
        self.session_memory = []
        self.long_term_memory = []

    def initialize(self):
        return True

    def execute(self, data):
        self.session_memory.append(data)

        return {
            "memory": self.session_memory,
            "status": "MEMORIZED",
        }

    def validate(self, result):
        return (
            result.get("status") == "MEMORIZED"
            and "memory" in result
        )

    def shutdown(self):
        return True