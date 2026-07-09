from __future__ import annotations

from maios.kernel import GoalPursuit, Workspace


def test_workspace_persists_memory_across_restarts(tmp_path):
    root = tmp_path / "space"

    first = Workspace(root)
    agi = first.build_foundation()
    pursuit = agi.pursue("Remember this goal")
    first.save(agi)

    second = Workspace(root)
    revived = second.build_foundation()

    assert [p.pursuit_id for p in revived.pursuits] == [pursuit.pursuit_id]
    assert revived.pursuits[0].lessons == pursuit.lessons
    assert revived.knowledge_graph.get_node(pursuit.pursuit_id) is not None


def test_workspace_accumulates_pursuits_over_sessions(tmp_path):
    root = tmp_path / "space"

    for objective in ("First goal", "Second goal"):
        space = Workspace(root)
        agi = space.build_foundation()
        agi.pursue(objective)
        space.save(agi)

    stats = Workspace(root).stats()
    assert stats["pursuits"] == 2
    assert stats["nodes"] > 0

    revived = Workspace(root).build_foundation()
    report = revived.evolve()
    assert report["pursuits"] == 2
    assert report["success_rate"] == 1.0


def test_workspace_stats_for_missing_directory(tmp_path):
    space = Workspace(tmp_path / "nowhere")

    assert space.exists() is False
    assert space.stats() == {"nodes": 0, "pursuits": 0}


def test_goal_pursuit_from_dict_round_trip():
    pursuit = GoalPursuit(
        objective="Round trip",
        goal_id="MG-1",
        status="COMPLETED",
        cycle_ids=("CC-1", "CC-2"),
        lessons=("Keep it",),
        governance={"approved": True},
    )

    restored = GoalPursuit.from_dict(pursuit.to_dict())

    assert restored.to_dict() == pursuit.to_dict()
    assert restored.success


def test_goal_pursuit_from_dict_fills_missing_identifiers():
    restored = GoalPursuit.from_dict({"objective": "Sparse"})

    assert restored.objective == "Sparse"
    assert restored.pursuit_id.startswith("GP-")
    assert restored.created_at


def test_cli_pursue_shares_memory_between_runs(tmp_path, monkeypatch, capsys):
    from maios import cli

    monkeypatch.chdir(tmp_path)
    for objective in ("Alpha", "Beta"):
        monkeypatch.setattr("sys.argv", ["maios", "pursue", objective])
        cli.main()

    out = capsys.readouterr().out
    assert "pursuits=1" in out
    assert "pursuits=2" in out
    assert (tmp_path / ".maios" / "pursuits.json").exists()
    assert (tmp_path / ".maios" / "knowledge_graph.json").exists()


def test_cli_workspace_flag_uses_custom_directory(tmp_path, monkeypatch, capsys):
    from maios import cli

    monkeypatch.chdir(tmp_path)
    custom = tmp_path / "custom-space"
    monkeypatch.setattr(
        "sys.argv",
        ["maios", "pursue", "Custom", "home", "--workspace", str(custom)],
    )
    cli.main()
    monkeypatch.setattr("sys.argv", ["maios", "introspect", "--workspace", str(custom)])
    cli.main()

    out = capsys.readouterr().out
    assert (custom / "pursuits.json").exists()
    assert not (tmp_path / ".maios").exists()
    assert out.count("pursuits=1") == 2
