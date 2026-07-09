from maios.kernel.memory_kernel import MemoryKernel
from maios.retrieval import Document


class FakeRetriever:
    def __init__(self):
        self.added = []
        self.queries = []
        self.documents = [
            Document(content="long term doctrine note", metadata={"kind": "doctrine"})
        ]

    def add(self, document):
        self.added.append(document)
        return [document]

    def retrieve(self, query, top_k=5):
        self.queries.append((query, top_k))
        return self.documents[:top_k]

    def retrieve_with_score(self, query, top_k=5):
        self.queries.append((query, top_k))
        return [(document, 0.9) for document in self.documents[:top_k]]


def test_memory_kernel_preserves_execute_api():
    kernel = MemoryKernel()

    result = kernel.execute("mission analysis")

    assert result["status"] == "MEMORIZED"
    assert result["memory"] == ["mission analysis"]
    assert kernel.session_memory == ["mission analysis"]
    assert kernel.validate(result)


def test_memory_kernel_supports_short_term_retrieval():
    kernel = MemoryKernel()
    kernel.remember_short_term("alpha mission")
    kernel.remember_short_term("beta logistics")

    assert kernel.retrieve_short_term("mission") == ["alpha mission"]
    assert kernel.retrieve("mission") == ["alpha mission"]


def test_memory_kernel_adds_long_term_memory_to_injected_retriever():
    retriever = FakeRetriever()
    kernel = MemoryKernel(retriever=retriever)

    document = kernel.remember_long_term("persistent memory", {"source": "unit"})

    assert document.content == "persistent memory"
    assert document.metadata == {"source": "unit"}
    assert kernel.long_term_memory == [document]
    assert retriever.added == [document]


def test_memory_kernel_combines_short_and_long_term_retrieval():
    retriever = FakeRetriever()
    kernel = MemoryKernel(retriever=retriever)
    kernel.remember_short_term("short term doctrine note")

    results = kernel.retrieve("doctrine", top_k=5)

    assert results[0] == "short term doctrine note"
    assert results[1].content == "long term doctrine note"
    assert retriever.queries == [("doctrine", 5)]


def test_memory_kernel_retrieve_with_score_uses_retriever_when_available():
    retriever = FakeRetriever()
    kernel = MemoryKernel(retriever=retriever)

    results = kernel.retrieve_with_score("doctrine", top_k=1)

    assert results[0][0].content == "long term doctrine note"
    assert results[0][1] == 0.9
    assert retriever.queries == [("doctrine", 1)]


def test_memory_kernel_retrieve_with_score_without_retriever_uses_short_term():
    kernel = MemoryKernel()
    kernel.remember_short_term("short doctrine")

    results = kernel.retrieve_with_score("doctrine")

    assert results[0][0].content == "short doctrine"
    assert results[0][0].metadata == {"memory_type": "short_term"}
    assert results[0][1] == 1.0
