from maios.retrieval import Chunker, Document, Retriever


class FakeEmbeddingProvider:
    def __init__(self):
        self.texts = []

    def embed(self, text):
        self.texts.append(text)
        return [float(len(text))]


class FakeVectorStore:
    def __init__(self):
        self.items = []
        self.queries = []

    def add(self, document, embedding):
        self.items.append((document, embedding))

    def search(self, embedding, top_k=5):
        self.queries.append((embedding, top_k))
        scored = [
            (document, 1.0 / (1.0 + abs(stored_embedding[0] - embedding[0])))
            for document, stored_embedding in self.items
        ]
        return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]


def test_document_defaults():
    document = Document(content="mission memory", metadata={"source": "test"})

    assert document.document_id.startswith("D-")
    assert document.content == "mission memory"
    assert document.metadata == {"source": "test"}


def test_chunker_returns_original_document_when_small():
    document = Document(content="short")
    chunks = Chunker(chunk_size=10, overlap=2).chunk(document)

    assert chunks == [document]


def test_chunker_splits_document_with_overlap():
    document = Document(content="abcdefghij", metadata={"source": "unit"})
    chunks = Chunker(chunk_size=4, overlap=1).chunk(document)

    assert [chunk.content for chunk in chunks] == ["abcd", "defg", "ghij", "j"]
    assert chunks[0].metadata["source_document_id"] == document.document_id
    assert chunks[1].metadata["chunk_index"] == 1
    assert chunks[1].metadata["start"] == 3


def test_chunker_validates_configuration():
    invalid_configs = [
        {"chunk_size": 0},
        {"chunk_size": 10, "overlap": -1},
        {"chunk_size": 10, "overlap": 10},
    ]

    for kwargs in invalid_configs:
        try:
            Chunker(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid chunker configuration to fail.")


def test_retriever_adds_chunk_embeddings_to_vector_store():
    provider = FakeEmbeddingProvider()
    store = FakeVectorStore()
    retriever = Retriever(
        embedding_provider=provider,
        vector_store=store,
        chunker=Chunker(chunk_size=5, overlap=0),
    )

    chunks = retriever.add(Document(content="abcdefghij"))

    assert [chunk.content for chunk in chunks] == ["abcde", "fghij"]
    assert provider.texts == ["abcde", "fghij"]
    assert len(store.items) == 2
    assert store.items[0][1] == [5.0]


def test_retriever_searches_with_query_embedding():
    provider = FakeEmbeddingProvider()
    store = FakeVectorStore()
    retriever = Retriever(provider, store)
    short_doc = Document(content="aaa")
    long_doc = Document(content="aaaaaaaa")

    retriever.add(short_doc)
    retriever.add(long_doc)

    results = retriever.retrieve("bbbbbbbb", top_k=1)
    scored = retriever.retrieve_with_score("bbb", top_k=2)

    assert results == [long_doc]
    assert store.queries[0] == ([8.0], 1)
    assert scored[0][0] == short_doc
    assert isinstance(scored[0][1], float)
