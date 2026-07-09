from __future__ import annotations

from maios.retrieval.document import Document


class Chunker:
    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0.")
        if overlap < 0:
            raise ValueError("overlap must be greater than or equal to 0.")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size.")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document) -> list[Document]:
        content = document.content
        if len(content) <= self.chunk_size:
            return [document]

        chunks: list[Document] = []
        start = 0
        index = 0
        step = self.chunk_size - self.overlap

        while start < len(content):
            end = start + self.chunk_size
            metadata = {
                **document.metadata,
                "source_document_id": document.document_id,
                "chunk_index": index,
                "start": start,
                "end": min(end, len(content)),
            }
            chunks.append(Document(content=content[start:end], metadata=metadata))
            start += step
            index += 1

        return chunks
