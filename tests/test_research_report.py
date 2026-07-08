from __future__ import annotations

from maios.research import ResearchReport, ResearchSource


def test_research_report_serializes_to_dict():
    source = ResearchSource(
        title="MAIOS architecture",
        content="Agents coordinate through shared memory.",
        url="https://example.test/maios",
    )
    report = ResearchReport(
        question="How do agents coordinate?",
        sub_questions=("What is shared?",),
        findings=("Shared memory coordinates agents.",),
        gaps=("Need production validation.",),
        sources=(source,),
    )

    data = report.to_dict()

    assert data["question"] == "How do agents coordinate?"
    assert data["sources"][0]["title"] == "MAIOS architecture"
    assert data["gaps"] == ["Need production validation."]


def test_research_report_formats_markdown():
    source = ResearchSource(title="Source", content="Evidence")
    report = ResearchReport(
        question="What matters?",
        sub_questions=("What evidence exists?",),
        findings=("Evidence exists.",),
        gaps=("No gaps.",),
        sources=(source,),
    )

    markdown = report.to_markdown()

    assert "# Research Report: What matters?" in markdown
    assert "- What evidence exists?" in markdown
    assert "- Evidence exists." in markdown
    assert "- Source" in markdown
