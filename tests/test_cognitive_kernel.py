from maios.kernel.cognitive_kernel import CognitiveKernel
from maios.runtime.packet import Packet


def test_cognitive_kernel_execute():
    kernel = CognitiveKernel()

    packet = Packet("북한군 드론 위협 분석")

    result = kernel.execute(packet)

    assert result["status"] == "SUCCESS"
    assert "analysis" in result
    assert kernel.validate(result)