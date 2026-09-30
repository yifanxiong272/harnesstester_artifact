import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.browser_use.chat')
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
        """Trigger the branch that raises ValueError('Request failed after ...') after retries exhausted."""
        # Create an instance with limited retries
        agent = ChatBrowserUse(model='bu-2-0', api_key='test-key', max_retries=3)

        # Prepare an async _make_request that always raises an HTTPStatusError (non-retryable code here)
        async def _always_http_error(payload: dict) -> dict:
            req = httpx.Request("POST", "https://llm.api.browser-use.com/v1/chat/completions")
            resp = httpx.Response(401, json={"detail": "unauthorized"})
            raise httpx.HTTPStatusError("unauthorized", request=req, response=resp)

        # Monkeypatch the _make_request to our raiser
        agent._make_request = _always_http_error

        # Monkeypatch _raise_http_error to be a no-op so the loop does not raise inside the except handler
        agent._raise_http_error = lambda e: None

        # Minimal message object with model_dump used by _serialize_message
        class DummyMessage:
            def model_dump(self):
                return {"role": "user", "content": "hello"}

        # Run ainvoke and assert we get the expected ValueError from the else branch
        with self.assertRaises(ValueError) as cm:
            asyncio.run(agent.ainvoke([DummyMessage()]))

        self.assertIn(f"Request failed after {agent.max_retries} attempts", str(cm.exception))
