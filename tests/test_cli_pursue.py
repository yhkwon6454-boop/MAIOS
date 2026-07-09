from __future__ import annotations

import pytest

import maios
from maios import cli


def _run(monkeypatch, *args: str) -> None:
    monkeypatch.setattr("sys.argv", ["maios", *args])
    cli.main()


def test_cli_version(monkeypatch, capsys):
    _run(monkeypatch, "--version")

    assert maios.__version__ in capsys.readouterr().out


def test_cli_without_arguments_prints_usage(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["maios"])

    with pytest.raises(SystemExit):
        cli.main()

    assert "maios pursue" in capsys.readouterr().out


def test_cli_pursue_runs_cognitive_cycles(monkeypatch, capsys):
    _run(monkeypatch, "pursue", "Summarize", "the", "weekly", "report")

    out = capsys.readouterr().out
    assert "[MAIOS] objective: Summarize the weekly report" in out
    assert "observe -> understand -> plan -> act -> reflect -> learn" in out
    assert "[status] COMPLETED" in out
    assert "risk=LOW" in out


def test_cli_pursue_accepts_capability_and_max_cycles_flags(monkeypatch, capsys):
    _run(
        monkeypatch,
        "pursue",
        "Handle",
        "the",
        "task",
        "--capability",
        "execute",
        "--max-cycles",
        "2",
    )

    out = capsys.readouterr().out
    assert "[status] COMPLETED" in out
    assert "[cycles] 1 executed" in out


def test_cli_pursue_high_risk_requires_approval(monkeypatch, capsys):
    _run(monkeypatch, "pursue", "Deploy", "the", "service")

    out = capsys.readouterr().out
    assert "[status] PENDING_APPROVAL" in out
    assert "[cycles] 0 executed" in out


def test_cli_pursue_high_risk_with_approve_flag_completes(monkeypatch, capsys):
    _run(monkeypatch, "pursue", "Deploy", "the", "service", "--approve")

    out = capsys.readouterr().out
    assert "[status] COMPLETED" in out
    assert "approved=True" in out


def test_cli_pursue_without_objective_prints_usage(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["maios", "pursue"])

    with pytest.raises(SystemExit):
        cli.main()

    assert "maios pursue" in capsys.readouterr().out


def test_cli_introspect_reports_self_model(monkeypatch, capsys):
    _run(monkeypatch, "introspect")

    out = capsys.readouterr().out
    assert "identity=maios" in out
    assert "readiness=" in out
    assert "[available]" in out
    assert "governance" in out
