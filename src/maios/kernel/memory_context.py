from __future__ import annotations

from typing import Any


class MemoryContextBuilder:
    """Builds compact memory context for model prompts."""

    def summarize(
        self,
        short_term_memory: list[Any],
        long_term_memory: list[Any],
        conversation_history: list[dict[str, str]],
    ) -> str:
        sections = []

        if short_term_memory:
            sections.append(
                self._section(
                    "Short-term memory",
                    [str(item) for item in short_term_memory[-5:]],
                )
            )

        if long_term_memory:
            sections.append(
                self._section(
                    "Long-term memory",
                    [self._document_text(item) for item in long_term_memory[-5:]],
                )
            )

        if conversation_history:
            sections.append(
                self._section(
                    "Conversation history",
                    [
                        f"{item.get('role', 'unknown')}: {item.get('content', '')}"
                        for item in conversation_history[-5:]
                    ],
                )
            )

        return "\n\n".join(section for section in sections if section)

    def build_context(
        self,
        query: str,
        retrieved_items: list[Any],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, str]:
        context: dict[str, str] = {}

        if retrieved_items:
            context["retrieved_memory"] = "\n".join(
                self._document_text(item) for item in retrieved_items
            )

        if conversation_history:
            context["conversation_history"] = "\n".join(
                f"{item.get('role', 'unknown')}: {item.get('content', '')}"
                for item in conversation_history[-5:]
            )

        if query:
            context["query"] = query

        return context

    def inject_context(self, prompt: str, context: dict[str, str]) -> str:
        if not context:
            return prompt

        memory = "\n".join(f"- {key}: {value}" for key, value in context.items() if value)
        if not memory:
            return prompt

        return "\n".join(
            [
                "[MAIOS Memory Context]",
                memory,
                "",
                prompt,
            ]
        )

    def _section(self, title: str, items: list[str]) -> str:
        if not items:
            return ""

        body = "\n".join(f"- {item}" for item in items if item)
        return f"{title}:\n{body}" if body else ""

    def _document_text(self, item: Any) -> str:
        return item.content if hasattr(item, "content") else str(item)
