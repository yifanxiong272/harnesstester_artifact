import asyncio
from gpt_researcher.utils import llm as llm_module
from gpt_researcher.utils.llm import create_chat_completion

class _FakeProvider:
    def __init__(self, responses):
        # deterministic finite sequence of provider responses
        self._responses = list(responses)
        self._idx = 0

    async def get_chat_response(self, messages, stream, websocket, **kwargs):
        # emulate async provider behavior: return next response in sequence
        if self._idx < len(self._responses):
            r = self._responses[self._idx]
            self._idx += 1
            return r
        # if called more than expected, keep returning last value
        return self._responses[-1]


def _fake_get_llm(llm_provider=None, **kwargs):
    # returns a provider with two empty responses followed by a final truthy response
    return _FakeProvider(["", "", "FINAL"])


def test_probe_001():
    # Monkeypatch module-level get_llm to return our deterministic fake provider.
    llm_module.get_llm = _fake_get_llm

    messages = [{"role": "user", "content": "hello"}]

    # Call the async entrypoint synchronously via asyncio.run to obtain the result.
    result = asyncio.run(
        create_chat_completion(messages=messages, model="a-model", stream=False)
    )

    # Primary behavioral oracle: the function should return the first truthy provider response seen ('FINAL').
    assert result == "FINAL", f"Expected first truthy provider response 'FINAL', got: {result!r}"
