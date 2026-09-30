import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.chat.chat')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Setup vector store creates embeddings, stores documents and creates retriever"""
        # Prepare test data
        documents = ["chunk one of report", "chunk two of report"]
        report_text = "This is a long report that will be split into chunks."

        # Create agent instance (constructor should not auto-setup vector store)
        agent = ChatAgentWithMemory(report=report_text, config_path="default", headers=None, vector_store=None)

        # Ensure _process_document returns our controlled chunks
        agent._process_document = lambda rpt: documents

        # Get the module where ChatAgentWithMemory is defined
        module_name = agent.__class__.__module__
        module = __import__(module_name, fromlist=["*"])

        # Save originals to restore later
        orig_Config = getattr(module, "Config", None)
        orig_Memory = getattr(module, "Memory", None)
        orig_InMemoryVectorStore = getattr(module, "InMemoryVectorStore", None)
        orig_uuid = getattr(module, "uuid", None)

        class DummyUUID:
            def __str__(self):
                return "fixed-thread-uuid-1234"

        class FakeUUIDModule:
            def uuid4(self):
                return DummyUUID()

        class FakeConfig:
            def __init__(self, *args, **kwargs):
                # minimal attributes used by _setup_vector_store
                self.embedding_provider = "fake_provider"
                self.embedding_model = "fake_model"
                self.embedding_kwargs = {"some": "kw"}

        class FakeMemory:
            def __init__(self, provider, model, **kwargs):
                self.provider = provider
                self.model = model
                self.kwargs = kwargs

            def get_embeddings(self):
                return "fake_embeddings_object"

        class FakeInMemoryVectorStore:
            def __init__(self, embedding):
                self.embedding = embedding
                self.added_texts = None
                self.as_retriever_k = None

            def add_texts(self, texts):
                self.added_texts = list(texts)

            def as_retriever(self, k=4):
                self.as_retriever_k = k
                return {"retriever_for_k": k}

        # Patch module-level names used by _setup_vector_store
        try:
            module.Config = FakeConfig
            module.Memory = FakeMemory
            module.InMemoryVectorStore = FakeInMemoryVectorStore
            module.uuid = FakeUUIDModule()

            # Call the method under test
            agent._setup_vector_store()

            # Assertions
            # thread_id was set using our DummyUUID
            self.assertEqual(agent.thread_id, "fixed-thread-uuid-1234")

            # embedding was set from FakeMemory.get_embeddings
            self.assertEqual(agent.embedding, "fake_embeddings_object")

            # vector_store is instance of our fake vector store and stored the documents
            self.assertIsInstance(agent.vector_store, FakeInMemoryVectorStore)
            self.assertEqual(agent.vector_store.added_texts, documents)

            # retriever returned expected structure with k=4
            self.assertEqual(agent.retriever, {"retriever_for_k": 4})
            self.assertEqual(agent.vector_store.as_retriever_k, 4)
        finally:
            # Restore originals to avoid side effects on other tests
            if orig_Config is not None:
                module.Config = orig_Config
            else:
                if hasattr(module, "Config"):
                    delattr(module, "Config")
            if orig_Memory is not None:
                module.Memory = orig_Memory
            else:
                if hasattr(module, "Memory"):
                    delattr(module, "Memory")
            if orig_InMemoryVectorStore is not None:
                module.InMemoryVectorStore = orig_InMemoryVectorStore
            else:
                if hasattr(module, "InMemoryVectorStore"):
                    delattr(module, "InMemoryVectorStore")
            if orig_uuid is not None:
                module.uuid = orig_uuid
            else:
                if hasattr(module, "uuid"):
                    delattr(module, "uuid")
