import pytest

from maios.knowledge import KNOWLEDGE_RELATIONSHIPS, KnowledgeGraph


def test_automatic_concept_linking_creates_similarity_edges():
    graph = KnowledgeGraph(auto_link_threshold=0.1)
    first = graph.add_node("Agent Memory", "Agents remember evidence and outcomes.")
    second = graph.add_node("Memory Retrieval", "Agents retrieve remembered evidence.")

    edges = graph.edges_for(second.node_id, ["similar_to"], direction="both")

    assert edges
    assert {first.node_id, second.node_id} == {edges[0].source_id, edges[0].target_id}


def test_metadata_relationships_create_semantic_edges():
    graph = KnowledgeGraph()
    evidence = graph.add_node("Evidence", "Evidence supports research conclusions.")
    prerequisite = graph.add_node("Prerequisite", "Research depends on context.")
    conclusion = graph.add_node(
        "Conclusion",
        "Research conclusion derived from evidence.",
        metadata={"derived_from": evidence.node_id, "depends_on": [prerequisite.node_id]},
    )

    derived_edge = graph.edges_for(conclusion.node_id, ["derived_from"], direction="out")[0]
    depends_edge = graph.edges_for(conclusion.node_id, ["depends_on"], direction="out")[0]

    assert derived_edge.target_id == evidence.node_id
    assert depends_edge.target_id == prerequisite.node_id
    assert KNOWLEDGE_RELATIONSHIPS == {
        "supports",
        "contradicts",
        "depends_on",
        "derived_from",
        "similar_to",
        "part_of",
    }


def test_rejects_unknown_relationships():
    graph = KnowledgeGraph()
    source = graph.add_node("A", "Alpha concept")
    target = graph.add_node("B", "Beta concept")

    with pytest.raises(ValueError):
        graph.add_edge(source.node_id, target.node_id, "unrelated")


def test_rejects_invalid_nodes_and_edges():
    graph = KnowledgeGraph()

    with pytest.raises(ValueError):
        graph.add_node("", "content")
    with pytest.raises(ValueError):
        graph.add_node("title", "")

    source = graph.add_node("Source", "Source concept")
    with pytest.raises(KeyError):
        graph.add_edge("missing", source.node_id, "supports")
    with pytest.raises(KeyError):
        graph.add_edge(source.node_id, "missing", "supports")
    with pytest.raises(ValueError):
        graph.add_edge(source.node_id, source.node_id, "supports")
    with pytest.raises(KeyError):
        graph.link_related_concepts("missing")


def test_existing_edges_are_updated_and_similarity_edges_are_directionless():
    graph = KnowledgeGraph()
    source = graph.add_node("Source", "Agent memory source concept.")
    target = graph.add_node("Target", "Agent memory target concept.")

    edge = graph.add_edge(source.node_id, target.node_id, "supports", weight=0.2)
    updated = graph.add_edge(
        source.node_id,
        target.node_id,
        "supports",
        weight=0.8,
        metadata={"reason": "stronger"},
    )
    similar = graph.add_edge(source.node_id, target.node_id, "similar_to", weight=0.4)
    reversed_similar = graph.add_edge(target.node_id, source.node_id, "similar_to", weight=0.9)

    assert updated is edge
    assert updated.weight == 0.8
    assert updated.metadata["reason"] == "stronger"
    assert reversed_similar is similar
    assert similar.weight == 0.9


def test_build_clusters_groups_related_concepts():
    graph = KnowledgeGraph(auto_link_threshold=0.1)
    graph.add_node("Research Memory", "Research memory stores source evidence.")
    graph.add_node("Evidence Memory", "Evidence memory supports research reports.")
    graph.add_node("Runtime Load", "Runtime load balancing assigns agents.")

    clusters = graph.build_clusters(min_similarity=0.1)

    assert any(len(cluster.node_ids) >= 2 for cluster in clusters)
