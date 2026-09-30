import types
import pytest

from backend.chat.chat import ChatAgentWithMemory

# The tests call the unbound method ChatAgentWithMemory.quick_search with a simple
# self-like object (SimpleNamespace) to avoid needing to construct the full
# ChatAgentWithMemory (which may require complex init parameters).


def test_client_none_round_097():
    """When tavily_client is None, quick_search should set search_metadata and
    return the disabled error structure."""
    self_obj = types.SimpleNamespace(tavily_client=None, search_metadata=None)

    result = ChatAgentWithMemory.quick_search(self_obj, "my-query")

    # Returned structure must indicate web search is disabled and have empty results
    assert result == {
        "error": "Web search is disabled - TAVILY_API_KEY not configured",
        "results": []
    }

    # search_metadata must be populated with the query, empty sources, and the same error
    assert isinstance(self_obj.search_metadata, dict)
    assert self_obj.search_metadata["query"] == "my-query"
    assert self_obj.search_metadata["sources"] == []
    assert self_obj.search_metadata["error"] == "Web search is disabled - TAVILY_API_KEY not configured"


def test_search_results_truncation_round_097():
    """When the tavily client returns long content, the search_metadata content
    must be truncated to 200 characters plus '...'. The original returned
    results dict must be returned verbatim by quick_search.
    """
    long_content = "x" * 250

    class MockClient:
        def search(self, query, max_results=5):
            return {
                "results": [
                    {"title": "Title A", "url": "http://a.example/", "content": long_content}
                ]
            }

    mock = MockClient()
    self_obj = types.SimpleNamespace(tavily_client=mock, search_metadata=None)

    returned = ChatAgentWithMemory.quick_search(self_obj, "long-content-query")

    # The function returns the raw results returned by the client
    assert returned == {"results": [{"title": "Title A", "url": "http://a.example/", "content": long_content}]}

    # search_metadata should be created with truncated content
    assert isinstance(self_obj.search_metadata, dict)
    assert self_obj.search_metadata["query"] == "long-content-query"
    assert isinstance(self_obj.search_metadata["sources"], list)
    assert len(self_obj.search_metadata["sources"]) == 1
    src = self_obj.search_metadata["sources"][0]
    assert src["title"] == "Title A"
    assert src["url"] == "http://a.example/"

    # Content should be first 200 chars plus '...'
    assert src["content"] == ("x" * 200) + "..."


def test_search_exception_round_097():
    """If the tavily client's search raises an exception, quick_search must
    return an error dict with the exception message and not modify search_metadata
    (if it was None before).
    """
    class ExplodingClient:
        def search(self, query, max_results=5):
            raise RuntimeError("boom")

    mock = ExplodingClient()
    self_obj = types.SimpleNamespace(tavily_client=mock, search_metadata=None)

    returned = ChatAgentWithMemory.quick_search(self_obj, "cause-error")

    # Should return error message and an empty results list
    assert returned == {"error": "boom", "results": []}

    # Because the exception happens before search_metadata assignment, it remains None
    assert self_obj.search_metadata is None
