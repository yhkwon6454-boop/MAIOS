from __future__ import annotations

from maios.kernel import MemoryRecall, Workspace
from maios.knowledge import KnowledgeGraph, OntologyAdapter

SAMPLE_TTL = """
@prefix mc:   <http://mc.mil.kr/ontology#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .

mc:CommandersIntent a owl:Class ; rdfs:label "지휘관의도"@ko .
mc:Purpose  a owl:Class ; rdfs:label "목적"@ko .
mc:KeyTask  a owl:Class ; rdfs:label "핵심과업"@ko .
mc:hasPurpose a owl:ObjectProperty ; rdfs:label "목적을가짐"@ko ;
    rdfs:domain mc:CommandersIntent ; rdfs:range mc:Purpose .
mc:hasKeyTask a owl:ObjectProperty ; rdfs:label "핵심과업을가짐"@ko ;
    rdfs:domain mc:CommandersIntent ; rdfs:range mc:KeyTask .

mc:FireSupport a owl:Class ; rdfs:label "화력지원"@ko .
mc:Artillery rdfs:subClassOf mc:FireSupport ; rdfs:label "포병"@ko .
mc:K9 a mc:Artillery ; rdfs:label "K9자주포"@ko .

mc:Intent1  a mc:CommandersIntent ; rdfs:label "작전의도1"@ko ; mc:hasPurpose mc:Purpose1 .
mc:Purpose1 a mc:Purpose ; rdfs:label "적방어선돌파"@ko .
"""


def _write_ttl(tmp_path, name="onto.ttl"):
    path = tmp_path / name
    path.write_text(SAMPLE_TTL, encoding="utf-8")
    return path


def test_adapter_without_path_is_unavailable():
    adapter = OntologyAdapter()

    assert adapter.available is False
    assert adapter.expand_query("아무 질의") == ()


def test_adapter_handles_missing_and_invalid_files(tmp_path):
    missing = OntologyAdapter(tmp_path / "nope.ttl")
    assert missing.available is False
    assert "not found" in missing.error

    bad = tmp_path / "bad.ttl"
    bad.write_text("이것은 터틀이 아님 @@@", encoding="utf-8")
    broken = OntologyAdapter(bad)
    assert broken.available is False
    assert "parse" in broken.error


def test_adapter_builds_label_neighborhood(tmp_path):
    adapter = OntologyAdapter(_write_ttl(tmp_path))

    assert adapter.available
    assert "지휘관의도" in adapter.labels()
    related = adapter.related("포병")
    assert "화력지원" in related
    assert "K9자주포" in related


def test_adapter_links_labeled_instance_triples(tmp_path):
    adapter = OntologyAdapter(_write_ttl(tmp_path))

    assert "적방어선돌파" in adapter.related("작전의도1")


def test_adapter_reports_missing_rdflib(tmp_path, monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "rdflib", None)
    adapter = OntologyAdapter(_write_ttl(tmp_path))

    assert adapter.available is False
    assert "rdflib" in adapter.error


def test_expand_query_matches_labels_despite_spacing(tmp_path):
    adapter = OntologyAdapter(_write_ttl(tmp_path))

    expansions = adapter.expand_query("지휘관 의도 명세를 점검")

    assert "목적" in expansions
    assert "핵심과업" in expansions
    assert "지휘관의도" not in expansions  # 이미 질의에 언급된 용어는 제외


def test_recall_finds_documents_via_ontology_expansion(tmp_path):
    graph = KnowledgeGraph()
    graph.add_node(
        title="사격 절차",
        content="K9자주포 사격 절차와 포병 운용 지침.",
        node_type="document",
        auto_link=False,
    )
    query = "화력지원 계획 수립"

    plain = MemoryRecall(graph).recall(query)
    assert not plain.entries  # 표층 토큰 겹침 없음

    adapter = OntologyAdapter(_write_ttl(tmp_path))
    expanded = MemoryRecall(graph, ontology=adapter).recall(query)

    assert expanded.entries
    assert "사격 절차" in expanded.entries[0]
    assert "포병" in expanded.expanded_terms or "K9자주포" in expanded.expanded_terms


