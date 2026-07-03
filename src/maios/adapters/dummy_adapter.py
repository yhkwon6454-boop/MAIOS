from __future__ import annotations

from maios.runtime.models import CognitivePacket


class DummyModelAdapter:
    """
    실제 LLM 호출 전 단계의 더미 어댑터.
    GPT/Claude/Gemini Adapter는 동일한 execute 인터페이스를 구현하면 된다.
    """

    def execute(self, packet: CognitivePacket, memory_context: dict[str, str]) -> str:
        memory_summary = "; ".join(memory_context.values()) if memory_context else "관련 메모리 없음"
        strategy = ", ".join(packet.strategy)

        return (
            f"### Packet {packet.packet_id}\n"
            f"- Instruction: {packet.instruction}\n"
            f"- Strategy: {strategy}\n"
            f"- Memory Context: {memory_summary}\n\n"
            f"분석 초안: 위 지시와 전략에 따라 임무를 구조화하고, 관련 메모리를 반영하여 "
            f"{packet.output_format} 형식의 산출물을 생성한다. 실제 모델 어댑터가 연결되면 "
            f"이 위치에서 본문 초안이 생성된다."
        )
