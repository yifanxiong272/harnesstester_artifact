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
        """Test that ChatLogger.log_request writes a JSON line with messages, response and stacktrace."""
        logger = ChatLogger("dummy_log.txt")
        messages = [{"role": "user", "content": "hello"}]
        response = {"reply": "hi"}

        written = []

        async def fake_write(data):
            written.append(data)
            return None

        # create a fake async context manager returned by aiofiles.open
        mock_handle = unittest.mock.MagicMock()
        mock_handle.write = unittest.mock.AsyncMock(side_effect=fake_write)

        cm = unittest.mock.MagicMock()
        cm.__aenter__ = unittest.mock.AsyncMock(return_value=mock_handle)
        cm.__aexit__ = unittest.mock.AsyncMock(return_value=None)

        with unittest.mock.patch("aiofiles.open", return_value=cm) as mock_open, \
             unittest.mock.patch("traceback.format_exc", return_value="fake-stack"):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(logger.log_request(messages, response))

        mock_open.assert_called_once_with("dummy_log.txt", mode="a", encoding="utf-8")
        self.assertEqual(len(written), 1)
        # parse the written JSON and verify contents
        recorded = json.loads(written[0].strip())
        self.assertEqual(recorded["messages"], messages)
        self.assertEqual(recorded["response"], response)
        self.assertEqual(recorded["stacktrace"], "fake-stack")
