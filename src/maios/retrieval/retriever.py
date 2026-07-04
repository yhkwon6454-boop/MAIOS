from __future__ import annotations

from maios.retrieval.chunker import Chunker
from maios.retrieval.document import Document
from maios.retrieval.interfaces import EmbeddingProvider, VectorStore


class Retriever:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        chunker: Chunker | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.chunker = chunker or Chunker()

    def add(self, document: Document) -> list[Document]:
        chunks = self.chunker.chunk(document)
        for chunk in chunks:
            embedding = self.embedding_provider.embed(chunk.content)
            self.vector_store.add(chunk, embedding)

        return chunks

    def retrieve(self, query: str, top_k: int = 5) -> list[Document]:
        return [document for document, _score in self.retrieve_with_score(query, top_k=top_k)]

    def retrieve_with_score(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[tuple[Document, float]]:
        query_embedding = self.embedding_provider.embed(query)
        return self.vector_store.search(query_embedding, top_k=top_k)
