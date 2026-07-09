from __future__ import annotations

from maios.kernel import DocumentIngestor, MemoryRecall, Workspace
from maios.knowledge import KnowledgeGraph


def _write(path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_ingest_markdown_splits_on_headings(tmp_path):
    doc = tmp_path / "doctrine.md"
    _write(doc, "# Intro\nMission command basics.\n# Drills\nRun drone drills weekly.")
    graph = KnowledgeGraph()

    node_ids = DocumentIngestor(graph).ingest_file(doc)

    assert len(node_ids) == 2
    titles = [graph.get_node(node_id).title for node_id in node_ids]
    assert titles == ["doctrine.md: Intro", "doctrine.md: Drills"]
    assert all(graph.get_node(node_id).node_type == "document" for node_id in node_ids)
    assert graph.get_node(node_ids[0]).metadata["source_path"] == str(doc)


def test_ingest_plain_text_splits_on_blank_lines(tmp_path):
    doc = tmp_path / "notes.txt"
    _write(doc, "First paragraph about drones.\n\nSecond paragraph about jamming.")

    node_ids = DocumentIngestor(KnowledgeGraph()).ingest_file(doc)

    assert len(node_ids) == 2


def test_ingest_html_strips_tags_and_scripts(tmp_path):
    doc = tmp_path / "post.html"
    _write(
        doc,
        "<html><head><style>body{color:red}</style><script>alert(1)</script></head>"
        "<body><h1>Drone Post</h1><p>Layered defense works best.</p></body></html>",
    )
    graph = KnowledgeGraph()

    node_ids = DocumentIngestor(graph).ingest_file(doc)

    content = " ".join(graph.get_node(node_id).content for node_id in node_ids)
    assert "Layered defense works best." in content
    assert "<p>" not in content
    assert "alert(1)" not in content
    assert "color:red" not in content


def test_ingest_chunks_long_sections(tmp_path):
    doc = tmp_path / "long.txt"
    _write(doc, "drone " * 500)

    node_ids = DocumentIngestor(KnowledgeGraph(), max_chars=600).ingest_file(doc)

    assert len(node_ids) > 1


def test_reingest_is_idempotent(tmp_path):
    doc = tmp_path / "doc.md"
    _write(doc, "# One\nAlpha content.\n# Two\nBeta content.")
    graph = KnowledgeGraph()
    ingestor = DocumentIngestor(graph)

    first = ingestor.ingest_file(doc)
    second = ingestor.ingest_file(doc)

    assert first == second
    assert len(graph.nodes) == 2


def test_ingest_directory_recursively_and_skips_unsupported(tmp_path):
    (tmp_path / "sub").mkdir()
    _write(tmp_path / "a.md", "# A\nAlpha.")
    _write(tmp_path / "sub" / "b.txt", "Beta.")
    _write(tmp_path / "c.docx", "binary-ish")

    report = DocumentIngestor(KnowledgeGraph()).ingest(tmp_path)

    assert len(report.files) == 2
    assert report.chunks == 2
    assert report.skipped == ()
    assert report.to_dict()["chunks"] == 2


def test_ingest_missing_or_unsupported_path_is_skipped(tmp_path):
    report = DocumentIngestor(KnowledgeGraph()).ingest(tmp_path / "nope.md")

    assert report.files == ()
    assert len(report.skipped) == 1


def test_ingest_decodes_cp949_files(tmp_path):
    doc = tmp_path / "korean.txt"
    doc.write_bytes("드론 방어 훈련 계획.".encode("cp949"))
    graph = KnowledgeGraph()

    node_ids = DocumentIngestor(graph).ingest_file(doc)

    assert "드론 방어" in graph.get_node(node_ids[0]).content


def test_ingest_chunks_text_without_spaces(tmp_path):
    doc = tmp_path / "dense.txt"
    _write(doc, "가" * 1500)

    node_ids = DocumentIngestor(KnowledgeGraph(), max_chars=600).ingest_file(doc)

    assert len(node_ids) == 3


def test_ingest_falls_back_on_undecodable_bytes(tmp_path):
    doc = tmp_path / "weird.txt"
    doc.write_bytes(b"drone data \xff\xfe\x81\x00 tail")
    graph = KnowledgeGraph()

    node_ids = DocumentIngestor(graph).ingest_file(doc)

    assert node_ids
    assert "drone data" in graph.get_node(node_ids[0]).content


def test_recall_and_research_use_ingested_documents(tmp_path):
    space = Workspace(tmp_path / "space")
    doc = tmp_path / "doctrine.md"
    _write(doc, "# Swarm Defense\nLayered jamming with interceptor drones covers the low tier.")

    foundation = space.build_foundation()
    DocumentIngestor(foundation.knowledge_graph).ingest(doc)

    recall = MemoryRecall(foundation.knowledge_graph).recall("interceptor drones jamming")
    assert any("doctrine.md" in entry for entry in recall.entries)

    pursuit = foundation.pursue("Swarm defense options", capabilities=("research",))
    assert "doctrine.md" in pursuit.output


def test_cli_ingest_command(tmp_path, monkeypatch, capsys):
    from maios import cli

    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "brief.md", "# Brief\nContent for the graph.")
    monkeypatch.setattr("sys.argv", ["maios", "ingest", str(tmp_path / "brief.md")])
    cli.main()

    out = capsys.readouterr().out
    assert "[ingested]" in out
    assert "files=1 chunks=1" in out
    assert (tmp_path / ".maios" / "knowledge_graph.json").exists()


def test_cli_ingest_without_paths_prints_usage(tmp_path, monkeypatch, capsys):
    import pytest

    from maios import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["maios", "ingest"])
    with pytest.raises(SystemExit):
        cli.main()

    assert "maios ingest" in capsys.readouterr().out


def test_shell_ingest_command(tmp_path):
    from maios.shell import MAIOSShell

    space = Workspace(tmp_path / "space")
    foundation = space.build_foundation()
    doc = tmp_path / "notes.md"
    _write(doc, "# Notes\nShell ingestion works.")
    outputs: list[str] = []
    lines = iter(["/ingest", f"/ingest {doc}", "/exit"])
    MAIOSShell(
        foundation,
        space,
        input_fn=lambda prompt: next(lines),
        output_fn=outputs.append,
    ).run()

    text = "\n".join(outputs)
    assert "usage: /ingest <path>" in text
    assert "ingested:" in text
    assert "files=1 chunks=1" in text
