import uuid
import types

import pytest

import backend.chat.chat as chatmod
from backend.chat.chat import ChatAgentWithMemory


class DummyConfig:
    def __init__(self):
        # values the implementation expects to read
        self.embedding_provider = "dummy-provider"
        self.embedding_model = "dummy-model"
        self.embedding_kwargs = {"kw": "val"}


class DummyMemory:
    def __init__(self, provider, model, **kwargs):
        # record what was passed in to validate forwarding
        self.provider = provider
        self.model = model
        self.kwargs = kwargs

    def get_embeddings(self):
        # deterministic embedding object
        return {"provider": self.provider, "model": self.model, **self.kwargs}


class DummyVectorStore:
    def __init__(self, embedding):
        # record embedding and texts added
        self.embedding = embedding
        self.added_texts = None

    def add_texts(self, texts):
        # record call for assertion
        self.added_texts = list(texts)

    def as_retriever(self, k=1):
        # return a deterministic retriever object influenced by embedding and k
        return {"k": k, "embedding_snapshot": self.embedding}


def test_setup_vector_store_creates_components_round_167(monkeypatch):
    """
    Validate _setup_vector_store wires together document processing, uuid assignment,
    embedding creation via Memory.get_embeddings, vector store creation, adding texts,
    and retriever creation. This patches Config, Memory, InMemoryVectorStore and uuid.uuid4
    to deterministic implementations.
    """
    # Patch module-level collaborators where the code under test resolves them
    monkeypatch.setattr(chatmod, "Config", DummyConfig)
    monkeypatch.setattr(chatmod, "Memory", DummyMemory)
    monkeypatch.setattr(chatmod, "InMemoryVectorStore", DummyVectorStore)

    # Force a deterministic uuid
    fixed_uuid = uuid.UUID("00000000-0000-0000-0000-000000000001")
    # chatmod.uuid is the uuid module imported in the source; patch its uuid4
    monkeypatch.setattr(chatmod.uuid, "uuid4", lambda: fixed_uuid)

    # Create an agent instance without running its __init__ (avoids external dependencies)
    agent = object.__new__(ChatAgentWithMemory)
    # Provide a predictable report value used by _process_document
    agent.report = {"title": "rpt"}

    # Patch the instance method _process_document to return known document chunks
    def fake_process_document(report):
        # assert it receives the same report we set (helps check call path)
        assert report == agent.report
        return ["chunk A", "chunk B"]

    agent._process_document = fake_process_document

    # Run the method under test
    agent._setup_vector_store()

    # Assertions that cover the behavior in lines 85-101
    #  - documents were created from _process_document
    assert isinstance(agent.thread_id, str)
    assert agent.thread_id == str(fixed_uuid)

    # embedding was created using DummyMemory.get_embeddings()
    expected_embedding = {"provider": "dummy-provider", "model": "dummy-model", "kw": "val"}
    assert agent.embedding == expected_embedding

    # vector_store is the DummyVectorStore and recorded added_texts
    assert isinstance(agent.vector_store, DummyVectorStore)
    assert agent.vector_store.added_texts == ["chunk A", "chunk B"]

    # retriever returned by as_retriever(k=4) and uses embedding snapshot
    assert agent.retriever == {"k": 4, "embedding_snapshot": expected_embedding}
