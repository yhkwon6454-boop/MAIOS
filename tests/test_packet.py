from maios.runtime.packet import Packet


def test_packet_creation():
    packet = Packet(instruction="테스트 임무를 수행하라.")
    assert packet.packet_id.startswith("P-")
    assert packet.mission_id.startswith("M-")
    assert packet.instruction == "테스트 임무를 수행하라."