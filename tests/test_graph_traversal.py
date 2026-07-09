from maios.knowledge import KnowledgeGraph


def test_traverse_follows_relationship_depth():
    graph = KnowledgeGraph()
    report = graph.add_node("Report", "Research report")
    source = graph.add_node("Source", "Source evidence")
    claim = graph.add_node("Claim", "Claim supported by source")
    graph.add_edge(report.node_id, source.node_id, "derived_from")
    graph.add_edge(source.node_id, claim.node_id, "supports")

    one_hop = graph.traverse(report.node_id, depth=1)
    two_hop = graph.traverse(report.node_id, depth=2)

    assert [node.node_id for node in one_hop] == [source.node_id]
    assert [node.node_id for node in two_hop] == [source.node_id, claim.node_id]


def test_traverse_supports_inbound_and_both_directions():
    graph = KnowledgeGraph()
    system = graph.add_node("System", "System has components")
    component = graph.add_node("Component", "Component is part of system")
    graph.add_edge(component.node_id, system.node_id, "part_of")

    inbound = graph.traverse(system.node_id, relationships=["part_of"], direction="in")
    both = graph.traverse(component.node_id, relationships=["part_of"], direction="both")

    assert inbound == [component]
    assert both == [system]


def test_traverse_returns_empty_for_zero_depth():
    graph = KnowledgeGraph()
    node = graph.add_node("Solo", "No traversal needed")

    assert graph.traverse(node.node_id, depth=0) == []
