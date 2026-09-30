import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.server.server_utils')
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
        """Call handle_start_command so it executes json.loads(data[6:]) and extract_command_data,
        then returns early because 'task' is missing."""
        # Prepare payload missing "task" to force early return after extract_command_data
        payload = {
            "report_type": "summary",
            "source_urls": ["http://example.com"]
        }

        data = "start " + json.dumps(payload)

        # Call the async function and ensure it returns without raising and returns None
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(handle_start_command(None, data, None))
        self.assertIsNone(result)
