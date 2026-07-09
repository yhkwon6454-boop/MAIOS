from __future__ import annotations

from maios.adapters.llm_provider import BaseLLMProvider
from maios.governance import GovernanceManager
from maios.kernel import GoalDecomposer, Workspace


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


def test_decomposer_without_provider_returns_none():
    decomposer = GoalDecomposer()

    assert decomposer.available is False
    assert decomposer.decompose("Write a book") is None
    assert decomposer.synthesize("Write a book", [("a", "b")]) is None


def test_decompose_parses_bullets_and_numbered_lines():
    provider = ScriptedProvider(
        ["Plan:\n- Outline the chapters\n1. Draft chapter one\n2) Draft chapter two\n- \nDone."]
    )

    subgoals = GoalDecomposer(provider).decompose("Write a book")

    assert subgoals == (
        "Outline the chapters",
        "Draft chapter one",
        "Draft chapter two",
    )


def test_decompose_caps_subgoals_and_rejects_short_lists():
    many = "\n".join(f"- Step {index}" for index in range(8))
    assert len(GoalDecomposer(ScriptedProvider([many])).decompose("Big goal", 3)) == 3
    assert GoalDecomposer(ScriptedProvider(["- Only one step"])).decompose("Goal") is None
    assert GoalDecomposer(ScriptedProvider(["No list at all."])).decompose("Goal") is None
    assert GoalDecomposer(BrokenProvider()).decompose("Goal") is None


def test_synthesize_combines_results_and_handles_failures():
    provider = ScriptedProvider(["Final integrated brief."])
    result = GoalDecomposer(provider).synthesize(
        "Write brief", [("part one", "Alpha."), ("part two", "Beta.")]
    )

    assert result == "Final integrated brief."
    assert "Alpha." in provider.prompts[0]
    assert "Beta." in provider.prompts[0]
    assert GoalDecomposer(ScriptedProvider(["x"])).synthesize("Goal", [("a", "")]) is None
    assert GoalDecomposer(BrokenProvider()).synthesize("Goal", [("a", "b")]) is None


def test_pursue_project_chains_subgoals_and_synthesizes(tmp_path):
    provider = ScriptedProvider(
        [
            "- Research the topic\n- Write the memo",
            "Understood research.",
            "Research notes: drones matter.",
            "Fine.\n- Cite sources.",
            "Understood writing.",
            "Memo: drones matter, with sources.",
            "Fine.\n- Keep it short.",
            "Final memo combining research and writing.",
        ]
    )
    space = Workspace(tmp_path / "space")
    agi = space.build_foundation(llm_provider=provider)

    project = agi.pursue_project("Produce a drone memo")
    space.save(agi)

    assert project.status == "COMPLETED"
    assert project.subgoals == ("Research the topic", "Write the memo")
    assert len(project.pursuit_ids) == 2
    assert project.output == "Final memo combining research and writing."
    second_act_prompt = provider.prompts[5]
    assert "Earlier results in this project" in second_act_prompt
    assert "Research notes: drones matter." in second_act_prompt
    artifact = space.project_artifact_path(project)
    assert artifact.exists()
    assert "Final memo" in artifact.read_text(encoding="utf-8")

    revived = space.build_foundation()
    assert revived.projects[0].project_id == project.project_id
    assert revived.projects[0].output == project.output


def test_pursue_project_without_llm_falls_back_to_single_goal(tmp_path):
    space = Workspace(tmp_path / "space")
    agi = space.build_foundation()

    project = agi.pursue_project("Simple objective")

    assert project.status == "COMPLETED"
    assert project.subgoals == ("Simple objective",)
    assert len(project.pursuit_ids) == 1
    assert project.output == ""


def test_pursue_project_stops_after_failed_subgoal():
    from typing import Any

    from maios.kernel import AGIFoundation, CognitiveLoop
    from maios.kernel.executive_brain import DecisionContext, ExecutiveBrain, ExecutiveDecision

    class FailingBrain(ExecutiveBrain):
        def _execute_decision(
            self,
            decision: ExecutiveDecision,
            context: DecisionContext,
        ) -> dict[str, Any]:
            return {"status": "FAILED", "error": "boom", "planner": "direct"}

    agi = AGIFoundation(cognitive_loop=CognitiveLoop(executive_brain=FailingBrain()))
    agi.decomposer = GoalDecomposer(ScriptedProvider(["- Step one\n- Step two"]))

    project = agi.pursue_project("Two step plan")

    assert project.status == "FAILED"
    assert not project.success
    assert project.subgoals == ("Step one", "Step two")
    assert len(project.pursuit_ids) == 1
    assert project.output == ""


def test_pursue_project_high_risk_requires_approval(tmp_path):
    space = Workspace(tmp_path / "space")
    agi = space.build_foundation(governance=GovernanceManager())

    project = agi.pursue_project("Deploy the fleet")

    assert project.status == "PENDING_APPROVAL"
    assert project.pursuit_ids == ()
    assert agi.pursuits == []

    approved = agi.pursue_project("Deploy the fleet", human_approved=True)
    assert approved.status == "COMPLETED"


def test_prior_lessons_capped_at_limit():
    from maios.kernel import AGIFoundation, GoalPursuit

    agi = AGIFoundation()
    for index in range(7):
        agi.pursuits.append(
            GoalPursuit(
                objective=f"Goal {index}",
                goal_id=f"MG-{index}",
                status="COMPLETED",
                lessons=(f"Lesson {index}",),
            )
        )

    lessons = agi._prior_lessons()

    assert len(lessons) == 5
    assert lessons[0] == "Lesson 6"


def test_introspect_reports_goal_decomposition_capability():
    from maios.kernel import AGIFoundation

    assert AGIFoundation().introspect().capabilities["goal_decomposition"] is False
    with_llm = AGIFoundation(llm_provider=ScriptedProvider([]))
    assert with_llm.introspect().capabilities["goal_decomposition"] is True


def test_cli_project_command_with_mock_llm(tmp_path, monkeypatch, capsys):
    from maios import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["maios", "project", "Write", "a", "defense", "note", "--llm", "mock"],
    )
    cli.main()

    out = capsys.readouterr().out
    assert "[MAIOS] project: Write a defense note" in out
    assert "[subgoals] 1" in out
    assert "[artifact]" in out
    assert "[status] COMPLETED" in out


def test_cli_project_without_objective_prints_usage(tmp_path, monkeypatch, capsys):
    from maios import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["maios", "project"])
    import pytest

    with pytest.raises(SystemExit):
        cli.main()

    assert "maios project" in capsys.readouterr().out


def test_shell_project_command(tmp_path):
    from maios.shell import MAIOSShell

    space = Workspace(tmp_path / "space")
    foundation = space.build_foundation()
    outputs: list[str] = []
    lines = iter(["/project Plan the week", "/project", "/exit"])
    MAIOSShell(
        foundation,
        space,
        input_fn=lambda prompt: next(lines),
        output_fn=outputs.append,
    ).run()

    text = "\n".join(outputs)
    assert "[COMPLETED] project: Plan the week" in text
    assert "1. [COMPLETED] Plan the week" in text
    assert "usage: /project <objective>" in text
