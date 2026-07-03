from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class MissionType(str, Enum):
    MILITARY_RESEARCH = "MILITARY_RESEARCH"
    STRATEGY_ANALYSIS = "STRATEGY_ANALYSIS"
    TRANSLATION = "TRANSLATION"
    WRITING = "WRITING"
    PLANNING = "PLANNING"
    PHILOSOPHY = "PHILOSOPHY"
    GENERAL = "GENERAL"


class Priority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Status(str, Enum):
    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NEEDS_REVISION = "NEEDS_REVISION"


@dataclass
class Mission:
    title: str
    objective: str
    mission_type: MissionType = MissionType.GENERAL
    priority: Priority = Priority.NORMAL
    constraints: list[str] = field(default_factory=list)
    expected_output: str = "brief"
    mission_id: str = field(default_factory=lambda: f"M-{uuid4().hex[:8]}")
    status: Status = Status.CREATED

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mission":
        return cls(
            title=data.get("title", "Untitled Mission"),
            objective=data.get("objective", ""),
            mission_type=MissionType(data.get("mission_type", "GENERAL")),
            priority=Priority(data.get("priority", "NORMAL")),
            constraints=data.get("constraints", []),
            expected_output=data.get("expected_output", "brief"),
        )


@dataclass
class CognitiveProcess:
    mission_id: str
    name: str
    process_type: str
    dependencies: list[str] = field(default_factory=list)
    process_id: str = field(default_factory=lambda: f"P-{uuid4().hex[:8]}")
    status: Status = Status.READY


@dataclass
class CognitivePacket:
    process_id: str
    instruction: str
    strategy: list[str] = field(default_factory=list)
    required_memory: list[str] = field(default_factory=list)
    output_format: str = "brief"
    packet_id: str = field(default_factory=lambda: f"CP-{uuid4().hex[:8]}")
    status: Status = Status.READY


@dataclass
class QAResult:
    status: Status
    score: int
    issues: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    mission: Mission
    processes: list[CognitiveProcess]
    packets: list[CognitivePacket]
    packet_outputs: list[str]
    qa_result: QAResult
    final_output: str
