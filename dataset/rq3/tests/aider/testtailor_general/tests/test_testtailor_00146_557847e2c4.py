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
        """Trigger KeyboardInterrupt in main() so the KeyboardInterrupt handler prints the expected message."""
        # Minimal stdout replacement to capture printed output and provide methods used by Spinner/Console
        class DummyStdout:
            def __init__(self):
                self._buf = []
                self.encoding = "utf-8"

            def write(self, s):
                # Console/print may pass non-str occasionally; ensure string conversion
                s = str(s)
                self._buf.append(s)
                return len(s)

            def flush(self):
                pass

            def isatty(self):
                # Let Spinner attempt unicode probing
                return True

            def getvalue(self):
                return "".join(self._buf)

        dummy = DummyStdout()

        # Make Spinner.step raise KeyboardInterrupt to exercise the except block in main()
        with patch.object(Spinner, "step", side_effect=KeyboardInterrupt):
            # Prevent Spinner.end from performing real cleanup
            with patch.object(Spinner, "end", return_value=None):
                # Avoid real sleeping delays
                with patch("time.sleep", return_value=None):
                    # Replace sys.stdout with our dummy to capture prints
                    with patch("sys.stdout", new=dummy):
                        main()

        output = dummy.getvalue()
        # Ensure the KeyboardInterrupt handler's message was printed
        self.assertIn("Interrupted by user.", output)
