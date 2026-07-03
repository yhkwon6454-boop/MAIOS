from typing import Dict

from maios.runtime.packet import Packet


class KnowledgeStore:
    """Packet을 저장하는 메모리 저장소"""

    def __init__(self):
        self._store: Dict[str, Packet] = {}

    def save(self, packet: Packet):
        self._store[packet.packet_id] = packet

    def get(self, packet_id: str):
        return self._store.get(packet_id)

    def exists(self, packet_id: str):
        return packet_id in self._store

    def count(self):
        return len(self._store)