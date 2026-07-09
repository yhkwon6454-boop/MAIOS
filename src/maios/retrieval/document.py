from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class Document:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    document_id: str = field(default_factory=lambda: f"D-{uuid4().hex[:8]}")
