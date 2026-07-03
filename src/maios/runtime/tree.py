from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from maios.runtime.models import CognitivePacket, CognitiveProcess, Mission


@dataclass
class ProcessNode:
    process: CognitiveProcess
    packets: list[CognitivePacket] = field(default_factory=list)
    children: list["ProcessNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "process_id": self.process.process_id,
            "name": self.process.name,
            "type": self.process.process_type,
            "status": self.process.status.value,
            "packets": [
                {
                    "packet_id": packet.packet_id,
                    "instruction": packet.instruction,
                    "strategy": packet.strategy,
                    "required_memory": packet.required_memory,
                    "output_format": packet.output_format,
                    "status": packet.status.value,
                }
                for packet in self.packets
            ],
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class CognitiveProcessTree:
    mission: Mission
    root_nodes: list[ProcessNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission": {
                "mission_id": self.mission.mission_id,
                "title": self.mission.title,
                "objective": self.mission.objective,
                "mission_type": self.mission.mission_type.value,
                "priority": self.mission.priority.value,
                "status": self.mission.status.value,
            },
            "process_tree": [node.to_dict() for node in self.root_nodes],
        }

    def flatten_packets(self) -> list[CognitivePacket]:
        packets: list[CognitivePacket] = []

        def walk(node: ProcessNode) -> None:
            packets.extend(node.packets)
            for child in node.children:
                walk(child)

        for root in self.root_nodes:
            walk(root)

        return packets
