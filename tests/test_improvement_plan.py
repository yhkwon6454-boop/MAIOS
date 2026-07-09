from __future__ import annotations

from maios.reflection import ImprovementPlan, ReflectionRecord, SelfImprovementEngine


def test_improvement_plan_serializes_and_formats_markdown():
    plan = ImprovementPlan(
        target="research",
        actions=("Increase source coverage.",),
        prompt_updates=("Require evidence citations.",),
        priority="high",
        metrics_baseline={"failure_count": 2.0},
        source_record_ids=("record-1",),
    )

    data = plan.to_dict()
    markdown = plan.to_markdown()

    assert data["target"] == "research"
    assert data["priority"] == "high"
    assert "# Improvement Plan: research" in markdown
    assert "- Increase source coverage." in markdown
    assert "- Require evidence citations." in markdown


def test_self_improvement_generates_actionable_plan_from_record():
    engine = SelfImprovementEngine()
    record = ReflectionRecord(
        subject_id="task-1",
        source_type="research",
        status="FAILED",
        failures=("No findings were generated.",),
        bottlenecks=("No sources were collected.",),
        repeated_mistakes=("no sources were collected.",),
        metrics={"failure_count": 1.0},
    )

    plan = engine.generate_plan(record, target="research task")

    assert plan.priority == "high"
    assert "Increase source collection breadth for weak research areas." in plan.actions
    assert "Add a finding extraction pass before final report generation." in plan.actions
    assert "Require cited evidence before summarizing findings." in plan.prompt_updates
    assert engine.plans == [plan]


def test_self_improvement_prompt_evolution_strategies_and_prompt_update():
    engine = SelfImprovementEngine()
    plan = ImprovementPlan(
        target="prompt",
        actions=("Improve validation.",),
        prompt_updates=("Add failure-mode checks before marking tasks complete.",),
    )

    appended = engine.evolve_prompt("Base prompt", plan)
    prepended = engine.evolve_prompt("Base prompt", plan, strategy="prepend")
    replaced = engine.evolve_prompt("Base prompt", plan, strategy="replace")

    assert appended.startswith("Base prompt")
    assert prepended.startswith("Improvement guidance:")
    assert "Updated operating guidance" in replaced
    assert engine.prompt_evolution_strategies(()) == [
        "Preserve current prompts and monitor future regressions."
    ]
