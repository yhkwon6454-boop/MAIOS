from __future__ import annotations

from dataclasses import dataclass, field

from maios.knowledge.graph import KnowledgeGraph
from maios.knowledge.ontology import OntologyAdapter

RECALL_NODE_TYPES = {"concept", "document", "evidence", "experience", "reflection"}


@dataclass(frozen=True)
class RecallResult:
    entries: tuple[str, ...] = ()
    node_ids: tuple[str, ...] = field(default_factory=tuple)
    expanded_terms: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.entries)


class MemoryRecall:
    """Retrieves long-term knowledge relevant to the current objective.

    Searches the knowledge graph and keeps only content-bearing node types
    (concepts, evidence, experiences, reflections), skipping raw state dumps.
    """

    def __init__(
        self,
        knowledge_graph: KnowledgeGraph | None = None,
        top_k: int = 3,
        max_chars: int = 200,
        ontology: OntologyAdapter | None = None,
    ) -> None:
        self.knowledge_graph = knowledge_graph
        self.top_k = max(1, top_k)
        self.max_chars = max(40, max_chars)
        self.ontology = ontology

    def recall(self, objective: str) -> RecallResult:
        if self.knowledge_graph is None:
            return RecallResult()
        expanded_terms: tuple[str, ...] = ()
        query = objective
        if self.ontology is not None and self.ontology.available:
            expanded_terms = self.ontology.expand_query(objective)
            if expanded_terms:
                query = objective + " " + " ".join(expanded_terms)
        candidates = self.knowledge_graph.semantic_search(query, top_k=self.top_k * 4)
        entries: list[str] = []
        node_ids: list[str] = []
        for node in candidates:
            if node.node_type not in RECALL_NODE_TYPES:
                continue
            entries.append(self._format(node.title, node.content))
            node_ids.append(node.node_id)
            if len(entries) >= self.top_k:
                break
        return RecallResult(
            entries=tuple(entries),
            node_ids=tuple(node_ids),
            expanded_terms=expanded_terms,
        )

    def _format(self, title: str, content: str) -> str:
        text = " ".join(content.split())
        if len(text) > self.max_chars:
            text = text[: self.max_chars] + "..."
        return f"{title}: {text}"
