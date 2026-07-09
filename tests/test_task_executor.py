from __future__ import annotations

from maios.adapters.llm_provider import BaseLLMProvider
from maios.kernel import TaskExecutor, Workspace
from maios.kernel.executive_brain import DecisionContext, ExecutiveBrain


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


def test_task_executor_without_provider_returns_none():
    executor = TaskExecutor()

    assert executor.available is False
    assert executor.execute("Summarize the report") is None


def test_task_executor_produces_deliverable_with_context():
    provider = ScriptedProvider(["Summary: all systems nominal."])
    executor = TaskExecutor(provider)

    result = executor.execute(
        "Summarize the report",
        interpretation="Stable situation.",
        capabilities=("summarize",),
    )

    assert result == {
        "status": "COMPLETED",
        "planner": "direct",
        "output": "Summary: all systems nominal.",
        "generated": True,
    }
    prompt = provider.prompts[0]
    assert "Summarize the report" in prompt
    assert "Stable situation." in prompt
    assert "summarize" in prompt


def test_task_executor_falls_back_on_error_or_empty_output():
    assert TaskExecutor(BrokenProvider()).execute("Goal") is None
    assert TaskExecutor(ScriptedProvider(["   "])).execute("Goal") is None


def test_executive_brain_direct_execution_uses_task_executor():
    provider = ScriptedProvider(["Translated text."])
    brain = ExecutiveBrain(task_executor=TaskExecutor(provider))

    decision = brain.execute(DecisionContext("Translate the memo"))

    assert decision.outcome["output"] == "Translated text."
    assert decision.outcome["generated"] is True


def test_executive_brain_echoes_objective_when_executor_unavailable():
    decision = ExecutiveBrain().execute(DecisionContext("Echo task"))

    assert decision.outcome["output"] == "Echo task"
    assert "generated" not in decision.outcome


def test_pursuit_records_generated_output_and_workspace_saves_artifact(tmp_path):
    provider = ScriptedProvider(
        [
            "Stable situation.",
            "Deliverable: three-point action plan.",
            "Went well.\n- Keep the plan format.",
        ]
    )
    space = Workspace(tmp_path / "space")
    agi = space.build_foundation(llm_provider=provider)

    pursuit = agi.pursue("Draft an action plan")
    space.save(agi)

    assert pursuit.output == "Deliverable: three-point action plan."
    assert agi.introspect().capabilities["task_execution"] is True
    artifact = space.artifact_path(pursuit)
    assert artifact.exists()
    text = artifact.read_text(encoding="utf-8")
    assert "Draft an action plan" in text
    assert "three-point action plan" in text

    revived = Workspace(space.root).build_foundation()
    assert revived.pursuits[0].output == "Deliverable: three-point action plan."


def test_cli_pursue_with_mock_llm_writes_artifact(tmp_path, monkeypatch, capsys):
    from maios import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["maios", "pursue", "Draft", "a", "note", "--llm", "mock"])
    cli.main()

    out = capsys.readouterr().out
    assert "[output]" in out
    assert "[artifact]" in out
    artifacts = list((tmp_path / ".maios" / "artifacts").glob("GP-*.md"))
    assert len(artifacts) == 1
