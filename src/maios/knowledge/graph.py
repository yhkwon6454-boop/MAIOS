from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from maios.knowledge.store import KnowledgeStore

if TYPE_CHECKING:
    from maios.kernel.memory_kernel import MemoryKernel

KNOWLEDGE_RELATIONSHIPS = frozenset(
    {
        "supports",
        "contradicts",
        "depends_on",
        "derived_from",
        "similar_to",
        "part_of",
    }
)


@dataclass
class KnowledgeNode:
    title: str
    content: str
    node_type: str = "concept"
    node_id: str = field(default_factory=lambda: f"KN-{uuid4().hex[:8]}")
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def text(self) -> str:
        return f"{self.title} {self.content} {' '.join(map(str, self.metadata.values()))}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeEdge:
    source_id: str
    target_id: str
    relationship: str
    weight: float = 1.0
    edge_id: str = field(default_factory=lambda: f"KE-{uuid4().hex[:8]}")
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeCluster:
    name: str
    node_ids: tuple[str, ...]
    cluster_id: str = field(default_factory=lambda: f"KC-{uuid4().hex[:8]}")
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class KnowledgeGraph:
    """Persistent long-term graph for concepts, evidence, reflections, and experience."""

    def __init__(
        self,
        path: str | Path | None = None,
        knowledge_store: KnowledgeStore | None = None,
        memory_kernel: MemoryKernel | None = None,
        auto_link_threshold: float = 0.2,
        duplicate_threshold: float = 0.86,
    ) -> None:
        self.path = Path(path) if path else None
        self.knowledge_store = knowledge_store
        self.memory_kernel = memory_kernel
        self.auto_link_threshold = auto_link_threshold
        self.duplicate_threshold = duplicate_threshold
        self.nodes: dict[str, KnowledgeNode] = {}
        self.edges: dict[str, KnowledgeEdge] = {}
        self.clusters: dict[str, KnowledgeCluster] = {}

        if self.path and self.path.exists():
            self._load()

    def add_node(
        self,
        title: str,
        content: str,
        node_type: str = "concept",
        metadata: dict[str, Any] | None = None,
        node_id: str | None = None,
        merge_duplicates: bool = True,
    ) -> KnowledgeNode:
        node = KnowledgeNode(
            title=title.strip(),
            content=content.strip(),
            node_type=node_type,
            node_id=node_id or f"KN-{uuid4().hex[:8]}",
            metadata=dict(metadata or {}),
        )
        if not node.title:
            raise ValueError("Knowledge node title is required.")
        if not node.content:
            raise ValueError("Knowledge node content is required.")

        if merge_duplicates:
            duplicate = self._find_duplicate(node)
            if duplicate is not None:
                self._merge_node(duplicate, node)
                self._persist_integrations(duplicate)
                self._persist()
                return duplicate

        self.nodes[node.node_id] = node
        self._persist_integrations(node)
        self.link_related_concepts(node.node_id)
        self._link_metadata_relationships(node)
        self._persist()
        return node

    def get_node(self, node_id: str) -> KnowledgeNode | None:
        return self.nodes.get(node_id)

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeEdge:
        if relationship not in KNOWLEDGE_RELATIONSHIPS:
            raise ValueError(f"Unsupported knowledge relationship: {relationship}")
        if source_id not in self.nodes:
            raise KeyError(f"Unknown source node: {source_id}")
        if target_id not in self.nodes:
            raise KeyError(f"Unknown target node: {target_id}")
        if source_id == target_id:
            raise ValueError("Knowledge edges require distinct nodes.")

        existing = self._find_edge(source_id, target_id, relationship)
        if existing is not None:
            existing.weight = max(existing.weight, weight)
            existing.metadata.update(metadata or {})
            self._persist()
            return existing

        edge = KnowledgeEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            weight=max(0.0, min(weight, 1.0)),
            metadata=dict(metadata or {}),
        )
        self.edges[edge.edge_id] = edge
        self._persist()
        return edge

    def edges_for(
        self,
        node_id: str,
        relationships: set[str] | list[str] | tuple[str, ...] | None = None,
        direction: str = "both",
    ) -> list[KnowledgeEdge]:
        relationship_filter = set(relationships or KNOWLEDGE_RELATIONSHIPS)
        edges = []
        for edge in self.edges.values():
            if edge.relationship not in relationship_filter:
                continue
            if direction in {"out", "both"} and edge.source_id == node_id:
                edges.append(edge)
            elif direction in {"in", "both"} and edge.target_id == node_id:
                edges.append(edge)
        return edges

    def link_related_concepts(self, node_id: str) -> list[KnowledgeEdge]:
        node = self._require_node(node_id)
        links = []
        for candidate in self.nodes.values():
            if candidate.node_id == node.node_id:
                continue
            score = self._similarity(node.text(), candidate.text())
            if score >= self.auto_link_threshold:
                links.append(
                    self.add_edge(
                        node.node_id,
                        candidate.node_id,
                        "similar_to",
                        weight=score,
                        metadata={"auto_linked": True},
                    )
                )
        return links

    def merge_duplicates(self, threshold: float | None = None) -> list[KnowledgeNode]:
        threshold = threshold if threshold is not None else self.duplicate_threshold
        merged = []
        node_ids = list(self.nodes)
        for index, node_id in enumerate(node_ids):
            node = self.nodes.get(node_id)
            if node is None:
                continue
            for other_id in node_ids[index + 1 :]:
                other = self.nodes.get(other_id)
                if other is None:
                    continue
                if self._similarity(node.text(), other.text()) >= threshold:
                    self._merge_node(node, other)
                    merged.append(node)
        if merged:
            self._persist()
        return merged

    def learn_experience(
        self,
        description: str,
        outcome: str,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeNode:
        node = self.add_node(
            title=f"Experience: {description[:80]}",
            content=f"{description}\nOutcome: {outcome}",
            node_type="experience",
            metadata={"outcome": outcome, **(metadata or {})},
        )
        relation = (
            "contradicts"
            if outcome.lower() in {"failure", "failed", "negative", "blocked"}
            else "supports"
        )
        for candidate in self.similarity_search(description, top_k=5):
            if candidate.node_id != node.node_id:
                self.add_edge(node.node_id, candidate.node_id, relation, weight=0.6)
        return node

    def build_clusters(self, min_similarity: float = 0.25) -> list[KnowledgeCluster]:
        visited: set[str] = set()
        clusters: list[KnowledgeCluster] = []
        for node in self.nodes.values():
            if node.node_id in visited:
                continue
            component = self._cluster_component(node, min_similarity)
            visited.update(component)
            if len(component) < 2:
                continue
            first = self.nodes[component[0]]
            cluster = KnowledgeCluster(
                name=f"{first.title} cluster",
                node_ids=tuple(component),
                metadata={"min_similarity": min_similarity},
            )
            clusters.append(cluster)

        self.clusters = {cluster.cluster_id: cluster for cluster in clusters}
        self._persist()
        return clusters

    def traverse(
        self,
        start_id: str,
        depth: int = 1,
        relationships: set[str] | list[str] | tuple[str, ...] | None = None,
        direction: str = "out",
    ) -> list[KnowledgeNode]:
        self._require_node(start_id)
        if depth < 1:
            return []
        visited = {start_id}
        frontier = [start_id]
        ordered: list[KnowledgeNode] = []

        for _ in range(depth):
            next_frontier: list[str] = []
            for node_id in frontier:
                for edge in self.edges_for(node_id, relationships, direction=direction):
                    neighbor_id = edge.target_id if edge.source_id == node_id else edge.source_id
                    if neighbor_id in visited:
                        continue
                    visited.add(neighbor_id)
                    next_frontier.append(neighbor_id)
                    ordered.append(self.nodes[neighbor_id])
            frontier = next_frontier
            if not frontier:
                break
        return ordered

    def semantic_search(self, query: str, top_k: int = 5) -> list[KnowledgeNode]:
        scored = [
            (self._semantic_score(query, node), node)
            for node in self.nodes.values()
            if self._semantic_score(query, node) > 0
        ]
        return [
            node
            for score, node in sorted(
                scored,
                key=lambda item: (item[0], item[1].updated_at),
                reverse=True,
            )[:top_k]
        ]

    def similarity_search(self, node_or_text: str, top_k: int = 5) -> list[KnowledgeNode]:
        origin = self.nodes.get(node_or_text)
        text = origin.text() if origin is not None else node_or_text
        scored = []
        for node in self.nodes.values():
            if origin is not None and node.node_id == origin.node_id:
                continue
            score = self._similarity(text, node.text())
            if score > 0:
                scored.append((score, node))
        return [
            node for score, node in sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]
        ]

    def _persist_integrations(self, node: KnowledgeNode) -> None:
        metadata = {
            "memory_type": "knowledge_graph_node",
            "node_id": node.node_id,
            "node_type": node.node_type,
            **node.metadata,
        }
        if self.knowledge_store is not None:
            self.knowledge_store.add(node.content, metadata=metadata, document_id=node.node_id)
        if self.memory_kernel is not None:
            self.memory_kernel.remember_long_term(node.content, metadata=metadata)

    def _link_metadata_relationships(self, node: KnowledgeNode) -> None:
        for relationship in KNOWLEDGE_RELATIONSHIPS - {"similar_to"}:
            target = node.metadata.get(relationship)
            if isinstance(target, str) and target in self.nodes and target != node.node_id:
                self.add_edge(node.node_id, target, relationship)
            elif isinstance(target, list):
                for target_id in target:
                    if isinstance(target_id, str) and target_id in self.nodes:
                        self.add_edge(node.node_id, target_id, relationship)

    def _find_duplicate(self, node: KnowledgeNode) -> KnowledgeNode | None:
        normalized_title = self._normalize_title(node.title)
        for candidate in self.nodes.values():
            if self._normalize_title(candidate.title) == normalized_title:
                return candidate
            if self._similarity(candidate.text(), node.text()) >= self.duplicate_threshold:
                return candidate
        return None

    def _merge_node(self, target: KnowledgeNode, duplicate: KnowledgeNode) -> None:
        if duplicate.content not in target.content:
            target.content = f"{target.content}\n\n{duplicate.content}"
        target.metadata.update(duplicate.metadata)
        target.updated_at = datetime.now(UTC).isoformat()

        if duplicate.node_id in self.nodes:
            del self.nodes[duplicate.node_id]
        for edge in list(self.edges.values()):
            if edge.source_id == duplicate.node_id:
                edge.source_id = target.node_id
            if edge.target_id == duplicate.node_id:
                edge.target_id = target.node_id
            if edge.source_id == edge.target_id:
                del self.edges[edge.edge_id]

    def _cluster_component(self, node: KnowledgeNode, min_similarity: float) -> list[str]:
        component = [node.node_id]
        for candidate in self.nodes.values():
            if candidate.node_id == node.node_id:
                continue
            linked = any(
                edge.relationship == "similar_to"
                and {edge.source_id, edge.target_id} == {node.node_id, candidate.node_id}
                for edge in self.edges.values()
            )
            if linked or self._similarity(node.text(), candidate.text()) >= min_similarity:
                component.append(candidate.node_id)
        return sorted(component)

    def _find_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
    ) -> KnowledgeEdge | None:
        for edge in self.edges.values():
            same_direction = edge.source_id == source_id and edge.target_id == target_id
            reverse_similarity = (
                relationship == "similar_to"
                and edge.source_id == target_id
                and edge.target_id == source_id
            )
            if edge.relationship == relationship and (same_direction or reverse_similarity):
                return edge
        return None

    def _require_node(self, node_id: str) -> KnowledgeNode:
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(f"Unknown knowledge node: {node_id}")
        return node

    def _load(self) -> None:
        if self.path is None:
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.nodes = {
            node_id: KnowledgeNode(**node_data)
            for node_id, node_data in data.get("nodes", {}).items()
        }
        self.edges = {
            edge_id: KnowledgeEdge(**edge_data)
            for edge_id, edge_data in data.get("edges", {}).items()
        }
        self.clusters = {
            cluster_id: KnowledgeCluster(
                **{
                    **cluster_data,
                    "node_ids": tuple(cluster_data.get("node_ids", ())),
                }
            )
            for cluster_id, cluster_data in data.get("clusters", {}).items()
        }

    def _persist(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {
                    "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
                    "edges": {edge_id: edge.to_dict() for edge_id, edge in self.edges.items()},
                    "clusters": {
                        cluster_id: cluster.to_dict()
                        for cluster_id, cluster in self.clusters.items()
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _semantic_score(self, query: str, node: KnowledgeNode) -> float:
        query_tokens = self._tokens(query)
        node_tokens = self._tokens(node.text())
        if not query_tokens or not node_tokens:
            return 0.0
        overlap = len(query_tokens & node_tokens) / len(query_tokens)
        phrase_bonus = 0.25 if query.lower() in node.text().lower() else 0.0
        return overlap + phrase_bonus

    def _similarity(self, left: str, right: str) -> float:
        left_tokens = self._tokens(left)
        right_tokens = self._tokens(right)
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    def _tokens(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(token) > 2}

    def _normalize_title(self, text: str) -> str:
        return " ".join(re.findall(r"[a-zA-Z0-9_]+", text.lower()))
