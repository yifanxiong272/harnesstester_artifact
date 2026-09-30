import asyncio
from gpt_researcher.llm_provider.generic.base import GenericLLMProvider

class MockLLM:
    def __init__(self, chunks):
        self._chunks = list(chunks)

    async def astream(self, messages):
        # async generator that yields simple objects with a .content attribute
        for c in self._chunks:
            class Chunk:
                def __init__(self, content):
                    self.content = content
            yield Chunk(c)

class DummyWebSocket:
    def __init__(self):
        self.calls = []

    async def send_json(self, payload):
        # record payloads for later inspection
        self.calls.append(payload)

def _run_stream_response(provider, ws):
    # Run the provider.stream_response coroutine in a fresh asyncio event loop
    return asyncio.run(provider.stream_response(messages=[], websocket=ws))

def test_probe_001_flushes_final_partial_paragraph():
    """
    Activation:
    - Provide an LLM astream that yields chunks whose concatenation ends with no trailing newline.
    - Provide a websocket-like object recording send_json calls.
    Oracle (primary): websocket must receive a final report containing the full trailing text.
    This test will fail on implementations that only send when a newline is seen and never flush the final remainder.
    """
    # Arrange: provider with mock LLM that yields no-newline chunks
    provider = object.__new__(GenericLLMProvider)
    provider.llm = MockLLM(["hello", " world"])  # concatenation -> 'hello world' (no '\n')

    ws = DummyWebSocket()

    # Act: execute async stream_response synchronously via asyncio.run
    response = _run_stream_response(provider, ws)

    # Basic sanity: the returned response should be the concatenation of chunks (independent check)
    assert response == "hello world"

    # Primary oracle: websocket should have received a final report with the trailing partial paragraph
    assert ws.calls, "expected websocket.send_json to be called at least once with final partial text"
    assert ws.calls[-1] == {"type": "report", "output": "hello world"}
