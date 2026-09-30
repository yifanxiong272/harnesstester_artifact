import importlib
import asyncio

# Only exercise the public entrypoint declared in the route
from gpt_researcher.utils.llm import create_chat_completion


def test_probe_001_retry_returns_success():
    """Assert that create_chat_completion tolerates a transient exception from the
    provider.get_chat_response on the first attempt and returns the first later
    successful response ('SUCCESS').

    This test deterministically patches the module-level get_llm symbol to
    return a local Provider whose async get_chat_response raises once then
    returns 'SUCCESS'.
    """

    module = importlib.import_module("gpt_researcher.utils.llm")

    # Local transient error sentinel
    class TransientError(Exception):
        pass

    # Deterministic provider mock: raises on first call, succeeds on second
    class Provider:
        def __init__(self):
            self.calls = 0

        async def get_chat_response(self, messages, stream, websocket, **kwargs):
            self.calls += 1
            if self.calls == 1:
                # Simulate a transient, retryable failure
                raise TransientError("simulated transient error")
            # Subsequent call succeeds
            return "SUCCESS"

    def fake_get_llm(llm_provider=None, **kwargs):
        # Return a fresh provider instance (deterministic, in-process)
        return Provider()

    # Patch the module-level get_llm used by create_chat_completion
    original_get_llm = getattr(module, "get_llm")
    try:
        setattr(module, "get_llm", fake_get_llm)

        # Call the async entrypoint synchronously from the test harness
        result = asyncio.run(
            create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                model="gpt-test-model",
                llm_provider="dummy-provider",
                # leave other args as defaults (max_tokens within allowed bounds)
            )
        )

        # Primary behavioral oracle: must return the successful response
        assert result == "SUCCESS", (
            "create_chat_completion should return the provider's successful "
            "response when a transient exception occurs on an earlier attempt"
        )
    finally:
        # Restore original symbol to avoid test cross-talk
        setattr(module, "get_llm", original_get_llm)
