from maios.knowledge.store import KnowledgeStore
from maios.retrieval import Document, RetrievalEngine


class FakeVectorRetriever:
    def __init__(self):
        self.calls = []
        self.results = [(Document("vector result", document_id="D-vector"), 0.99)]

    def retrieve_with_score(self, query, top_k=5):
        self.calls.append((query, top_k))
        return self.results[:top_k]


def test_retrieval_engine_adds_to_knowledge_store(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    engine = RetrievalEngine(store)

    document_id = engine.add("mission command doctrine", {"source": "manual"})

    assert store.exists(document_id)
    assert store.get(document_id).content == "mission command doctrine"
    assert store.get(document_id).metadata == {"source": "manual"}


def test_retrieval_engine_retrieves_keyword_matches(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    first_id = store.add("mission command enables disciplined initiative")
    store.add("logistics planning supports sustainment")
    engine = RetrievalEngine(store)

    results = engine.retrieve("mission command", top_k=5)

    assert len(results) == 1
    assert results[0].document_id == first_id


def test_retrieval_engine_scores_and_ranks_keyword_results(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    strong_id = store.add("mission command doctrine")
    weak_id = store.add("mission logistics")
    engine = RetrievalEngine(store)

    results = engine.retrieve_with_score("mission command", top_k=2)

    assert [document.document_id for document, _score in results] == [
        strong_id,
        weak_id,
    ]
    assert results[0][1] == 1.0
    assert results[1][1] == 0.5


def test_retrieval_engine_searches_metadata(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    document_id = store.add("standing note", {"domain": "air defense"})
    engine = RetrievalEngine(store)

    results = engine.retrieve("defense")

    assert [document.document_id for document in results] == [document_id]


def test_retrieval_engine_respects_top_k(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    first_id = store.add("alpha mission")
    store.add("beta mission")
    engine = RetrievalEngine(store)

    results = engine.retrieve("mission", top_k=1)

    assert [document.document_id for document in results] == [first_id]


def test_retrieval_engine_can_delegate_to_vector_retriever(tmp_path):
    vector_retriever = FakeVectorRetriever()
    engine = RetrievalEngine(
        KnowledgeStore(tmp_path / "knowledge.json"),
        vector_retriever=vector_retriever,
    )

    results = engine.retrieve_with_score("semantic query", top_k=1)

    assert results == [(Document("vector result", document_id="D-vector"), 0.99)]
    assert vector_retriever.calls == [("semantic query", 1)]
