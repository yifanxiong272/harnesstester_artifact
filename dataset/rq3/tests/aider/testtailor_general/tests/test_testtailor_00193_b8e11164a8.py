import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.mdstream')
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
        """Ensure update returns early (no rendering) when called too soon after previous update."""
        stream = MarkdownStream()

        # Pretend the live renderer was already started so update won't try to start it.
        stream._live_started = True

        # Set when to "now" and a long min_delay so the next update should be throttled.
        initial_when = time.time()
        stream.when = initial_when
        stream.min_delay = 1.0  # 1 second throttle window

        # Replace the rendering method with one that would fail the test if called.
        def fail_if_called(text):
            raise AssertionError("Renderer should not be invoked when update is throttled")
        stream._render_markdown_to_lines = fail_if_called

        # Call update quickly; because now - stream.when < min_delay, it should return early.
        stream.update("## Hello\n\nThis should be throttled.", final=False)

        # Verify that update returned early: the timestamp should be unchanged and nothing printed.
        self.assertEqual(stream.when, initial_when)
        self.assertEqual(stream.printed, [])
