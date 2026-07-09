import json

from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge.store import KnowledgeStore
from maios.retrieval import Document
from maios.runtime.packet import Packet


def test_knowledge_store_preserves_packet_save_get_api():
    store = KnowledgeStore()
    packet = Packet("legacy packet")

    store.save(packet)

    assert store.exists(packet.packet_id)
    assert store.get(packet.packet_id) == packet
    assert store.count() == 1


def test_knowledge_store_add_get_update_delete_document(tmp_path):
    path = tmp_path / "knowledge.json"
    store = KnowledgeStore(path)

    document_id = store.add("mission doctrine", {"kind": "note"})
    document = store.get(document_id)

    assert document.content == "mission doctrine"
    assert document.metadata == {"kind": "note"}
    assert store.exists(document_id)

    updated = store.update(document_id, content="updated doctrine", metadata={"kind": "updated"})

    assert updated.content == "updated doctrine"
    assert updated.metadata == {"kind": "updated"}
    assert store.delete(document_id)
    assert not store.exists(document_id)
    assert store.get(document_id) is None


def test_knowledge_store_persists_documents_to_json(tmp_path):
    path = tmp_path / "knowledge.json"
    original = KnowledgeStore(path)
    document = Document(content="persistent memory", metadata={"source": "test"})

    original.add(document)
    loaded = KnowledgeStore(path)

    assert loaded.get(document.document_id) == document
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["documents"][document.document_id]["content"] == "persistent memory"


def test_knowledge_store_searches_content_and_metadata(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    first_id = store.add("alpha mission memory", {"tag": "planning"})
    second_id = store.add("beta logistics memory", {"tag": "sustainment"})

    content_results = store.search("mission")
    metadata_results = store.search("sustainment")

    assert [document.document_id for document in content_results] == [first_id]
    assert [document.document_id for document in metadata_results] == [second_id]
    assert store.search("memory", top_k=1)[0].document_id == first_id


def test_knowledge_store_update_missing_document_returns_none(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")

    assert store.update("missing", content="none") is None
    assert not store.delete("missing")


def test_memory_kernel_can_persist_long_term_memory(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    kernel = MemoryKernel(knowledge_store=store)

    document = kernel.remember_long_term("stored long term memory", {"mission": "M-1"})

    assert store.get(document.document_id) == document
    assert KnowledgeStore(tmp_path / "knowledge.json").get(document.document_id) == document
