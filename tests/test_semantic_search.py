from maios.knowledge import KnowledgeGraph


def test_semantic_search_ranks_matching_concepts():
    graph = KnowledgeGraph()
    graph.add_node("Runtime Scheduling", "Distributed agents schedule queued tasks.")
    graph.add_node("Prompt Evolution", "Prompts improve after reflection history.")

    results = graph.semantic_search("distributed task scheduling")

    assert [node.title for node in results][:1] == ["Runtime Scheduling"]


def test_similarity_search_accepts_node_id_or_text():
    graph = KnowledgeGraph()
    runtime = graph.add_node("Runtime", "Agents execute distributed scheduled tasks.")
    graph.add_node("Scheduler", "Task scheduling balances distributed agent load.")
    graph.add_node("Research", "Research reports summarize evidence and gaps.")

    by_node = graph.similarity_search(runtime.node_id)
    by_text = graph.similarity_search("distributed task load balancing")

    assert by_node[0].title == "Scheduler"
    assert by_text[0].title in {"Runtime", "Scheduler"}


def test_empty_queries_return_no_search_results():
    graph = KnowledgeGraph()
    graph.add_node("Runtime", "Agents execute scheduled tasks.")

    assert graph.semantic_search("") == []
    assert graph.similarity_search("") == []


def test_experience_learning_links_success_and_failure_outcomes():
    graph = KnowledgeGraph(auto_link_threshold=0.1)
    graph.add_node("Source Collection", "Research source collection requires evidence.")
    success = graph.learn_experience("Research source collection found evidence.", "success")
    failure = graph.learn_experience("Research source collection missed evidence.", "failure")

    assert success.node_type == "experience"
    assert graph.edges_for(success.node_id, ["supports"], direction="out")
    assert graph.edges_for(failure.node_id, ["contradicts"], direction="out")
