import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.views')
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
    def test_get_screenshot_missing_file_returns_none(self):
        """When a screenshot path is set but the file does not exist, get_screenshot should return None."""
        from browser_use.beta.service import _history_from_events

        # Use a filename that is very unlikely to exist on the test runner.
        missing_path = 'definitely_missing_screenshot_0123456789.png'

        events = [
            {
                'type': 'tool.output',
                'payload': {
                    'name': 'browser_script',
                    'tool_call_id': 'call-browser',
                    'images': [{'path': missing_path, 'mime_type': 'image/png'}],
                },
            },
            {'event_type': 'session.done', 'payload': {'result': 'final answer'}},
        ]

        history = _history_from_events(
            events,
            model='gpt-test',
            started=1.0,
            finished=2.0,
            output_model_schema=None,
            process_error=None,
        )

        # The reconstructed history should contain a state whose screenshot_path points to our missing file.
        state = history.history[0].state
        self.assertEqual(state.screenshot_path, missing_path)
        # get_screenshot should return None because the path does not exist.
        self.assertIsNone(state.get_screenshot())
