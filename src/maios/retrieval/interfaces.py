from __future__ import annotations

from typing import Protocol

from maios.retrieval.document import Document


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class VectorStore(Protocol):
    def add(self, document: Document, embedding: list[float]) -> None:
        ...

    def search(
        self,
        embedding: list[float],
        top_k: int = 5,
    ) -> list[tuple[Document, float]]:
        ...
