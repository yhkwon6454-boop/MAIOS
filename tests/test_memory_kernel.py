from maios.kernel.memory_kernel import MemoryKernel


def test_memory_kernel_execute():
    kernel = MemoryKernel()

    result = kernel.execute("적 기동 분석")

    assert result["status"] == "MEMORIZED"
    assert "memory" in result
    assert kernel.validate(result)