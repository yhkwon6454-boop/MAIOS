from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from maios.adapters.llm_provider import BaseLLMProvider
from maios.governance import GovernanceManager
from maios.kernel.agi_foundation import AGIFoundation, GoalPursuit
from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge.graph import KnowledgeGraph
from maios.knowledge.store import KnowledgeStore

DEFAULT_WORKSPACE = ".maios"


class Workspace:
    """Disk-backed home for MAIOS long-term memory and pursuit history.

    A workspace directory holds the knowledge graph, the long-term memory
    store, and the goal-pursuit journal, so consecutive runs share what the
    system has learned.
    """

    def __init__(self, root: str | Path = DEFAULT_WORKSPACE) -> None:
        self.root = Path(root)
        self.graph_path = self.root / "knowledge_graph.json"
        self.memory_path = self.root / "memory_store.json"
        self.pursuits_path = self.root / "pursuits.json"

    def exists(self) -> bool:
        return self.root.exists()

    def build_foundation(
        self,
        *,
        governance: GovernanceManager | None = None,
        llm_provider: BaseLLMProvider | None = None,
        runtime: Any | None = None,
        **kwargs: Any,
    ) -> AGIFoundation:
        graph = KnowledgeGraph(path=self.graph_path)
        memory = MemoryKernel(knowledge_store=KnowledgeStore(path=self.memory_path))
        foundation = AGIFoundation(
            knowledge_graph=graph,
            memory_kernel=memory,
            governance=governance,
            llm_provider=llm_provider,
            runtime=runtime,
            **kwargs,
        )
        foundation.pursuits.extend(self.load_pursuits())
        return foundation

    def load_pursuits(self) -> list[GoalPursuit]:
        if not self.pursuits_path.exists():
            return []
        data = json.loads(self.pursuits_path.read_text(encoding="utf-8"))
        return [GoalPursuit.from_dict(item) for item in data]

    def save(self, foundation: AGIFoundation) -> None:
        """Write the pursuit journal.

        The knowledge graph and memory store persist themselves on every
        write because they were opened with workspace paths.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        self.pursuits_path.write_text(
            json.dumps(
                [pursuit.to_dict() for pursuit in foundation.pursuits],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        for pursuit in foundation.pursuits:
            if pursuit.output:
                self.save_artifact(pursuit)

    def save_artifact(self, pursuit: GoalPursuit) -> Path:
        artifacts_dir = self.root / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = artifacts_dir / f"{pursuit.pursuit_id}.md"
        path.write_text(f"# {pursuit.objective}\n\n{pursuit.output}\n", encoding="utf-8")
        return path

    def artifact_path(self, pursuit: GoalPursuit) -> Path:
        return self.root / "artifacts" / f"{pursuit.pursuit_id}.md"

    def stats(self) -> dict[str, int]:
        nodes = 0
        if self.graph_path.exists():
            graph_data = json.loads(self.graph_path.read_text(encoding="utf-8"))
            nodes = len(graph_data.get("nodes", {}))
        pursuits = len(self.load_pursuits())
        return {"nodes": nodes, "pursuits": pursuits}
