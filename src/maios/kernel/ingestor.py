from __future__ import annotations

import re
from dataclasses import dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any

from maios.knowledge.graph import KnowledgeGraph

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".html", ".htm"}

_TAG_PATTERN = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_PATTERN = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class IngestReport:
    files: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    chunks: int = 0
    node_ids: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": list(self.files),
            "skipped": list(self.skipped),
            "chunks": self.chunks,
            "node_ids": list(self.node_ids),
        }


class DocumentIngestor:
    """Reads local documents into the knowledge graph as recallable nodes.

    Markdown files are split on headings, plain text on blank lines, and
    HTML has tags stripped first. Node ids are derived from the file path
    and chunk index, so re-ingesting a changed file updates its nodes
    instead of duplicating them.
    """

    def __init__(self, knowledge_graph: KnowledgeGraph, max_chars: int = 1200) -> None:
        self.knowledge_graph = knowledge_graph
        self.max_chars = max(200, max_chars)

    def ingest(self, path: str | Path) -> IngestReport:
        target = Path(path).expanduser()
        if target.is_dir():
            files = sorted(
                candidate
                for candidate in target.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES
            )
        else:
            files = [target]
        ingested: list[str] = []
        skipped: list[str] = []
        node_ids: list[str] = []
        with self.knowledge_graph.bulk():
            for file in files:
                if not file.exists() or file.suffix.lower() not in SUPPORTED_SUFFIXES:
                    skipped.append(str(file))
                    continue
                node_ids.extend(self._ingest_file_nodes(file))
                ingested.append(str(file))
        return IngestReport(
            files=tuple(ingested),
            skipped=tuple(skipped),
            chunks=len(node_ids),
            node_ids=tuple(node_ids),
        )

    def ingest_file(self, path: str | Path) -> list[str]:
        with self.knowledge_graph.bulk():
            return self._ingest_file_nodes(Path(path).expanduser())

    def _ingest_file_nodes(self, file: Path) -> list[str]:
        text = self._read_text(file)
        if file.suffix.lower() in {".html", ".htm"}:
            text = self._strip_html(text)
        chunks = self._chunk(text)
        node_ids: list[str] = []
        for index, (title, content) in enumerate(chunks):
            digest = sha1(f"{file.resolve()}:{index}".encode()).hexdigest()[:10]
            node = self.knowledge_graph.add_node(
                title=f"{file.name}: {title}" if title else f"{file.name} ({index + 1})",
                content=content,
                node_type="document",
                metadata={
                    "source_path": str(file),
                    "chunk_index": index,
                },
                node_id=f"DOC-{digest}",
                merge_duplicates=False,
                auto_link=False,
            )
            node_ids.append(node.node_id)
        return node_ids

    @staticmethod
    def _read_text(file: Path) -> str:
        raw = file.read_bytes()
        for encoding in ("utf-8", "cp949"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="ignore")

    @staticmethod
    def _strip_html(text: str) -> str:
        without_blocks = _SCRIPT_STYLE_PATTERN.sub(" ", text)
        without_tags = _TAG_PATTERN.sub(" ", without_blocks)
        return re.sub(r"[ \t]+", " ", without_tags)

    def _chunk(self, text: str) -> list[tuple[str, str]]:
        sections = self._split_sections(text)
        chunks: list[tuple[str, str]] = []
        for title, body in sections:
            compact = body.strip()
            if not compact:
                continue
            while len(compact) > self.max_chars:
                cut = compact.rfind(" ", 0, self.max_chars)
                if cut < self.max_chars // 2:
                    cut = self.max_chars
                chunks.append((title, compact[:cut].strip()))
                compact = compact[cut:].strip()
            if compact:
                chunks.append((title, compact))
        return chunks

    @staticmethod
    def _split_sections(text: str) -> list[tuple[str, str]]:
        lines = text.splitlines()
        sections: list[tuple[str, list[str]]] = [("", [])]
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") and stripped.lstrip("#").strip():
                sections.append((stripped.lstrip("#").strip(), []))
            else:
                sections[-1][1].append(line)
        result = [(title, "\n".join(body)) for title, body in sections]
        if len(result) == 1:
            paragraphs = re.split(r"\n\s*\n", result[0][1])
            return [("", paragraph) for paragraph in paragraphs]
        return result
