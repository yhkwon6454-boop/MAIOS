from __future__ import annotations

from maios.kernel import AGIFoundation, Workspace
from maios.knowledge import KnowledgeGraph
from maios.research import KnowledgeGraphSourceCollector


def _seeded_graph() -> KnowledgeGraph:
    graph = KnowledgeGraph()
    graph.add_node(
        title="Drone swarm lessons",
        content="Swarm attacks overwhelmed point defenses in three exercises.",
        node_type="experience",
    )
    graph.add_node(
        title="Counter-drone concept",
        content="Layered jamming with interceptor drones covers the low tier.",
        node_type="concept",
    )
    graph.add_node(
        title="World State: WM-9",
        content="{'noise': 'drone swarm state dump'}",
        node_type="world_state",
    )
    return graph


def test_collector_returns_graph_sources_and_skips_state_dumps():
    collector = KnowledgeGraphSourceCollector(_seeded_graph())

    sources = collector.collect("drone swarm defense", limit=5)

    titles = [source.title for source in sources]
    assert "Drone swarm lessons" in titles
    assert "Counter-drone concept" in titles
    assert all("World State" not in title for title in titles)
    assert all(source.metadata["node_id"] for source in sources)


def test_collector_respects_limit_and_empty_graph():
    assert KnowledgeGraphSourceCollector(KnowledgeGraph()).collect("anything") == []
    sources = KnowledgeGraphSourceCollector(_seeded_graph()).collect("drone", limit=1)
    assert len(sources) == 1


def test_workspace_foundation_wires_research_engine(tmp_path):
    space = Workspace(tmp_path / "space")
    foundation = space.build_foundation()

    assert foundation.executive_brain.research_engine is not None
    assert foundation.introspect().capabilities["research"] is True
    assert AGIFoundation().introspect().capabilities["research"] is False


def test_research_pursuit_produces_report_from_accumulated_knowledge(tmp_path):
    space = Workspace(tmp_path / "space")
    first = space.build_foundation()
    first.knowledge_graph.add_node(
        title="Drone swarm lessons",
        content="Swarm attacks overwhelmed point defenses in three exercises.",
        node_type="experience",
    )
    space.save(first)

    second = space.build_foundation()
    pursuit = second.pursue("Drone swarm defense options", capabilities=("research",))
    space.save(second)

    assert pursuit.status == "COMPLETED"
    assert pursuit.output.startswith("# Research Report:")
    assert "Drone swarm lessons" in pursuit.output
    artifact = space.artifact_path(pursuit)
    assert artifact.exists()
    assert "Research Report" in artifact.read_text(encoding="utf-8")


def test_cli_research_command(tmp_path, monkeypatch, capsys):
    from maios import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["maios", "research", "Drone", "defense", "options"])
    cli.main()

    out = capsys.readouterr().out
    assert "# Research Report: Drone defense options" in out
    assert "[artifact]" in out
    assert "[status] COMPLETED" in out


def test_shell_research_command(tmp_path):
    from maios.shell import MAIOSShell

    space = Workspace(tmp_path / "space")
    foundation = space.build_foundation()
    outputs: list[str] = []
    lines = iter(["/research", "/research Drone defense", "/exit"])
    MAIOSShell(
        foundation,
        space,
        input_fn=lambda prompt: next(lines),
        output_fn=outputs.append,
    ).run()

    text = "\n".join(outputs)
    assert "usage: /research <question>" in text
    assert "[COMPLETED] Drone defense" in text
    assert "# Research Report: Drone defense" in text
