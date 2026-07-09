from __future__ import annotations

from maios.adapters.llm_provider import BaseLLMProvider
from maios.kernel import AGIFoundation, CognitiveInterpreter, CognitiveLoop
from maios.kernel.executive_brain import DecisionContext
from maios.kernel.world_model import WorldModel


class ScriptedProvider(BaseLLMProvider):
    name = "scripted"

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


class BrokenProvider(BaseLLMProvider):
    name = "broken"

    def generate(self, prompt: str) -> str:
        raise RuntimeError("provider down")


def _world_context(objective: str = "Test objective"):
    world = WorldModel()
    return world.build_context(DecisionContext(objective))


def test_interpreter_without_provider_returns_none():
    interpreter = CognitiveInterpreter()

    assert interpreter.available is False
    assert interpreter.interpret_situation("Goal", _world_context()) is None
    assert interpreter.reflect_on_outcome("Goal", {"status": "COMPLETED"}, True) is None


def test_interpret_situation_sends_world_state_to_provider():
    provider = ScriptedProvider(["The system is stable; main risk is low capacity."])
    interpreter = CognitiveInterpreter(provider)

    result = interpreter.interpret_situation("Ship release", _world_context("Ship release"))

    assert result == "The system is stable; main risk is low capacity."
    assert "Ship release" in provider.prompts[0]
    assert "Predictions:" in provider.prompts[0]


def test_interpreter_falls_back_on_provider_error_or_empty_text():
    assert (
        CognitiveInterpreter(BrokenProvider()).interpret_situation("Goal", _world_context()) is None
    )
    assert (
        CognitiveInterpreter(ScriptedProvider(["   "])).interpret_situation(
            "Goal", _world_context()
        )
        is None
    )


def test_reflect_on_outcome_parses_summary_and_lessons():
    provider = ScriptedProvider(
        ["The cycle succeeded cleanly.\n- Keep the direct planner.\n- Cache the world state."]
    )
    interpreter = CognitiveInterpreter(provider)

    result = interpreter.reflect_on_outcome(
        "Goal",
        {"status": "COMPLETED"},
        True,
        interpretation="Stable system.",
    )

    assert result == (
        "The cycle succeeded cleanly.",
        ("Keep the direct planner.", "Cache the world state."),
    )
    assert "Stable system." in provider.prompts[0]


def test_reflect_on_outcome_without_summary_returns_none():
    provider = ScriptedProvider(["- only a bullet, no summary"])
    interpreter = CognitiveInterpreter(provider)

    assert interpreter.reflect_on_outcome("Goal", {"status": "COMPLETED"}, True) is None


def test_cognitive_loop_uses_llm_for_understand_act_and_reflect():
    provider = ScriptedProvider(
        [
            "System healthy; no meaningful risk.",
            "The weekly report shows steady progress.",
            "Cycle went well.\n- Reuse this pattern.",
        ]
    )
    loop = CognitiveLoop(llm_provider=provider)

    cycle = loop.run_cycle("LLM cycle")

    understand = cycle.phases[1]
    assert understand.summary == "System healthy; no meaningful risk."
    assert understand.data["interpretation"] == "System healthy; no meaningful risk."
    assert cycle.outcome["output"] == "The weekly report shows steady progress."
    assert cycle.outcome["generated"] is True
    assert cycle.report is not None
    assert cycle.report.summary == "Cycle went well."
    assert cycle.report.improvement_points == ["Reuse this pattern."]
    assert cycle.status == "COMPLETED"


def test_cognitive_loop_keeps_heuristics_when_provider_fails():
    loop = CognitiveLoop(llm_provider=BrokenProvider())

    cycle = loop.run_cycle("Fallback cycle")

    assert cycle.status == "COMPLETED"
    assert "interpretation" not in cycle.phases[1].data
    assert cycle.report is not None
    assert "Cognitive cycle for 'Fallback cycle'" in cycle.report.summary


def test_agi_foundation_reports_llm_capability():
    without_llm = AGIFoundation()
    with_llm = AGIFoundation(llm_provider=ScriptedProvider(["ok", "fine.\n- lesson"]))
    injected = AGIFoundation(
        cognitive_loop=CognitiveLoop(),
        llm_provider=ScriptedProvider(["ok"]),
    )

    assert without_llm.introspect().capabilities["llm"] is False
    assert with_llm.introspect().capabilities["llm"] is True
    assert injected.introspect().capabilities["llm"] is True


def test_cli_pursue_with_mock_llm_prints_understanding(tmp_path, monkeypatch, capsys):
    from maios import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["maios", "pursue", "Review", "the", "logs", "--llm", "mock"],
    )
    cli.main()

    out = capsys.readouterr().out
    assert "[understanding] Mock GPT response:" in out
    assert "[status] COMPLETED" in out


def test_cli_introspect_with_mock_llm_reports_llm_available(tmp_path, monkeypatch, capsys):
    from maios import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["maios", "introspect", "--llm", "mock"])
    cli.main()

    out = capsys.readouterr().out
    assert "llm" in out.split("[available]")[1].splitlines()[0]
