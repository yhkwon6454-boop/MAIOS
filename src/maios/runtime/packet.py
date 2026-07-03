from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Packet:
    """MAIOS의 최소 실행 단위"""

    instruction: str
    mission_id: str = field(default_factory=lambda: f"M-{uuid4().hex[:8]}")
    packet_id: str = field(default_factory=lambda: f"P-{uuid4().hex[:8]}")
    strategy: list[str] = field(default_factory=list)
    memory_keys: list[str] = field(default_factory=list)
    output_format: str = "text"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())