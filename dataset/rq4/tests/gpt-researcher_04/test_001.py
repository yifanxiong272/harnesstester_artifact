from backend.chat.chat import ChatAgentWithMemory


def test_probe_001():
    agent = ChatAgentWithMemory.__new__(ChatAgentWithMemory)
    agent.search_metadata = {"sentinel": True}

    class FailingTavilyClient:
        def search(self, query, max_results=5):
            raise RuntimeError("tavily failure for testing")

    agent.tavily_client = FailingTavilyClient()
    query = "example query"

    result = agent.quick_search(query)

    assert result == {"error": "tavily failure for testing", "results": []}

    assert agent.search_metadata == {
        "query": query,
        "sources": [],
        "error": "tavily failure for testing",
    }
