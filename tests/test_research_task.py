from __future__ import annotations

import pytest

from maios.research import ResearchEngine, ResearchSource, ResearchTask


def test_research_task_tracks_status_and_timestamps():
    task = ResearchTask(question="How should MAIOS research agents coordinate?")
    created = task.updated_at

    task.mark("DECOMPOSED")

    assert task.status == "DECOMPOSED"
    assert task.updated_at >= created


def test_research_engine_defines_and_decomposes_questions():
    engine = ResearchEngine()

    task = engine.define_question("AI planning and memory")
    sub_questions = engine.decompose(task)

    assert task.task_id in engine.tasks
    assert sub_questions == ["AI planning", "memory"]
    assert task.status == "DECOMPOSED"
    assert engine.memory_kernel.session_memory[-1]["question"] == "AI planning and memory"


def test_research_engine_rejects_empty_questions():
    engine = ResearchEngine()

    with pytest.raises(ValueError, match="Research question is required"):
        engine.define_question("   ")


def test_research_source_summary_truncates_long_content():
    source = ResearchSource(title="Long", content="x" * 200)

    summary = source.summary(max_length=20)

    assert summary == f"{'x' * 17}..."
    assert source.to_dict()["title"] == "Long"
