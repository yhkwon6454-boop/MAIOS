from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass
class Packet:
    """Small executable MAIOS packet."""

    instruction: str
    mission_id: str = field(default_factory=lambda: f"M-{uuid4().hex[:8]}")
    packet_id: str = field(default_factory=lambda: f"P-{uuid4().hex[:8]}")
    strategy: list[str] = field(default_factory=list)
    memory_keys: list[str] = field(default_factory=list)
    output_format: str = "text"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
