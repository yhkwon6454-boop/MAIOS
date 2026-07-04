from __future__ import annotations

from typing import Any

from maios.kernel.base import BaseKernel
from maios.kernel.memory_context import MemoryContextBuilder
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
        self.conversation_history: list[dict[str, str]] = []
        self.retriever = retriever
        self.knowledge_store = knowledge_store
        self.context_builder = MemoryContextBuilder()

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

    def remember_conversation(self, role: str, content: str) -> dict[str, str]:
        message = {"role": role, "content": content}
        self.conversation_history.append(message)
        return message

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

    def summarize(self) -> str:
        return self.context_builder.summarize(
            self.session_memory,
            self.long_term_memory,
            self.conversation_history,
        )

    def retrieve_context(self, query: str, top_k: int = 5) -> dict[str, str]:
        retrieved_items = self.retrieve(query, top_k=top_k)
        context = self.context_builder.build_context(
            query,
            retrieved_items,
            self.conversation_history,
        )
        summary = self.summarize()
        if summary:
            context["memory_summary"] = summary

        return context

    def inject_context(
        self,
        prompt: str,
        query: str | None = None,
        top_k: int = 5,
        memory_context: dict[str, str] | None = None,
    ) -> str:
        context = dict(memory_context or {})
        context.update(self.retrieve_context(query or prompt, top_k=top_k))
        return self.context_builder.inject_context(prompt, context)

    def validate(self, result):
        return (
            result.get("status") == "MEMORIZED"
            and "memory" in result
        )

    def shutdown(self):
        return True