def test_workspace_auto_detects_ontology(tmp_path):
    space = Workspace(tmp_path / "space")
    space.root.mkdir(parents=True)
    _write_ttl(space.root, "ontology.ttl")

    foundation = space.build_foundation()

    assert foundation.introspect().capabilities["ontology"] is True

    foundation.knowledge_graph.add_node(
        title="포병 문서",
        content="포병 진지 변환과 K9자주포 정비 주기.",
        node_type="document",
        auto_link=False,
    )
    pursuit = foundation.pursue("화력지원 태세 점검")
    cycle = foundation.cognitive_loop.cycles[-1]
    understand = cycle.phases[1]

    assert pursuit.success
    assert understand.data.get("ontology_expanded")
    assert any("포병 문서" in entry for entry in understand.data.get("recalled", []))


def test_foundation_without_ontology_reports_capability_false(tmp_path):
    space = Workspace(tmp_path / "space")

    assert space.build_foundation().introspect().capabilities["ontology"] is False


def test_mentions_and_neighborhood(tmp_path):
    adapter = OntologyAdapter(_write_ttl(tmp_path))

    assert adapter.mentions("포병과 K9 자주포 배치") == ("K9자주포", "포병")
    assert "제한과충돌" not in adapter.mentions("일반 행정 업무")
    assert "제한사항" in adapter.neighborhood("제한사항")


def test_ontology_risk_labels_escalate_governance(tmp_path):
    from maios.governance import GovernanceManager
    from maios.kernel import AGIFoundation

    adapter = OntologyAdapter(_write_full_ttl(tmp_path))
    agi = AGIFoundation(
        governance=GovernanceManager(),
        ontology=adapter,
        ontology_risk_labels=("제한사항",),
    )

    direct = agi.pursue("제한사항 완화 검토")
    assert direct.status == "PENDING_APPROVAL"
    assert direct.governance["risk_level"] == "HIGH"

    neighbor = agi.pursue("소대 기동이 제한과 충돌하는지 판단")
    assert neighbor.status == "PENDING_APPROVAL"

    unrelated = agi.pursue("주간 정비 일지 요약")
    assert unrelated.status == "COMPLETED"

    approved = agi.pursue("제한사항 완화 검토", human_approved=True)
    assert approved.status == "COMPLETED"


def test_risk_labels_without_ontology_have_no_effect():
    from maios.governance import GovernanceManager
    from maios.kernel import AGIFoundation

    agi = AGIFoundation(
        governance=GovernanceManager(),
        ontology_risk_labels=("제한사항",),
    )

    assert agi.pursue("제한사항 완화 검토").status == "COMPLETED"


def test_project_pursuit_respects_ontology_risk(tmp_path):
    from maios.governance import GovernanceManager
    from maios.kernel import AGIFoundation

    adapter = OntologyAdapter(_write_full_ttl(tmp_path))
    agi = AGIFoundation(
        governance=GovernanceManager(),
        ontology=adapter,
        ontology_risk_labels=("수용가능위험",),
    )

    project = agi.pursue_project("수용가능위험 범위 재설정 계획")
    assert project.status == "PENDING_APPROVAL"


def test_workspace_reads_governance_config(tmp_path):
    import json

    from maios.governance import GovernanceManager

    space = Workspace(tmp_path / "space")
    space.root.mkdir(parents=True)
    _write_full_ttl(space.root, "ontology.ttl")
    (space.root / "governance.json").write_text(
        json.dumps({"ontology_risk_labels": ["제한사항"]}, ensure_ascii=False),
        encoding="utf-8",
    )

    foundation = space.build_foundation(governance=GovernanceManager())
    pursuit = foundation.pursue("제한사항 초과 기동 승인")

    assert pursuit.status == "PENDING_APPROVAL"


def _write_full_ttl(tmp_path, name="onto.ttl"):
    path = tmp_path / name
    path.write_text(
        SAMPLE_TTL + """
mc:Constraint a owl:Class ; rdfs:label "제한사항"@ko .
mc:AcceptableRisk a owl:Class ; rdfs:label "수용가능위험"@ko .
mc:Action a owl:Class ; rdfs:label "부하의 행동"@ko .
mc:conflictsWith a owl:ObjectProperty ; rdfs:label "제한과충돌"@ko ;
    rdfs:domain mc:Action ; rdfs:range mc:Constraint .
""",
        encoding="utf-8",
    )
    return path
