from __future__ import annotations

import pytest

from maios.governance import GovernanceManager
from maios.kernel import Workspace
from maios.shell import MAIOSShell


class FakeIO:
    def __init__(self, lines: list[str]) -> None:
        self.lines = list(lines)
        self.outputs: list[str] = []

    def input_fn(self, prompt: str) -> str:
        if not self.lines:
            raise EOFError
        return self.lines.pop(0)

    def output_fn(self, message: str) -> None:
        self.outputs.append(message)

    @property
    def text(self) -> str:
        return "\n".join(self.outputs)


def _shell(tmp_path, lines: list[str]) -> FakeIO:
    space = Workspace(tmp_path / "space")
    foundation = space.build_foundation(governance=GovernanceManager())
    io = FakeIO(lines)
    MAIOSShell(foundation, space, input_fn=io.input_fn, output_fn=io.output_fn).run()
    return io


def test_shell_exits_on_command(tmp_path):
    io = _shell(tmp_path, ["/exit"])

    assert "MAIOS shell" in io.outputs[0]
    assert io.outputs[-1] == "bye"


def test_shell_exits_cleanly_on_eof(tmp_path):
    io = _shell(tmp_path, [])

    assert io.outputs[-1] == "bye"


def test_shell_pursues_objective_and_persists(tmp_path):
    io = _shell(tmp_path, ["Summarize the meeting", "/exit"])

    assert "[COMPLETED] Summarize the meeting" in io.text
    assert "pursuits=1" in io.text
    space = Workspace(tmp_path / "space")
    assert space.stats()["pursuits"] == 1


def test_shell_session_shares_memory_between_objectives(tmp_path):
    io = _shell(tmp_path, ["First goal", "Second goal", "/history", "/exit"])

    assert "pursuits=2" in io.text
    history = [line for line in io.outputs if line.startswith("[COMPLETED]")]
    assert len(history) >= 2
    assert "(GP-" in io.text


def test_shell_help_and_empty_lines(tmp_path):
    io = _shell(tmp_path, ["", "/help", "/exit"])

    assert "Commands:" in io.text
    assert "/approve" in io.text


def test_shell_introspect_and_evolve(tmp_path):
    io = _shell(tmp_path, ["A goal", "/introspect", "/evolve", "/exit"])

    assert "identity=maios" in io.text
    assert "readiness=" in io.text
    assert "success_rate=1.0" in io.text


def test_shell_history_when_empty(tmp_path):
    io = _shell(tmp_path, ["/history", "/exit"])

    assert "no pursuits yet" in io.text


def test_shell_approve_flow_for_high_risk_goal(tmp_path):
    io = _shell(tmp_path, ["Deploy the new build", "/approve", "/exit"])

    assert "[PENDING_APPROVAL] Deploy the new build" in io.text
    assert "type /approve to re-run with human approval" in io.text
    assert "[COMPLETED] Deploy the new build" in io.text


def test_shell_approve_without_prior_objective(tmp_path):
    io = _shell(tmp_path, ["/approve", "/exit"])

    assert "nothing to approve yet" in io.text


@pytest.mark.parametrize("command", ["quit", "exit", "/quit"])
def test_shell_alternate_exit_commands(tmp_path, command):
    io = _shell(tmp_path, [command])

    assert io.outputs[-1] == "bye"


def test_cli_shell_command_runs_interactive_loop(tmp_path, monkeypatch, capsys):
    from maios import cli

    monkeypatch.chdir(tmp_path)
    answers = iter(["Note the date", "/exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr("sys.argv", ["maios", "shell"])
    cli.main()

    out = capsys.readouterr().out
    assert "MAIOS shell" in out
    assert "[COMPLETED] Note the date" in out
    assert (tmp_path / ".maios" / "pursuits.json").exists()
