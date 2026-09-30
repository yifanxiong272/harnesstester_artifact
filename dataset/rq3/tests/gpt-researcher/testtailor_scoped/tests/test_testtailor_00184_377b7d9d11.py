import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.llm_provider.generic.base')
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
        """Ensure log_request writes the expected JSON line to the file handle."""
        logger = ChatLogger("dummy_fname")

        written = []

        class FakeHandle:
            async def write(self, data):
                # capture what would be written to the file
                written.append(data)
                return len(data)

        class FakeAiofilesCM:
            def __init__(self, fname, mode="a", encoding=None):
                self._handle = FakeHandle()

            async def __aenter__(self):
                return self._handle

            async def __aexit__(self, exc_type, exc, tb):
                return False

        def fake_aiofiles_open(fname, mode="a", encoding=None):
            return FakeAiofilesCM(fname, mode, encoding)

        messages = [{"role": "user", "content": "hello"}]
        response = {"reply": "hi"}

        with patch("aiofiles.open", new=fake_aiofiles_open):
            with patch("traceback.format_exc", return_value="fake-stacktrace"):
                loop = asyncio.get_event_loop()
                loop.run_until_complete(logger.log_request(messages, response))

        # One write call should have been made
        self.assertEqual(len(written), 1)
        # The written content should be JSON with our messages, response, and the patched stacktrace
        line = written[0].rstrip("\n")
        payload = json.loads(line)
        self.assertEqual(payload["messages"], messages)
        self.assertEqual(payload["response"], response)
        self.assertEqual(payload["stacktrace"], "fake-stacktrace")
