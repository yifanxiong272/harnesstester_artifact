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
        """Ensure that when not final, num_lines is reduced by live_window and
        the stable lines are printed while the rest are kept in the live window.
        """
        stream = MarkdownStream()

        # Prevent real Live creation in update()
        stream._live_started = True

        # Create a dummy live object with console.print and update to capture calls
        class DummyConsole:
            def __init__(self):
                self.printed = []

            def print(self, obj):
                # record the object passed (usually a rich.Text)
                self.printed.append(obj)

        class DummyLive:
            def __init__(self):
                self.console = DummyConsole()
                self.updated = []
                self.stopped = False

            def update(self, obj):
                self.updated.append(obj)

            def stop(self):
                self.stopped = True

        dummy_live = DummyLive()
        stream.live = dummy_live

        # Make _render_markdown_to_lines return 8 lines so that
        # num_lines = 8 - live_window (6) => 2 stable lines to print
        lines = [f"line{i}\n" for i in range(8)]
        stream._render_markdown_to_lines = lambda text: list(lines)

        # Ensure printed starts empty
        self.assertEqual(stream.printed, [])

        # Call update with final=False to exercise the num_lines -= self.live_window branch
        stream.update("ignored markdown", final=False)

        # After update, two lines should have been moved to printed (stable)
        expected_printed = lines[:2]  # 8 total - 6 live_window = 2 stable lines
        self.assertEqual(stream.printed, expected_printed)

        # The dummy console.print should have been called once with a Text-like object
        self.assertTrue(len(dummy_live.console.printed) == 1)
        # The live.update should have been called to update the remaining lines (6 lines)
        self.assertTrue(len(dummy_live.updated) == 1)
