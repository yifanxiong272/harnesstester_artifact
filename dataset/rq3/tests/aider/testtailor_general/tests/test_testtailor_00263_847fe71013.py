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
        """Ensure update returns early when there are no new stable lines to show.

        Path requirements:
          - final or num_lines > 0 must be True (we make num_lines > 0 by controlling _render_markdown_to_lines and live_window)
          - show <= 0 must be True (we set printed length >= num_lines)
        The method should return without printing or changing printed.
        """
        stream = MarkdownStream()

        # Prevent the real Live object from being created/started during the test.
        stream._live_started = True

        # Arrange for 3 rendered lines, and make the live window small so num_lines > 0.
        stream.live_window = 1
        def fake_renderer(text):
            return ["line1\n", "line2\n", "line3\n"]
        stream._render_markdown_to_lines = fake_renderer

        # Set printed so that len(printed) >= num_lines, causing show <= 0
        # After live_window subtraction: num_lines = 3 - 1 = 2, so make printed length 2.
        stream.printed = ["line1\n", "line2\n"]

        # Ensure throttle won't early-return: set when sufficiently in the past.
        stream.when = 0

        # Call update (not final). It should return early when show <= 0.
        result = stream.update("ignored text", final=False)

        # Verify it returned None and didn't change printed.
        self.assertIsNone(result)
        self.assertEqual(stream.printed, ["line1\n", "line2\n"])
