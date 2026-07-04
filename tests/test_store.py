from maios.knowledge.store import KnowledgeStore
from maios.runtime.packet import Packet


def test_store_save_and_get():
    store = KnowledgeStore()

    packet = Packet("저장 테스트")

    store.save(packet)

    assert store.exists(packet.packet_id)
    assert store.get(packet.packet_id) == packet
    assert store.count() == 1
