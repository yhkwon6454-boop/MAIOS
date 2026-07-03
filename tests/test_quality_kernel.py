from maios.kernel.executive_kernel import ExecutiveKernel
from maios.kernel.quality_kernel import QualityKernel
from maios.runtime.packet import Packet


def test_quality_kernel():
    packet = Packet("적의 기동을 분석하라.")

    executive = ExecutiveKernel()
    execution = executive.execute(packet)

    quality = QualityKernel()

    result = quality.execute(execution)

    assert result["passed"]
    assert result["score"] == 100
    assert quality.validate(result)