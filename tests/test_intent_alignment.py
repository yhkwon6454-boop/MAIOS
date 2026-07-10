from __future__ import annotations

import json

from maios.governance import GovernanceManager
from maios.kernel import (
    AGIFoundation,
    CommandersIntent,
    GoalPursuit,
    IntentAlignmentChecker,
    Workspace,
)

INTENT = CommandersIntent(
    purpose="적 방어선 돌파로 후속 부대 진출 여건 보장",
    end_state="교량 확보 및 적 화력 무력화 상태",
    key_tasks=("교량 확보", "적 포병 무력화"),
    constraints=("민간 지역 포격 금지", "예비대 무단 투입 금지"),
    acceptable_risks=("야간 기동 간 소부대 고립",),
)


def test_intent_round_trip(tmp_path):
    path = tmp_path / "intent.json"
    path.write_text(json.dumps(INTENT.to_dict(), ensure_ascii=False), encoding="utf-8")

    loaded = CommandersIntent.load(path)

    assert loaded == INTENT


def test_action_supporting_key_task_is_aligned():
    report = IntentAlignmentChecker(INTENT).check("1중대가 교량을 확보하고 통로를 개척한다")

    assert report.verdict == "ALIGNED"
    assert "교량 확보" in report.supported_tasks


def test_action_touching_constraint_is_conflict():
    report = IntentAlignmentChecker(INTENT).check("민간 지역 일대에 대한 포격 준비")

    assert report.verdict == "CONFLICT"
    assert "민간 지역 포격 금지" in report.touched_constraints
    assert "충돌" in report.rationale


def test_constraint_covered_by_accepted_risk_is_not_conflict():
    intent = CommandersIntent(
        key_tasks=("적 후방 교란",),
        constraints=("야간 기동 제한",),
        acceptable_risks=("야간 기동 간 소부대 고립",),
    )

    report = IntentAlignmentChecker(intent).check("야간 기동으로 적 후방 교란 실시")

    assert report.verdict != "CONFLICT"
    assert report.covered_by_risks


def test_unrelated_action_needs_check():
    report = IntentAlignmentChecker(INTENT).check("부대 체육대회 준비")

    assert report.verdict == "CHECK"
    assert "확인" in report.rationale


def test_ontology_widens_alignment_matching(tmp_path):
    from maios.knowledge import OntologyAdapter

    ttl = tmp_path / "onto.ttl"
    ttl.write_text(
        """
@prefix mc:   <http://mc.mil.kr/ontology#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
mc:FireSupport a owl:Class ; rdfs:label "화력지원"@ko .
mc:Artillery rdfs:subClassOf mc:FireSupport ; rdfs:label "포병"@ko .
""",
        encoding="utf-8",
    )
    intent = CommandersIntent(key_tasks=("화력지원 태세 확립",))
    plain = IntentAlignmentChecker(intent).check("포병 사격 준비")
    widened = IntentAlignmentChecker(intent, ontology=OntologyAdapter(ttl)).check("포병 사격 준비")

    assert plain.verdict == "CHECK"
    assert widened.verdict == "ALIGNED"
    assert "화력지원" in widened.expanded_terms


def test_pursue_records_alignment_and_escalates_conflict(tmp_path):
    space = Workspace(tmp_path / "space")
    space.root.mkdir(parents=True)
    space.intent_path.write_text(json.dumps(INTENT.to_dict(), ensure_ascii=False), encoding="utf-8")

    foundation = space.build_foundation(governance=GovernanceManager())

    aligned = foundation.pursue("교량 확보 작전 준비")
    assert aligned.status == "COMPLETED"
    assert aligned.alignment["verdict"] == "ALIGNED"

    conflict = foundation.pursue("민간 지역 포격 계획 수립")
    assert conflict.status == "PENDING_APPROVAL"
    assert conflict.alignment["verdict"] == "CONFLICT"
    assert conflict.governance["risk_level"] == "HIGH"

    approved = foundation.pursue("민간 지역 포격 계획 수립", human_approved=True)
    assert approved.status == "COMPLETED"

    space.save(foundation)
    revived = Workspace(space.root).build_foundation()
    assert revived.pursuits[1].alignment["verdict"] == "CONFLICT"
    assert revived.introspect().capabilities["intent_alignment"] is True


def test_alignment_capability_false_without_intent():
    assert AGIFoundation().introspect().capabilities["intent_alignment"] is False


def test_goal_pursuit_alignment_round_trip():
    pursuit = GoalPursuit(
        objective="x",
        goal_id="g",
        status="COMPLETED",
        alignment={"verdict": "ALIGNED", "rationale": "ok"},
    )

    assert GoalPursuit.from_dict(pursuit.to_dict()).alignment["verdict"] == "ALIGNED"


def test_cli_align_command(tmp_path, monkeypatch, capsys):
    import pytest

    from maios import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["maios", "align", "교량", "확보", "작전"])
    with pytest.raises(SystemExit):
        cli.main()  # intent.json 없음 → 안내 후 종료
    assert "intent.json" in capsys.readouterr().out

    space = Workspace(tmp_path / ".maios")
    space.root.mkdir(parents=True)
    space.intent_path.write_text(json.dumps(INTENT.to_dict(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["maios", "align", "교량", "확보", "작전"])
    cli.main()
    out = capsys.readouterr().out
    assert "[verdict] ALIGNED" in out
    assert "교량 확보" in out


def test_shell_align_command(tmp_path):
    from maios.shell import MAIOSShell

    space = Workspace(tmp_path / "space")
    space.root.mkdir(parents=True)
    space.intent_path.write_text(json.dumps(INTENT.to_dict(), ensure_ascii=False), encoding="utf-8")
    foundation = space.build_foundation()
    outputs: list[str] = []
    lines = iter(["/align", "/align 민간 지역 포격 준비", "/exit"])
    MAIOSShell(
        foundation,
        space,
        input_fn=lambda prompt: next(lines),
        output_fn=outputs.append,
    ).run()

    text = "\n".join(outputs)
    assert "usage: /align <action>" in text
    assert "[CONFLICT]" in text
