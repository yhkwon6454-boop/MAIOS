from __future__ import annotations

from typing import TYPE_CHECKING

from maios.retrieval.document import Document

if TYPE_CHECKING:
    from maios.knowledge.store import KnowledgeStore


class RetrievalEngine:
    """RAG retrieval engine backed by KnowledgeStore keyword search."""

    def __init__(self, knowledge_store: KnowledgeStore, vector_retriever=None) -> None:
        self.knowledge_store = knowledge_store
        self.vector_retriever = vector_retriever

    def add(
        self,
        content: str,
        metadata: dict | None = None,
        document_id: str | None = None,
    ) -> str:
        return self.knowledge_store.add(
            content,
            metadata=metadata,
            document_id=document_id,
        )

    def retrieve(self, query: str, top_k: int = 5) -> list[Document]:
        return [document for document, _score in self.retrieve_with_score(query, top_k=top_k)]

    def retrieve_with_score(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[tuple[Document, float]]:
        if self.vector_retriever is not None:
            return self.vector_retriever.retrieve_with_score(query, top_k=top_k)

        return self._keyword_retrieve_with_score(query, top_k=top_k)

    def _keyword_retrieve_with_score(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[tuple[Document, float]]:
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        results: list[tuple[Document, float]] = []
        for document in self.knowledge_store.search("", top_k=self.knowledge_store.count()):
            score = self._score(document, query_terms)
            if score > 0:
                results.append((document, score))

        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_k]

    def _score(self, document: Document, query_terms: list[str]) -> float:
        searchable = " ".join(
            [
                document.content,
                " ".join(str(value) for value in document.metadata.values()),
            ]
        ).lower()
        matches = sum(1 for term in query_terms if term in searchable)
        return matches / len(query_terms)

    def _tokenize(self, text: str) -> list[str]:
        return [token for token in text.lower().split() if token.strip()]
