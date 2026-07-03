from maios.kernel.executive_kernel import ExecutiveKernel
from maios.runtime.packet import Packet


def test_executive_kernel_execute():
    kernel = ExecutiveKernel()
    packet = Packet("임무를 분석하고 실행하라.")

    result = kernel.execute(packet)

    assert result["status"] == "EXECUTED"
    assert "cognitive_result" in result
    assert kernel.validate(result)