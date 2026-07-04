from __future__ import annotations

from typing import Any

from maios.kernel.base import BaseKernel
from maios.knowledge.store import KnowledgeStore
from maios.retrieval import Document, Retriever


class MemoryKernel(BaseKernel):
    """Kernel for short-term memory and long-term retrieval."""

    def __init__(
        self,
        retriever: Retriever | None = None,
        knowledge_store: KnowledgeStore | None = None,
    ) -> None:
        self.session_memory: list[Any] = []
        self.long_term_memory: list[Document] = []
        self.retriever = retriever
        self.knowledge_store = knowledge_store

    def initialize(self):
        return True

    def execute(self, data):
        self.remember_short_term(data)

        return {
            "memory": self.session_memory,
            "status": "MEMORIZED",
        }

    def remember_short_term(self, data):
        self.session_memory.append(data)
        return data

    def remember_long_term(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        document = Document(content=content, metadata=metadata or {})
        self.long_term_memory.append(document)

        if self.knowledge_store is not None:
            self.knowledge_store.add(document)

        if self.retriever is not None:
            self.retriever.add(document)

        return document

    def retrieve(self, query: str, top_k: int = 5):
        short_term_matches = self.retrieve_short_term(query, top_k=top_k)

        if self.retriever is None:
            return short_term_matches

        long_term_matches = self.retriever.retrieve(query, top_k=top_k)
        return [*short_term_matches, *long_term_matches][:top_k]

    def retrieve_with_score(self, query: str, top_k: int = 5):
        if self.retriever is not None:
            return self.retriever.retrieve_with_score(query, top_k=top_k)

        return [
            (Document(content=str(item), metadata={"memory_type": "short_term"}), 1.0)
            for item in self.retrieve_short_term(query, top_k=top_k)
        ]

    def retrieve_short_term(self, query: str, top_k: int = 5):
        query_text = query.lower()
        matches = [
            item
            for item in self.session_memory
            if query_text in str(item).lower()
        ]
        return matches[:top_k]

    def validate(self, result):
        return (
            result.get("status") == "MEMORIZED"
            and "memory" in result
        )

    def shutdown(self):
        return True
