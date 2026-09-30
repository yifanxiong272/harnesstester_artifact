import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.knowledge_management.vector_base')
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
        """Test that contents_to_documents batches inputs in chunks of 16 and maps embeddings correctly."""
        # Prepare inputs: 20 items -> will require two calls (16 + 4)
        contents = [f"text_{i}" for i in range(20)]
        label = "label_A"

        # Save originals to restore later
        globals_dict = contents_to_documents.__globals__
        orig_APIBackend = globals_dict.get("APIBackend", None)
        orig_Document = globals_dict.get("Document", None)

        # Fake APIBackend to capture calls and return one embedding per input item
        class FakeAPIBackend:
            calls = []

            def __init__(self):
                pass

            def create_embedding(self, input_content):
                # Record the call (make a shallow copy)
                FakeAPIBackend.calls.append(list(input_content))
                # Return a simple embedding value for each input element
                return [f"emb_{c}" for c in input_content]

        # Simple fake Document to capture attributes
        class FakeDocument:
            def __init__(self, content, label, embedding):
                self.content = content
                self.label = label
                self.embedding = embedding

            def __repr__(self):
                return f"FakeDocument(content={self.content}, label={self.label}, embedding={self.embedding})"

        try:
            # Patch the globals used by the function
            globals_dict["APIBackend"] = FakeAPIBackend
            globals_dict["Document"] = FakeDocument

            # Call the function under test
            docs = contents_to_documents(contents, label=label)

            # Assertions
            # 1) Returned list length equals input length
            self.assertEqual(len(docs), len(contents))

            # 2) Each document has expected content, label and embedding
            for i, doc in enumerate(docs):
                self.assertEqual(doc.content, contents[i])
                self.assertEqual(doc.label, label)
                self.assertEqual(doc.embedding, f"emb_{contents[i]}")

            # 3) APIBackend.create_embedding was called twice: once for 16 items, once for 4 items
            self.assertEqual(len(FakeAPIBackend.calls), 2)
            self.assertEqual(len(FakeAPIBackend.calls[0]), 16)
            self.assertEqual(len(FakeAPIBackend.calls[1]), 4)
            # And the concatenation of calls equals the original contents
            concatenated = FakeAPIBackend.calls[0] + FakeAPIBackend.calls[1]
            self.assertEqual(concatenated, contents)

        finally:
            # Restore originals
            if orig_APIBackend is not None:
                globals_dict["APIBackend"] = orig_APIBackend
            else:
                globals_dict.pop("APIBackend", None)
            if orig_Document is not None:
                globals_dict["Document"] = orig_Document
            else:
                globals_dict.pop("Document", None)
