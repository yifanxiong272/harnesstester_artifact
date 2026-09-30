import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.waiting')
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
        """Ensure Spinner.step executes the time.time() path when stdout is a TTY-like environment."""
        # Create the spinner instance
        spinner = Spinner("loading")

        # Force the spinner into a TTY-like state and provide a controllable console
        spinner.is_tty = True
        spinner.console = MagicMock()
        spinner.console.width = 80
        spinner.console.show_cursor = MagicMock()

        # Make sure the spinner will become visible on the next step call
        spinner.visible = False
        spinner.start_time = time.time() - 1.0  # more than 0.5s in the past
        spinner.last_update = 0.0

        # Fake stdout to capture writes without importing io
        class FakeStdout:
            def __init__(self):
                self.buf = ""
            def write(self, s):
                # emulate sys.stdout.write behavior
                self.buf += str(s)
            def flush(self):
                pass
            def isatty(self):
                return True

        fake = FakeStdout()
        original_stdout = sys.stdout
        try:
            sys.stdout = fake
            spinner.step("working")
        finally:
            sys.stdout = original_stdout

        output = fake.buf

        # Assertions to ensure the path executing `now = time.time()` progressed as expected
        self.assertTrue(spinner.visible)
        spinner.console.show_cursor.assert_called_with(False)
        self.assertIn("working", output)  # the text payload was written to stdout
        self.assertGreater(spinner.last_display_len, 0)
