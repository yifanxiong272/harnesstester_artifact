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
        """When there are no new stable lines to show, update should return early
        without printing or updating the live window.
        """
        ms = MarkdownStream()

        # Create a dummy live object to ensure no real Live is started or used.
        class DummyConsole:
            def __init__(self):
                self.print_called = False

            def print(self, *a, **k):
                self.print_called = True

        class DummyLive:
            def __init__(self):
                self.console = DummyConsole()
                self.update_called = False
                self.stop_called = False

            def update(self, *a, **k):
                self.update_called = True

            def stop(self, *a, **k):
                self.stop_called = True

        ms._live_started = True
        ms.live = DummyLive()

        # Make the renderer return 10 lines so num_lines = 10.
        # live_window is 6 by default, so num_lines after subtraction = 4.
        rendered_lines = ["line\n"] * 10
        ms._render_markdown_to_lines = lambda text: list(rendered_lines)

        # Simulate that we've already printed 4 stable lines, so show == 0 -> early return.
        ms.printed = ["p\n"] * 4

        # Call update; should return early and not call console.print or live.update
        ms.update("ignored text", final=False)

        # Assertions: printed unchanged and no live writes happened
        self.assertEqual(ms.printed, ["p\n"] * 4)
        self.assertFalse(ms.live.console.print_called)
        self.assertFalse(ms.live.update_called)
        # when should have been updated
        self.assertGreater(ms.when, 0)
