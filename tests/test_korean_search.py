from __future__ import annotations

from maios.knowledge import KnowledgeGraph


def _graph_with_corpus() -> KnowledgeGraph:
    graph = KnowledgeGraph()
    graph.add_node(
        title="러우전 교훈",
        content="우크라이나 전쟁에서 드론이 포병 관측과 타격을 지배했다.",
        node_type="document",
        auto_link=False,
        merge_duplicates=False,
    )
    graph.add_node(
        title="군주론 요약",
        content="마키아벨리는 권력의 획득과 유지를 냉정하게 분석했다.",
        node_type="document",
        auto_link=False,
        merge_duplicates=False,
    )
    graph.add_node(
        title="요리 노트",
        content="된장찌개는 멸치 육수가 기본이다.",
        node_type="document",
        auto_link=False,
        merge_duplicates=False,
    )
    return graph


def test_tokens_include_korean_bigrams():
    graph = KnowledgeGraph()

    tokens = graph._tokens("드론 전쟁과 AI 시대")

    assert "드론" in tokens
    assert "전쟁" in tokens
    assert "쟁과" in tokens
    assert not any(token == "ai" for token in tokens)  # short ascii filtered


def test_korean_query_ranks_relevant_document_first():
    graph = _graph_with_corpus()

    results = graph.semantic_search("우크라이나 전쟁의 드론 교훈", top_k=3)

    assert results
    assert results[0].title == "러우전 교훈"


def test_korean_query_for_other_topic_ranks_differently():
    graph = _graph_with_corpus()

    results = graph.semantic_search("마키아벨리 권력 분석", top_k=1)

    assert results[0].title == "군주론 요약"


def test_idf_prefers_rare_terms_over_common_ones():
    graph = KnowledgeGraph()
    for index in range(5):
        graph.add_node(
            title=f"공통 문서 {index}",
            content="전쟁 이야기 공통 내용.",
            node_type="document",
            auto_link=False,
            merge_duplicates=False,
        )
    graph.add_node(
        title="희귀 문서",
        content="전쟁 이야기 그리고 무인기 통제권 서술.",
        node_type="document",
        auto_link=False,
        merge_duplicates=False,
    )

    results = graph.semantic_search("전쟁 무인기 통제권", top_k=1)

    assert results[0].title == "희귀 문서"


def test_token_cache_refreshes_after_node_update():
    graph = KnowledgeGraph()
    node = graph.add_node(
        title="갱신 문서",
        content="초기 내용은 항공모함 이야기.",
        node_type="document",
        auto_link=False,
    )

    assert graph.semantic_search("항공모함", top_k=1)

    node.content = "이제는 잠수함 이야기."
    node.updated_at = "2999-01-01T00:00:00+00:00"
    graph._invalidate_search_index()

    assert graph.semantic_search("잠수함", top_k=1)
    assert not graph.semantic_search("항공모함", top_k=1)


def test_term_frequency_breaks_ties_between_matching_documents():
    graph = KnowledgeGraph()
    graph.add_node(
        title="스치듯 언급",
        content="여러 주제를 다루다가 드론을 한 번 언급하고 다른 이야기로 넘어간다.",
        node_type="document",
        auto_link=False,
        merge_duplicates=False,
    )
    graph.add_node(
        title="집중 분석",
        content="드론 방어를 다룬다. 드론 탐지, 드론 요격, 드론 전파방해까지 드론 중심 서술.",
        node_type="document",
        auto_link=False,
        merge_duplicates=False,
    )

    results = graph.semantic_search("드론", top_k=2)

    assert results[0].title == "집중 분석"


def test_token_counts_count_occurrences():
    graph = KnowledgeGraph()

    counts = graph._token_counts("drone drone drone 전쟁 전쟁")

    assert counts["drone"] == 3
    assert counts["전쟁"] == 2


def test_recall_works_for_korean_documents(tmp_path):
    from maios.kernel import DocumentIngestor, MemoryRecall

    doc = tmp_path / "교리.md"
    doc.write_text(
        "# 드론 방어\n계층화된 전파방해와 요격 드론이 저고도를 담당한다.",
        encoding="utf-8",
    )
    graph = KnowledgeGraph()
    DocumentIngestor(graph).ingest(doc)

    recall = MemoryRecall(graph).recall("드론 방어 훈련 준비")

    assert recall.entries
    assert "교리.md" in recall.entries[0]
