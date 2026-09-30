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
        """Call main() so the line `spinner = Spinner("Running spinner...")` is executed.
        Make the first time.sleep raise KeyboardInterrupt so the loop exits quickly and
        the finally block (spinner.end()) runs. Capture stdout to assert the interrupt
        message was printed.
        """
        # Minimal dummy stdout to capture prints and emulate a non-tty
        class DummyStdout:
            def __init__(self):
                self._buf = ""

            def write(self, s):
                self._buf += str(s)

            def flush(self):
                pass

            def isatty(self):
                return False

            def getvalue(self):
                return self._buf

        dummy_out = DummyStdout()

        # Patch time.sleep to raise KeyboardInterrupt immediately on first call,
        # which causes main() to hit the except block and then the finally block.
        with patch("time.sleep", side_effect=KeyboardInterrupt()):
            with patch("sys.stdout", new=dummy_out):
                # Call the function-under-test; instantiation of Spinner happens inside.
                main()

        output = dummy_out.getvalue()
        # The except block in main prints "\nInterrupted by user."
        self.assertIn("Interrupted by user.", output)
