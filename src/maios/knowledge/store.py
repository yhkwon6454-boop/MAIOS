from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

from maios.retrieval.document import Document
from maios.runtime.packet import Packet


class KnowledgeStore:
    """JSON-backed knowledge store with legacy Packet compatibility."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self._packets: dict[str, Packet] = {}
        self._documents: dict[str, dict[str, Any]] = {}

        if self.path and self.path.exists():
            self._load()

    def save(self, packet: Packet):
        self._packets[packet.packet_id] = packet

    def add(
        self,
        document: Document | str,
        metadata: dict[str, Any] | None = None,
        document_id: str | None = None,
    ) -> str:
        if isinstance(document, Document):
            record = asdict(document)
        else:
            record = {
                "document_id": document_id or f"D-{uuid4().hex[:8]}",
                "content": str(document),
                "metadata": metadata or {},
            }

        self._documents[record["document_id"]] = record
        self._persist()
        return record["document_id"]

    def get(self, item_id: str):
        if item_id in self._packets:
            return self._packets[item_id]

        document = self._documents.get(item_id)
        if document is None:
            return None

        return Document(
            content=document["content"],
            metadata=document.get("metadata", {}),
            document_id=document["document_id"],
        )

    def search(self, query: str, top_k: int = 5) -> list[Document]:
        query_text = query.lower()
        matches = [
            self.get(document_id)
            for document_id, document in self._documents.items()
            if query_text in document.get("content", "").lower()
            or any(
                query_text in str(value).lower() for value in document.get("metadata", {}).values()
            )
        ]
        return [document for document in matches if document is not None][:top_k]

    def update(
        self,
        document_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document | None:
        if document_id not in self._documents:
            return None

        if content is not None:
            self._documents[document_id]["content"] = content

        if metadata is not None:
            self._documents[document_id]["metadata"] = metadata

        self._persist()
        return self.get(document_id)

    def delete(self, item_id: str) -> bool:
        if item_id in self._packets:
            del self._packets[item_id]
            return True

        if item_id in self._documents:
            del self._documents[item_id]
            self._persist()
            return True

        return False

    def exists(self, item_id: str):
        return item_id in self._packets or item_id in self._documents

    def count(self):
        return len(self._packets) + len(self._documents)

    def _load(self) -> None:
        if self.path is None:
            return

        data = json.loads(self.path.read_text(encoding="utf-8"))
        documents = data.get("documents", {})
        self._documents = {
            document_id: {
                "document_id": document.get("document_id", document_id),
                "content": document.get("content", ""),
                "metadata": document.get("metadata", {}),
            }
            for document_id, document in documents.items()
        }

    def _persist(self) -> None:
        if self.path is None:
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"documents": self._documents}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class InMemoryKnowledgeStore:
    """Simple key-value memory store used by the runtime pipeline."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def store(self, key: str, value: str) -> None:
        self._store[key] = value

    def retrieve(self, keys: list[str]) -> dict[str, str]:
        return {key: self._store[key] for key in keys if key in self._store}

    def get(self, key: str, default: str = "") -> str:
        return self._store.get(key, default)

    def exists(self, key: str) -> bool:
        return key in self._store

    def count(self) -> int:
        return len(self._store)
