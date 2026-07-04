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


class InMemoryKnowledgeStore:
    """Simple key-value memory store used by the runtime pipeline."""

    def __init__(self):
        self._store: Dict[str, str] = {}

    def store(self, key: str, value: str):
        self._store[key] = value

    def retrieve(self, keys: list[str]):
        return {
            key: self._store[key]
            for key in keys
            if key in self._store
        }

    def get(self, key: str, default: str = ""):
        return self._store.get(key, default)

    def exists(self, key: str):
        return key in self._store

    def count(self):
        return len(self._store)
