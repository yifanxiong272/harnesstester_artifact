import os
import pytest
import types

import gpt_researcher.context.compression as compression
from gpt_researcher.context.compression import ContextCompressor

# Create a minimal Document stand-in to patch into the module so we can
# observe Document construction without importing external dependencies.
class LocalDocument:
    def __init__(self, page_content=None, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}

    def __repr__(self):
        return f"LocalDocument(page_content={self.page_content!r})"


class DummyPromptFamily:
    def __init__(self):
        self.last_docs = None
        self.last_max = None

    def pretty_print_docs(self, docs, max_results):
        # Record the call inputs for assertions and return a deterministic string
        # based on the docs' page_content to make assertions straightforward.
        self.last_docs = list(docs)
        self.last_max = max_results
        contents = [getattr(d, 'page_content', str(d)) for d in self.last_docs]
        # Truncate to max_results like the real pretty printer might
        return "|".join(contents[:max_results])


@pytest.mark.asyncio
async def test_fast_path_round_102(monkeypatch):
    """
    Fast path: total_chars < COMPRESSION_THRESHOLD and len(documents) <= max_results
    Expectation: __get_contextual_retriever is NOT called and prompt_family.pretty_print_docs
    receives Document instances constructed from the raw_content strings.
    """
    # Patch the module-level Document so the code under test constructs our LocalDocument
    monkeypatch.setattr(compression, 'Document', LocalDocument)

    # Ensure threshold is large so small content triggers fast path
    monkeypatch.setenv('COMPRESSION_THRESHOLD', '8000')

    # Prepare a prompt family that returns a recognizably formatted string
    prompt = DummyPromptFamily()

    # Prepare tiny documents so total_chars < threshold and len <= max_results
    docs = [
        {'raw_content': 'docA', 'id': 'A'},
        {'raw_content': 'docB', 'id': 'B'},
    ]

    # Prevent the compression path from being used by making __get_contextual_retriever raise if called
    def fail_if_called(self):
        raise AssertionError("__get_contextual_retriever should not be called on fast path")

    monkeypatch.setattr(ContextCompressor, '_ContextCompressor__get_contextual_retriever', fail_if_called)

    # Instantiate compressor (match the real constructor signature: documents, embeddings, max_results, prompt_family, **kwargs)
    compressor = ContextCompressor(documents=docs, embeddings=None, max_results=5, prompt_family=prompt)

    result = await compressor.async_get_context(query='irrelevant', max_results=5)

    # The prompt family's pretty_print_docs should have been called with LocalDocument wrappers
    assert result == 'docA|docB'
    assert isinstance(prompt.last_docs[0], LocalDocument)
    assert prompt.last_max == 5


@pytest.mark.asyncio
async def test_compression_with_cost_callback_round_102(monkeypatch):
    """
    Compression path: force large total_chars by setting a tiny COMPRESSION_THRESHOLD.
    Verify that:
      - __get_contextual_retriever is used (its .invoke is called via asyncio.to_thread),
      - cost_callback is invoked with the value returned by estimate_embedding_cost,
      - prompt_family.pretty_print_docs is called with the retriever results and max_results.
    """
    # Patch Document to our lightweight stand-in
    monkeypatch.setattr(compression, 'Document', LocalDocument)

    # Force the code into the compression branch regardless of document sizes
    monkeypatch.setenv('COMPRESSION_THRESHOLD', '1')

    # Replace asyncio.to_thread with a synchronous executor to keep determinism
    # Patch at the module where it's referenced
    monkeypatch.setattr(compression.asyncio, 'to_thread', lambda func, *a, **k: func(*a, **k))

    # Stub estimate_embedding_cost to return a deterministic cost value
    captured_cost_calls = []

    def fake_estimate_embedding_cost(model, docs):
        # record the inputs for a possible assertion and return fixed cost
        captured_cost_calls.append((model, docs))
        return 42.5

    monkeypatch.setattr(compression, 'estimate_embedding_cost', fake_estimate_embedding_cost)

    # Build a retriever stub whose invoke returns a list of LocalDocument instances
    class RetrieverStub:
        def __init__(self, returned_docs):
            self._returned = returned_docs
            self.invoked_with = None

        def invoke(self, query, **kwargs):
            # record invocation and return the prebuilt documents
            self.invoked_with = (query, kwargs)
            return self._returned

    # Prepare retriever output documents (these should be passed to pretty_print_docs)
    returned_docs = [LocalDocument(page_content='R1'), LocalDocument(page_content='R2')]
    retriever = RetrieverStub(returned_docs)

    # Patch the private method to return our retriever stub
    monkeypatch.setattr(ContextCompressor, '_ContextCompressor__get_contextual_retriever', lambda self: retriever)

    # Prepare prompt family to capture the call
    prompt = DummyPromptFamily()

    # Prepare a cost_callback that captures the argument
    received_costs = []

    def cost_cb(val):
        received_costs.append(val)

    # Documents content can be anything; threshold forces compression branch
    docs = [{'raw_content': 'x' * 10, 'id': 'X'}]

    # Create compressor and ensure kwargs exists (some implementations rely on self.kwargs)
    compressor = ContextCompressor(documents=docs, embeddings=None, max_results=2, prompt_family=prompt, some_kw='v')

    # Ensure compressor.kwargs exists; if not set by __init__, set it explicitly to avoid unexpected kwargs errors
    if not hasattr(compressor, 'kwargs'):
        compressor.kwargs = {}

    result = await compressor.async_get_context(query='search-me', max_results=2, cost_callback=cost_cb)

    # The cost callback should have been called with the fake estimate value
    assert received_costs == [42.5]

    # estimate_embedding_cost should have been called with the configured model and the original docs list
    assert captured_cost_calls, "estimate_embedding_cost was not called"
    # confirm the model argument exists (we don't tightly couple to its exact name here)
    assert captured_cost_calls[0][1] == docs

    # The retriever's invoke should have been called with the query passed through
    assert retriever.invoked_with is not None
    assert retriever.invoked_with[0] == 'search-me'

    # The prompt family should have received the retriever-produced LocalDocument objects and respected max_results
    assert result == 'R1|R2'
    assert isinstance(prompt.last_docs[0], LocalDocument)
    assert prompt.last_max == 2
