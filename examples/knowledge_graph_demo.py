from maios.knowledge import KnowledgeGraph


def main() -> None:
    graph = KnowledgeGraph("knowledge_graph.json")
    memory = graph.add_node(
        "Agent Memory",
        "Long-term memory stores reusable facts, decisions, and experiences.",
    )
    research = graph.add_node(
        "Autonomous Research",
        "Research reports derive findings from collected evidence.",
        metadata={"depends_on": memory.node_id},
    )
    graph.add_edge(research.node_id, memory.node_id, "depends_on")
    graph.learn_experience(
        "Research agents produced stronger reports after retrieving prior evidence.",
        "success",
    )
    graph.build_clusters()

    print("Semantic search:")
    for node in graph.semantic_search("research evidence memory"):
        print(f"- {node.title} ({node.node_type})")

    print("Traversal:")
    for node in graph.traverse(research.node_id, relationships=["depends_on"], depth=1):
        print(f"- {research.title} depends on {node.title}")


if __name__ == "__main__":
    main()
