def test_probe_stream_response_flush_final_paragraph():
    import asyncio
    from types import SimpleNamespace
    from gpt_researcher.llm_provider.generic.base import GenericLLMProvider

    class DummyLLM:
        def __init__(self, chunks):
            self._chunks = list(chunks)

        async def astream(self, messages):
            # Deterministic async generator yielding chunk-like objects
            for c in self._chunks:
                yield SimpleNamespace(content=c)

    class DummyWebsocket:
        def __init__(self):
            self.sent = []

        async def send_json(self, obj):
            # Record calls for later inspection
            self.sent.append(obj)

    # Construct provider without invoking potentially complex __init__
    provider = GenericLLMProvider.__new__(GenericLLMProvider)
    # Provide deterministic mock LLM that will leave a trailing paragraph without a newline
    provider.llm = DummyLLM(["Line1\n", "Line2\n", "TrailingNoNewline"]) 

    ws = DummyWebsocket()

    # Run the async stream_response and capture the returned aggregated response
    response = asyncio.run(provider.stream_response(messages=[], websocket=ws))

    # PRIMARY ORACLE: the websocket must have received the final buffered text (which lacks a trailing newline)
    assert any(
        (isinstance(call, dict) and call.get("type") == "report" and call.get("output") == "TrailingNoNewline")
        for call in ws.sent
    ), f"Expected websocket.send_json to be called with the trailing buffered text, recorded calls: {ws.sent}"

    # Secondary check (observational): the returned response should equal the concatenation of all yielded contents
    assert response == "Line1\nLine2\nTrailingNoNewline"
